/**
 * i18n setup: loads the three language files and picks the starting language.
 *
 * Every visible string comes from en.json / fr.json / es.json through
 * `t('key')`. Start order: the saved choice, then the device language if
 * we support it, then English.
 */

import { getLocales } from 'expo-localization';
import { createInstance } from 'i18next';
import { initReactI18next } from 'react-i18next';

import { readPreference, STORAGE_KEYS, writePreference } from '@/lib/storage';

import en from './en.json';
import es from './es.json';
import fr from './fr.json';

export const LANGUAGES = ['en', 'fr', 'es'] as const;

// One entry per language; the parity test checks every one against English.
export const resources = { en, fr, es };
export type Language = (typeof LANGUAGES)[number];

// Locale tags used by Intl.NumberFormat and date formatting (SPEC 9).
export const INTL_LOCALE: Record<Language, string> = { en: 'en-US', fr: 'fr-FR', es: 'es-US' };

export function isLanguage(value: unknown): value is Language {
  return typeof value === 'string' && (LANGUAGES as readonly string[]).includes(value);
}

function deviceLanguage(): Language {
  const code = getLocales()[0]?.languageCode;
  return isLanguage(code) ? code : 'en';
}

// Our own instance (not the global one), so tests and app share exactly this.
const i18n = createInstance();

void i18n.use(initReactI18next).init({
  resources: Object.fromEntries(
    Object.entries(resources).map(([lang, translation]) => [lang, { translation }]),
  ),
  lng: deviceLanguage(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false }, // React already escapes output
});

// Apply a saved choice once storage answers (async on every platform).
void readPreference(STORAGE_KEYS.language).then((saved) => {
  if (isLanguage(saved) && saved !== i18n.language) void i18n.changeLanguage(saved);
});

export function setLanguage(language: Language): void {
  void i18n.changeLanguage(language);
  void writePreference(STORAGE_KEYS.language, language);
}

export default i18n;
