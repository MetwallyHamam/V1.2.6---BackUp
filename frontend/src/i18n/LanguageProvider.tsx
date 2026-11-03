import { ReactNode, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import {
  LANGUAGE_STORAGE_KEY,
  type SupportedLanguage,
  validLanguage,
} from "./config";

export function LanguageProvider({ children }: { children: ReactNode }) {
  const { i18n } = useTranslation();
  const { user } = useAuth();
  const userLanguage = user?.preferred_language;

  useEffect(() => {
    const language: SupportedLanguage = validLanguage(userLanguage)
      ? userLanguage
      : validLanguage(i18n.language)
        ? i18n.language
        : "en";
    if (i18n.language !== language) void i18n.changeLanguage(language);
    document.documentElement.lang = language;
    document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
    try {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    } catch {
      // Browser storage is an optional startup cache; the database remains authoritative.
    }
  }, [i18n, i18n.language, userLanguage]);

  return children;
}
