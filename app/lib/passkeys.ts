/**
 * Web passkeys through the browser's WebAuthn API (SPEC 6.2 item 3).
 *
 * @simplewebauthn/browser turns the API's JSON options into the binary
 * objects navigator.credentials expects, and the browser's answer back
 * into JSON. Native passkeys are V1.1 (D-22), so on iOS/Android
 * `passkeysSupported()` is false and the passkey buttons are hidden.
 */

import {
  browserSupportsWebAuthn,
  startAuthentication,
  startRegistration,
  type PublicKeyCredentialCreationOptionsJSON,
  type PublicKeyCredentialRequestOptionsJSON,
} from '@simplewebauthn/browser';
import { Platform } from 'react-native';

import { api, type TokenResponse } from './api';
import { readPreference, STORAGE_KEYS, writePreference } from './storage';

export function passkeysSupported(): boolean {
  return Platform.OS === 'web' && browserSupportsWebAuthn();
}

export async function registerPasskey(label: string): Promise<void> {
  const { challenge_id, options } = await api.passkeyRegisterOptions();
  const credential = await startRegistration({
    optionsJSON: options as unknown as PublicKeyCredentialCreationOptionsJSON,
  });
  await api.passkeyRegisterVerify(challenge_id, credential, label);
  await writePreference(STORAGE_KEYS.hasPasskey, 'yes');
}

export async function signInWithPasskey(): Promise<TokenResponse> {
  const { challenge_id, options } = await api.passkeyLoginOptions();
  const credential = await startAuthentication({
    optionsJSON: options as unknown as PublicKeyCredentialRequestOptionsJSON,
  });
  const tokens = await api.passkeyLoginVerify(challenge_id, credential);
  await writePreference(STORAGE_KEYS.hasPasskey, 'yes');
  return tokens;
}

/** Once this browser has used a passkey, it becomes the default sign-in. */
export async function deviceHasPasskey(): Promise<boolean> {
  return (await readPreference(STORAGE_KEYS.hasPasskey)) === 'yes';
}
