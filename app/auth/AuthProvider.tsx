/**
 * Auth context: who is signed in, and the actions that change it.
 *
 * At startup it tries /auth/refresh (the cookie on web, secure-store on
 * native) to restore the session. `status` is 'loading' until that answers.
 * The MFA token and the email waiting for verification stay in memory
 * here, never in the URL, so they don't end up in browser history.
 * While signed in, theme and language follow the account (/settings).
 */

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';

import { setLanguage } from '@/i18n';
import {
  api,
  type Me,
  onSessionEnded,
  refreshSession,
  type Settings,
  storeTokens,
  type TokenResponse,
} from '@/lib/api';
import { passkeysSupported } from '@/lib/passkeys';
import { readPreference, STORAGE_KEYS, writePreference } from '@/lib/storage';
import { clearTokens } from '@/lib/tokens';
import { useTheme } from '@/theme/ThemeProvider';

type Status = 'loading' | 'signedOut' | 'signedIn';

type AuthContextValue = {
  status: Status;
  me: Me | null;
  /** Email waiting for its verification code (set by sign-up or sign-in). */
  pendingEmail: string | null;
  setPendingEmail: (email: string | null) => void;
  /** Password was right; this token proves it while the 2nd factor is asked. */
  mfaToken: string | null;
  setMfaToken: (token: string | null) => void;
  completeSignIn: (tokens: TokenResponse) => Promise<void>;
  reloadMe: () => Promise<void>;
  signOut: () => Promise<void>;
  /** Offer a passkey after sign-in, once, on browsers that support it. */
  shouldOfferPasskey: boolean;
  dismissPasskeyOffer: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>('loading');
  const [me, setMe] = useState<Me | null>(null);
  const [pendingEmail, setPendingEmail] = useState<string | null>(null);
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [offerDismissed, setOfferDismissed] = useState(true);
  const { preference, setPreference } = useTheme();
  const { i18n } = useTranslation();
  // The values last saved to (or loaded from) the server; null = not synced yet.
  const synced = useRef<Settings | null>(null);

  const signedOut = useCallback(() => {
    synced.current = null;
    setMe(null);
    setMfaToken(null);
    setStatus('signedOut');
  }, []);

  const loadAccount = useCallback(async () => {
    const [account, settings] = await Promise.all([api.me(), api.getSettings()]);
    synced.current = settings;
    setPreference(settings.theme);
    setLanguage(settings.language);
    setMe(account);
    setStatus('signedIn');
  }, [setPreference]);

  // Restore the session once at startup.
  useEffect(() => {
    onSessionEnded(signedOut);
    void readPreference(STORAGE_KEYS.passkeyOfferDismissed).then((v) =>
      setOfferDismissed(v === 'yes'),
    );
    void refreshSession()
      .then((ok) => (ok ? loadAccount() : signedOut()))
      .catch(signedOut);
  }, [loadAccount, signedOut]);

  // Push theme/language changes made in the app to the account.
  const language = i18n.language;
  useEffect(() => {
    const last = synced.current;
    if (status !== 'signedIn' || !last) return;
    const patch: Partial<Settings> = {};
    if (preference !== last.theme) patch.theme = preference;
    if (language !== last.language && (language === 'en' || language === 'fr' || language === 'es'))
      patch.language = language;
    if (Object.keys(patch).length === 0) return;
    synced.current = { ...last, ...patch };
    void api.patchSettings(patch).catch(() => {
      // Offline: the device keeps the choice; the next change retries.
    });
  }, [status, preference, language]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      me,
      pendingEmail,
      setPendingEmail,
      mfaToken,
      setMfaToken,
      completeSignIn: async (tokens) => {
        await storeTokens(tokens);
        setMfaToken(null);
        setPendingEmail(null);
        await loadAccount();
      },
      reloadMe: async () => setMe(await api.me()),
      signOut: async () => {
        try {
          await api.logout();
        } catch {
          // Already signed out on the server, or offline: sign out locally anyway.
        }
        await clearTokens();
        signedOut();
      },
      shouldOfferPasskey:
        status === 'signedIn' &&
        !offerDismissed &&
        (me?.passkey_count ?? 0) === 0 &&
        passkeysSupported(),
      dismissPasskeyOffer: () => {
        setOfferDismissed(true);
        void writePreference(STORAGE_KEYS.passkeyOfferDismissed, 'yes');
      },
    }),
    [status, me, pendingEmail, mfaToken, offerDismissed, loadAccount, signedOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>');
  return value;
}
