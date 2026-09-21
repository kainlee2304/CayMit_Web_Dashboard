import { vi } from "./vi";
import { en } from "./en";

export type Locale = "vi" | "en";
export const translations = { vi, en };

export function getTranslation(locale: Locale = "vi") {
  return translations[locale] || translations.vi;
}

export { useLanguage, LanguageProvider } from "@/context/LanguageContext";
export { vi, en };
