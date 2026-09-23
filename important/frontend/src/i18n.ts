import React, { createContext, useContext, useState, type ReactNode } from 'react';

export type Language = 'en' | 'fr' | 'nl';

export interface Translations {
  nav: {
    opportunities: string;
    internships: string;
    profile: string;
    applications: string;
    interviewPrep: string;
    companies: string;
    supervision: string;
    scraperHub: string;
    guide: string;
    extension: string;
    aiSettings: string;
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
  internships: {
    title: string;
    subtitle: string;
    searchPlaceholder: string;
    allRepos: string;
    allVisas: string;
    sponsorsVisa: string;
    noSponsorship: string;
    usCitizenOnly: string;
    canadaEligible: string;
    notSpecified: string;
    allCategories: string;
    openOnly: string;
    totalListings: string;
    activeOpenings: string;
    syncGithub: string;
    syncing: string;
    clearFilters: string;
    applyNow: string;
    closed: string;
    matchingCount: string;
    viewGrid: string;
    viewTable: string;
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
  common: {
    loading: string;
    retry: string;
    cancel: string;
    save: string;
    close: string;
    export: string;
    all: string;
  };
}

export const translations: Record<Language, Translations> = {
  en: {
    nav: {
      opportunities: 'Opportunities',
      internships: 'Internships',
      profile: 'Match Profile',
      applications: 'Applications',
      interviewPrep: 'Interview Prep',
      companies: 'Company Intel',
      supervision: 'Data Supervision',
      scraperHub: 'Scraper Hub',
      guide: 'Guide & Docs',
      extension: 'Browser Extension',
      aiSettings: 'AI Settings',
      login: 'Sign In',
      logout: 'Sign Out',
    },
    hero: {
      badge: 'Real-Time Career Intelligence',
      titlePrefix: 'Verified Careers, ',
      titleHighlight: 'Worldwide & Across Regions',
      titleSuffix: '',
      subtitle: 'Compliant ingestion directly from verified employer portals worldwide. Transparent matching, sanitized job intelligence, and zero intermediaries.',
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
    internships: {
      title: 'Curated Tech Internships',
      subtitle: 'Directly parsed from top community GitHub repositories with work authorization status, company logos, and direct career links.',
      searchPlaceholder: 'Search by company, role, location, or keyword (e.g. Disney, SWE, Toronto, AI)...',
      allRepos: 'All Repositories',
      allVisas: 'All Sponsorship',
      sponsorsVisa: 'Sponsors Visa',
      noSponsorship: 'No Sponsorship',
      usCitizenOnly: 'US Citizens Only',
      canadaEligible: 'Canada Eligible',
      notSpecified: 'Not Specified',
      allCategories: 'All Categories',
      openOnly: 'Active Only',
      totalListings: 'Total Tracked',
      activeOpenings: 'Active Openings',
      syncGithub: 'Sync with GitHub',
      syncing: 'Syncing Live...',
      clearFilters: 'Clear Filters',
      applyNow: 'Apply',
      closed: 'Closed',
      matchingCount: 'matching opportunities',
      viewGrid: 'Grid View',
      viewTable: 'Table View',
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
    common: {
      loading: 'Loading...',
      retry: 'Retry',
      cancel: 'Cancel',
      save: 'Save',
      close: 'Close',
      export: 'Export',
      all: 'All',
    },
  },
  fr: {
    nav: {
      opportunities: 'Opportunités',
      internships: 'Stages & Alternances',
      profile: 'Profil de Match',
      applications: 'Mes Candidatures',
      interviewPrep: 'Préparation Entretiens',
      companies: 'Entreprises',
      supervision: 'Supervision Données',
      scraperHub: 'Centre de Scraping',
      guide: 'Guide & Documentation',
      extension: 'Extension Navigateur',
      aiSettings: 'Paramètres IA',
      login: 'Connexion',
      logout: 'Déconnexion',
    },
    hero: {
      badge: 'Veille Carrière en Temps Réel',
      titlePrefix: 'Carrières Vérifiées, ',
      titleHighlight: 'Mondial & Multi-Régions',
      titleSuffix: '',
      subtitle: 'Ingestion conforme directement depuis les portails recruteurs officiels à l\'international. Scoring transparent, descriptions assainies et zéro intermédiaire.',
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
    internships: {
      title: 'Stages Tech Vérifiés',
      subtitle: 'Directement extrait des meilleurs dépôts GitHub communautaires avec statut de visa, logos et liens officiels.',
      searchPlaceholder: 'Rechercher par entreprise, poste, lieu ou mot-clé (ex. Disney, SWE, Paris, IA)...',
      allRepos: 'Tous les Dépôts',
      allVisas: 'Toutes Autorisations',
      sponsorsVisa: 'Sponsorise le Visa',
      noSponsorship: 'Pas de Sponsoring',
      usCitizenOnly: 'Citoyens US Uniquement',
      canadaEligible: 'Éligible Canada',
      notSpecified: 'Non Spécifié',
      allCategories: 'Toutes Catégories',
      openOnly: 'Actives Uniquement',
      totalListings: 'Total Suivi',
      activeOpenings: 'Postes Actifs',
      syncGithub: 'Synchroniser GitHub',
      syncing: 'Synchronisation en direct...',
      clearFilters: 'Réinitialiser Filtres',
      applyNow: 'Postuler',
      closed: 'Fermé',
      matchingCount: 'opportunités correspondantes',
      viewGrid: 'Vue Grille',
      viewTable: 'Vue Tableau',
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
    common: {
      loading: 'Chargement...',
      retry: 'Réessayer',
      cancel: 'Annuler',
      save: 'Enregistrer',
      close: 'Fermer',
      export: 'Exporter',
      all: 'Tous',
    },
  },
  nl: {
    nav: {
      opportunities: 'Vacatures',
      internships: 'Stages',
      profile: 'Matchprofiel',
      applications: 'Sollicitaties',
      interviewPrep: 'Sollicitatiegesprek',
      companies: 'Bedrijven',
      supervision: 'Gegevenstoezicht',
      scraperHub: 'Scraper Hub',
      guide: 'Handleiding & Documentatie',
      extension: 'Browserextensie',
      aiSettings: 'AI-instellingen',
      login: 'Inloggen',
      logout: 'Uitloggen',
    },
    hero: {
      badge: 'Realtime Loopbaanintelligentie',
      titlePrefix: 'Geverifieerde Carrières, ',
      titleHighlight: 'Wereldwijd & Grenzeloos',
      titleSuffix: '',
      subtitle: 'Directe intake van geverifieerde werkgeversportalen wereldwijd. Transparante matching, opgeschoonde vacature-informatie en zonder tussenpersonen.',
    },
    search: {
      placeholder: 'Zoek op functie, vaardigheid, tech stack of werkgever...',
      allCountries: 'Alle Landen',
      allModes: 'Alle Werktijden',
      savedJobs: 'Opgeslagen Vacatures',
      remote: 'Op Afstand',
      hybrid: 'Hybride',
      onsite: 'Op Locatie',
    },
    directory: {
      opportunitiesCount: 'actieve vacatures gevonden',
      page: 'Pagina',
      of: 'van',
      prev: 'Vorige',
      next: 'Volgende',
      noJobsFound: 'Geen vacatures gevonden die voldoen aan uw criteria.',
      noJobsSub: 'Probeer uw zoektermen, werkvormfilters of geselecteerde land aan te passen.',
    },
    card: {
      match: 'Match',
      viewDetails: 'Details Bekijken',
      saved: 'Opgeslagen',
      save: 'Opslaan',
    },
    internships: {
      title: 'Gecureerde Tech Stages',
      subtitle: 'Rechtstreeks geëxtraheerd uit actieve GitHub-repositories van de gemeenschap met visumstatus, bedrijfslogo\'s en directe links.',
      searchPlaceholder: 'Zoek op bedrijf, functie, locatie of trefwoord (bijv. Disney, SWE, Amsterdam, AI)...',
      allRepos: 'Alle Repositories',
      allVisas: 'Alle Visumstatussen',
      sponsorsVisa: 'Sponsoring Mogelijk',
      noSponsorship: 'Geen Sponsoring',
      usCitizenOnly: 'Alleen VS Burgers',
      canadaEligible: 'Geschikt voor Canada',
      notSpecified: 'Niet Gespecificeerd',
      allCategories: 'Alle Categorieën',
      openOnly: 'Alleen Openstaand',
      totalListings: 'Totaal Gevolgde',
      activeOpenings: 'Actieve Vacatures',
      syncGithub: 'Synchroniseren met GitHub',
      syncing: 'Live Synchroniseren...',
      clearFilters: 'Filters Wissen',
      applyNow: 'Solliciteren',
      closed: 'Gesloten',
      matchingCount: 'overeenkomende vacatures',
      viewGrid: 'Rasterweergave',
      viewTable: 'Tabelweergave',
    },
    modal: {
      posted: 'Geplaatst op',
      employmentType: 'Dienstverband',
      workMode: 'Vorm',
      salary: 'Salaris',
      matchAnalysis: 'Regelgebaseerde Matchanalyse',
      strengths: 'Overeenkomende Vaardigheden',
      missingSkills: 'Ontbrekende Vaardigheden',
      description: 'Functieomschrijving (Beveiligd)',
      applyOnPortal: 'Solliciteren via Carrièreportaal',
      close: 'Sluiten',
    },
    profile: {
      title: 'Kandidaatprofiel & Matchinstellingen',
      subtitle: 'Stel uw vaardigheden, voorkeuren en doelsalaris in voor nauwkeurige matchscores.',
      preferences: 'Carrièrevoorkeuren',
      skills: 'Vaardigheden & Technologieën',
      workMode: 'Voorkeurswerkvorm',
      location: 'Voorkeurslocatie',
      expectedSalary: 'Minimaal Verwacht Salaris',
      saveChanges: 'Voorkeuren Opslaan',
    },
    scraper: {
      title: 'Scraper Hub & Doelenmonitor',
      subtitle: 'Inspecteer actieve werkgeversdoelen, robots.txt-naleving en synchronisatieruns.',
      liveTargets: 'Geconfigureerde Bronnen',
      complianceNote: 'Alle portalen hanteren robots.txt-richtlijnen en wachttijden.',
      sync: 'Bron Synchroniseren',
      syncing: 'Synchroniseren...',
      cooldown: 'In Wachttijd',
      disallowed: 'Geweigerd door Robots.txt',
    },
    common: {
      loading: 'Laden...',
      retry: 'Opnieuw Proberen',
      cancel: 'Annuleren',
      save: 'Opslaan',
      close: 'Sluiten',
      export: 'Exporteren',
      all: 'Alle',
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
      return saved === 'fr' || saved === 'nl' ? saved : 'en';
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
    t: translations[language] || translations.en,
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
