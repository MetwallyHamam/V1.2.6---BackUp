import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import ar from "../locales/ar.json";
import en from "../locales/en.json";

export type SupportedLanguage = "en" | "ar";
export const LANGUAGE_STORAGE_KEY = "support-hub-language";
export const supportedLanguages: ReadonlyArray<{
  code: SupportedLanguage;
  label: string;
  nativeLabel: string;
  direction: "ltr" | "rtl";
}> = [
  { code: "en", label: "English", nativeLabel: "English", direction: "ltr" },
  { code: "ar", label: "Arabic", nativeLabel: "العربية", direction: "rtl" },
];

export function validLanguage(value: unknown): value is SupportedLanguage {
  return value === "en" || value === "ar";
}

function initialLanguage(): SupportedLanguage {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return validLanguage(stored) ? stored : "en";
  } catch {
    return "en";
  }
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ar: { translation: ar } },
  lng: initialLanguage(),
  fallbackLng: "en",
  supportedLngs: ["en", "ar"],
  interpolation: { escapeValue: false },
  returnNull: false,
  saveMissing: import.meta.env.DEV,
  missingKeyHandler: (_languages, _namespace, key) => {
    if (import.meta.env.DEV) console.warn(`Missing translation: ${key}`);
  },
});

export default i18n;
