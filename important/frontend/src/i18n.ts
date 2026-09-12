import React, { createContext, useContext, useState, type ReactNode } from 'react';

export type Language = 'en' | 'fr';

export interface Translations {
  nav: {
    opportunities: string;
    profile: string;
    scraperHub: string;
    login: string;
    logout: string;
  };
  hero: {
    badge: string;
    titlePrefix: string;
    titleHighlight: string;
    titleSuffix: string;
    subtitle: string;
  };
  search: {
    placeholder: string;
    allCountries: string;
    allModes: string;
    savedJobs: string;
    remote: string;
    hybrid: string;
    onsite: string;
  };
  directory: {
    opportunitiesCount: string;
    page: string;
    of: string;
    prev: string;
    next: string;
    noJobsFound: string;
    noJobsSub: string;
  };
  card: {
    match: string;
    viewDetails: string;
    saved: string;
    save: string;
  };
  modal: {
    posted: string;
    employmentType: string;
    workMode: string;
    salary: string;
    matchAnalysis: string;
    strengths: string;
    missingSkills: string;
    description: string;
    applyOnPortal: string;
    close: string;
  };
  profile: {
    title: string;
    subtitle: string;
    preferences: string;
    skills: string;
    workMode: string;
    location: string;
    expectedSalary: string;
    saveChanges: string;
  };
  scraper: {
    title: string;
    subtitle: string;
    liveTargets: string;
    complianceNote: string;
    sync: string;
    syncing: string;
    cooldown: string;
    disallowed: string;
  };
}

export const translations: Record<Language, Translations> = {
  en: {
    nav: {
      opportunities: 'Opportunities',
      profile: 'Match Profile',
      scraperHub: 'Scraper Hub',
      login: 'Sign In',
      logout: 'Sign Out',
    },
    hero: {
      badge: 'Real-Time Career Intelligence',
      titlePrefix: 'Verified Careers in ',
      titleHighlight: 'Morocco & Beyond',
      titleSuffix: '',
      subtitle: 'Compliant ingestion directly from verified employer portals. Transparent matching, sanitized job intelligence, and zero intermediaries.',
    },
    search: {
      placeholder: 'Search by role, skill, tech stack, or employer...',
      allCountries: 'All Countries',
      allModes: 'All Work Modes',
      savedJobs: 'Saved Jobs',
      remote: 'Remote',
      hybrid: 'Hybrid',
      onsite: 'Onsite',
    },
    directory: {
      opportunitiesCount: 'active opportunities found',
      page: 'Page',
      of: 'of',
      prev: 'Previous',
      next: 'Next',
      noJobsFound: 'No opportunities found matching your criteria.',
      noJobsSub: 'Try adjusting your search terms, work mode filters, or selected country.',
    },
    card: {
      match: 'Match',
      viewDetails: 'View Details',
      saved: 'Saved',
      save: 'Save',
    },
    modal: {
      posted: 'Posted',
      employmentType: 'Employment',
      workMode: 'Mode',
      salary: 'Salary',
      matchAnalysis: 'Rule-Based Match Analysis',
      strengths: 'Matched Strengths',
      missingSkills: 'Missing / Desired Skills',
      description: 'Job Description (Sanitized)',
      applyOnPortal: 'Apply on Career Portal',
      close: 'Close',
    },
    profile: {
      title: 'Candidate Profile & Match Settings',
      subtitle: 'Customize your skills, preferences, and salary targets for deterministic match scoring.',
      preferences: 'Career Preferences',
      skills: 'Skills & Technologies',
      workMode: 'Preferred Work Mode',
      location: 'Preferred Location',
      expectedSalary: 'Minimum Expected Salary',
      saveChanges: 'Save Preferences',
    },
    scraper: {
      title: 'Scraper Hub & Target Monitor',
      subtitle: 'Inspect live employer targets, robots.txt compliance status, and sync runs.',
      liveTargets: 'Configured Targets',
      complianceNote: 'All portals enforce robots.txt compliance and rate cooldown limits.',
      sync: 'Sync Target',
      syncing: 'Syncing...',
      cooldown: 'In Cooldown',
      disallowed: 'Robots Disallowed',
    },
  },
  fr: {
    nav: {
      opportunities: 'Opportunités',
      profile: 'Profil de Match',
      scraperHub: 'Centre de Scraping',
      login: 'Connexion',
      logout: 'Déconnexion',
    },
    hero: {
      badge: 'Veille Carrière en Temps Réel',
      titlePrefix: 'Carrières vérifiées au ',
      titleHighlight: 'Maroc & International',
      titleSuffix: '',
      subtitle: 'Ingestion conforme directement depuis les portails recruteurs officiels. Scoring transparent, descriptions assainies et zéro intermédiaire.',
    },
    search: {
      placeholder: 'Rechercher par poste, compétence, technologie ou entreprise...',
      allCountries: 'Tous les pays',
      allModes: 'Tous les modes',
      savedJobs: 'Favoris',
      remote: 'Télétravail',
      hybrid: 'Hybride',
      onsite: 'Sur site',
    },
    directory: {
      opportunitiesCount: 'opportunités actives trouvées',
      page: 'Page',
      of: 'sur',
      prev: 'Précédent',
      next: 'Suivant',
      noJobsFound: 'Aucune opportunité ne correspond à vos critères.',
      noJobsSub: 'Essayez de modifier vos termes de recherche, le mode de travail ou le pays sélectionné.',
    },
    card: {
      match: 'Match',
      viewDetails: 'Détails',
      saved: 'Enregistré',
      save: 'Enregistrer',
    },
    modal: {
      posted: 'Publié le',
      employmentType: 'Contrat',
      workMode: 'Mode',
      salary: 'Rémunération',
      matchAnalysis: 'Analyse de Correspondance Déterministe',
      strengths: 'Compétences Validées',
      missingSkills: 'Compétences Manquantes / Souhaitées',
      description: 'Description du Poste (Sécurisée)',
      applyOnPortal: 'Postuler sur le Portail Recruteur',
      close: 'Fermer',
    },
    profile: {
      title: 'Profil Candidat & Paramètres de Match',
      subtitle: 'Définissez vos compétences, préférences et salaire cible pour le calcul de pertinence.',
      preferences: 'Préférences Professionnelles',
      skills: 'Compétences & Technologies',
      workMode: 'Mode de Travail Préféré',
      location: 'Localisation Préférée',
      expectedSalary: 'Salaire Minimum Souhaité',
      saveChanges: 'Enregistrer les Préférences',
    },
    scraper: {
      title: 'Moniteur de Scraping & Sources',
      subtitle: 'Inspectez les sources employeurs, la conformité robots.txt et les cycles de synchronisation.',
      liveTargets: 'Cibles Configurées',
      complianceNote: 'Chaque source respecte les directives robots.txt et les délais de temporisation.',
      sync: 'Synchroniser',
      syncing: 'Synchronisation...',
      cooldown: 'En Temporisation',
      disallowed: 'Refusé par Robots.txt',
    },
  },
};

interface LanguageContextProps {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: Translations;
}

const LanguageContext = createContext<LanguageContextProps | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    try {
      const saved = localStorage.getItem('compust_lang');
      return saved === 'fr' ? 'fr' : 'en';
    } catch {
      return 'en';
    }
  });

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    try {
      localStorage.setItem('compust_lang', lang);
    } catch {
      // ignore
    }
  };

  const value = {
    language,
    setLanguage,
    t: translations[language],
  };

  return React.createElement(LanguageContext.Provider, { value }, children);
};

export const useTranslation = (): LanguageContextProps => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useTranslation must be used within a LanguageProvider');
  }
  return context;
};
