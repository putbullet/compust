/**
 * Multilingual Resume Localization Utilities
 * Supports canonical neutral tokens, backward compatibility for legacy labels,
 * and natural English, French, and German translations.
 */

export type SupportedResumeLanguage = 'en' | 'fr' | 'de';

export type SkillProficiencyToken =
  | 'NONE'
  | 'BEGINNER'
  | 'INTERMEDIATE'
  | 'ADVANCED'
  | 'EXPERT';

export type LanguageProficiencyToken =
  | 'NONE'
  | 'NATIVE'
  | 'BILINGUAL'
  | 'FLUENT'
  | 'PROFESSIONAL'
  | 'INTERMEDIATE'
  | 'BASIC';

export const SKILL_PROFICIENCY_LABELS: Record<SupportedResumeLanguage, Record<SkillProficiencyToken, string>> = {
  en: {
    NONE: '',
    BEGINNER: 'Beginner',
    INTERMEDIATE: 'Intermediate',
    ADVANCED: 'Advanced',
    EXPERT: 'Expert',
  },
  fr: {
    NONE: '',
    BEGINNER: 'Débutant',
    INTERMEDIATE: 'Intermédiaire',
    ADVANCED: 'Avancé',
    EXPERT: 'Expert',
  },
  de: {
    NONE: '',
    BEGINNER: 'Anfänger',
    INTERMEDIATE: 'Fortgeschritten',
    ADVANCED: 'Sehr gute Kenntnisse',
    EXPERT: 'Experte',
  },
};

export const LANGUAGE_PROFICIENCY_LABELS: Record<SupportedResumeLanguage, Record<LanguageProficiencyToken, string>> = {
  en: {
    NONE: '',
    NATIVE: 'Native',
    BILINGUAL: 'Bilingual',
    FLUENT: 'Fluent',
    PROFESSIONAL: 'Professional Working',
    INTERMEDIATE: 'Intermediate',
    BASIC: 'Basic',
  },
  fr: {
    NONE: '',
    NATIVE: 'Langue maternelle',
    BILINGUAL: 'Bilingue',
    FLUENT: 'Courant',
    PROFESSIONAL: 'Professionnel',
    INTERMEDIATE: 'Intermédiaire',
    BASIC: 'Notions / Débutant',
  },
  de: {
    NONE: '',
    NATIVE: 'Muttersprache',
    BILINGUAL: 'Zweisprachig',
    FLUENT: 'Fließend',
    PROFESSIONAL: 'Verhandlungssicher',
    INTERMEDIATE: 'Gute Kenntnisse',
    BASIC: 'Grundkenntnisse',
  },
};

export const DEFAULT_SECTION_TITLES_BY_LANG: Record<SupportedResumeLanguage, Record<string, string>> = {
  en: {
    summary: 'Professional Summary',
    experience: 'Professional Experience',
    education: 'Education & Academic Background',
    skills: 'Technical & Core Skills',
    projects: 'Featured Projects',
    certifications: 'Certifications & Accreditations',
    languages: 'Languages',
    custom_sections: 'Additional Information',
  },
  fr: {
    summary: 'Profil Professionnel',
    experience: 'Expérience Professionnelle',
    education: 'Formation & Diplômes',
    skills: 'Compétences',
    projects: 'Projets Réalisés',
    certifications: 'Certifications',
    languages: 'Langues',
    custom_sections: 'Informations Complémentaires',
  },
  de: {
    summary: 'Kurzprofil',
    experience: 'Berufserfahrung',
    education: 'Ausbildung',
    skills: 'Kenntnisse & Fähigkeiten',
    projects: 'Projekte',
    certifications: 'Zertifikate',
    languages: 'Sprachen',
    custom_sections: 'Zusätzliche Informationen',
  },
};

/**
 * Normalize raw/legacy skill proficiency to canonical token.
 */
export function normalizeSkillProficiency(raw?: string | null): SkillProficiencyToken {
  if (!raw) return 'NONE';
  const clean = String(raw).trim().toUpperCase();
  if (['', 'NONE', 'NO_LABEL', 'NO LABEL', 'BLANK', 'NULL', 'UNDEFINED'].includes(clean)) {
    return 'NONE';
  }
  if (clean.includes('BEGINNER') || clean.includes('DEBUTANT') || clean.includes('DÉBUTANT') || clean.includes('ANFÄNGER') || clean.includes('ANFANGER')) {
    return 'BEGINNER';
  }
  if (clean.includes('INTERMEDIATE') || clean.includes('INTERMEDIAIRE') || clean.includes('INTERMÉDIAIRE') || clean.includes('MITTEL')) {
    return 'INTERMEDIATE';
  }
  if (clean.includes('ADVANCED') || clean.includes('AVANCE') || clean.includes('AVANCÉ') || clean.includes('FORTGESCHRITTEN')) {
    return 'ADVANCED';
  }
  if (clean.includes('EXPERT')) {
    return 'EXPERT';
  }
  return 'NONE';
}

/**
 * Normalize raw/legacy spoken language proficiency to canonical token.
 */
export function normalizeLanguageProficiency(raw?: string | null): LanguageProficiencyToken {
  if (!raw) return 'NONE';
  const clean = String(raw).trim().toUpperCase();
  if (['', 'NONE', 'NO_LABEL', 'NO LABEL', 'BLANK', 'NULL', 'UNDEFINED'].includes(clean)) {
    return 'NONE';
  }
  if (clean.includes('NATIVE') || clean.includes('MATERNELLE') || clean.includes('MUTTERSPRACHE')) {
    return 'NATIVE';
  }
  if (clean.includes('BILINGUAL') || clean.includes('BILINGUE') || clean.includes('ZWEISPRACHIG')) {
    return 'BILINGUAL';
  }
  if (clean.includes('FLUENT') || clean.includes('COURANT') || clean.includes('FLIEẞEND') || clean.includes('FLIESSEND')) {
    return 'FLUENT';
  }
  if (clean.includes('PROFESSIONAL') || clean.includes('PROFESSIONNEL') || clean.includes('VERHANDLUNGSSICHER')) {
    return 'PROFESSIONAL';
  }
  if (clean.includes('INTERMEDIATE') || clean.includes('INTERMEDIAIRE') || clean.includes('INTERMÉDIAIRE') || clean.includes('GUTE KENNTNISSE')) {
    return 'INTERMEDIATE';
  }
  if (clean.includes('BASIC') || clean.includes('NOTION') || clean.includes('GRUNDKENNTNISSE')) {
    return 'BASIC';
  }
  return 'NONE';
}

/**
 * Get localized skill proficiency label.
 * Returns empty string if NONE / no label.
 */
export function getSkillProficiencyLabel(proficiency?: string | null, lang: string = 'en'): string {
  const token = normalizeSkillProficiency(proficiency);
  if (token === 'NONE') return '';
  const langKey = (lang && ['en', 'fr', 'de'].includes(lang.toLowerCase()) ? lang.toLowerCase() : 'en') as SupportedResumeLanguage;
  return SKILL_PROFICIENCY_LABELS[langKey]?.[token] || SKILL_PROFICIENCY_LABELS.en[token] || '';
}

/**
 * Get localized spoken language proficiency label.
 * Returns empty string if NONE / no label.
 */
export function getLanguageProficiencyLabel(proficiency?: string | null, lang: string = 'en'): string {
  const token = normalizeLanguageProficiency(proficiency);
  if (token === 'NONE') return '';
  const langKey = (lang && ['en', 'fr', 'de'].includes(lang.toLowerCase()) ? lang.toLowerCase() : 'en') as SupportedResumeLanguage;
  return LANGUAGE_PROFICIENCY_LABELS[langKey]?.[token] || LANGUAGE_PROFICIENCY_LABELS.en[token] || '';
}

/**
 * Dropdown options for Skill Proficiency selector.
 */
export function getSkillDropdownOptions(lang: string = 'en'): Array<{ value: SkillProficiencyToken; label: string }> {
  const langKey = (lang && ['en', 'fr', 'de'].includes(lang.toLowerCase()) ? lang.toLowerCase() : 'en') as SupportedResumeLanguage;
  const noLabelText = langKey === 'fr' ? 'Sans niveau' : langKey === 'de' ? 'Ohne Angabe' : 'No label';
  return [
    { value: 'NONE', label: noLabelText },
    { value: 'BEGINNER', label: SKILL_PROFICIENCY_LABELS[langKey].BEGINNER },
    { value: 'INTERMEDIATE', label: SKILL_PROFICIENCY_LABELS[langKey].INTERMEDIATE },
    { value: 'ADVANCED', label: SKILL_PROFICIENCY_LABELS[langKey].ADVANCED },
    { value: 'EXPERT', label: SKILL_PROFICIENCY_LABELS[langKey].EXPERT },
  ];
}

/**
 * Dropdown options for Spoken Language Proficiency selector.
 */
export function getLanguageDropdownOptions(lang: string = 'en'): Array<{ value: LanguageProficiencyToken; label: string }> {
  const langKey = (lang && ['en', 'fr', 'de'].includes(lang.toLowerCase()) ? lang.toLowerCase() : 'en') as SupportedResumeLanguage;
  const noLabelText = langKey === 'fr' ? 'Sans niveau' : langKey === 'de' ? 'Ohne Angabe' : 'No label';
  return [
    { value: 'NONE', label: noLabelText },
    { value: 'NATIVE', label: LANGUAGE_PROFICIENCY_LABELS[langKey].NATIVE },
    { value: 'BILINGUAL', label: LANGUAGE_PROFICIENCY_LABELS[langKey].BILINGUAL },
    { value: 'FLUENT', label: LANGUAGE_PROFICIENCY_LABELS[langKey].FLUENT },
    { value: 'PROFESSIONAL', label: LANGUAGE_PROFICIENCY_LABELS[langKey].PROFESSIONAL },
    { value: 'INTERMEDIATE', label: LANGUAGE_PROFICIENCY_LABELS[langKey].INTERMEDIATE },
    { value: 'BASIC', label: LANGUAGE_PROFICIENCY_LABELS[langKey].BASIC },
  ];
}

/**
 * Resolve localized section title with custom title override.
 */
export function getLocalizedSectionTitle(
  sectionId: string,
  lang: string = 'en',
  customTitle?: string | null
): string {
  if (customTitle && typeof customTitle === 'string' && customTitle.trim()) {
    return customTitle.trim();
  }
  const langKey = (lang && ['en', 'fr', 'de'].includes(lang.toLowerCase()) ? lang.toLowerCase() : 'en') as SupportedResumeLanguage;
  const defaults = DEFAULT_SECTION_TITLES_BY_LANG[langKey] || DEFAULT_SECTION_TITLES_BY_LANG.en;
  return defaults[sectionId] || DEFAULT_SECTION_TITLES_BY_LANG.en[sectionId] || sectionId.replace(/_/g, ' ');
}

export const PRESENT_LABELS: Record<SupportedResumeLanguage, string> = {
  en: 'Present',
  fr: 'Présent',
  de: 'Heute',
};

export function getLocalizedPresentLabel(lang: string = 'en'): string {
  const langKey = (lang && ['en', 'fr', 'de'].includes(lang.toLowerCase()) ? lang.toLowerCase() : 'en') as SupportedResumeLanguage;
  return PRESENT_LABELS[langKey] || PRESENT_LABELS.en;
}

export const DEGREE_CONNECTORS: Record<SupportedResumeLanguage, string> = {
  en: 'in',
  fr: 'en',
  de: 'in',
};

export function getLocalizedDegreeConnector(lang: string = 'en'): string {
  const langKey = (lang && ['en', 'fr', 'de'].includes(lang.toLowerCase()) ? lang.toLowerCase() : 'en') as SupportedResumeLanguage;
  return DEGREE_CONNECTORS[langKey] || DEGREE_CONNECTORS.en;
}

export const HONORS_LABELS: Record<SupportedResumeLanguage, string> = {
  en: 'GPA / Honors:',
  fr: 'Mention / Moyenne :',
  de: 'Abschlussnote / Auszeichnungen:',
};

export function getLocalizedHonorsLabel(lang: string = 'en'): string {
  const langKey = (lang && ['en', 'fr', 'de'].includes(lang.toLowerCase()) ? lang.toLowerCase() : 'en') as SupportedResumeLanguage;
  return HONORS_LABELS[langKey] || HONORS_LABELS.en;
}

