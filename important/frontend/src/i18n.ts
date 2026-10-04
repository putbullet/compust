import React, { createContext, useContext, useState, type ReactNode } from 'react';
import {
  applicationsTranslations,
  type ApplicationsTranslations,
  formatRelativeTime,
  getStatusLabel,
  getPriorityLabel,
  getCommunicationStatusLabel,
} from './locales/applicationsTranslations';

export { formatRelativeTime, getStatusLabel, getPriorityLabel, getCommunicationStatusLabel };
export type { ApplicationsTranslations };

export type Language = 'en' | 'fr' | 'de' | 'nl';

export interface Translations {
  applications: ApplicationsTranslations;
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
  guide: {
    tableOfContents: string;
    searchPlaceholder: string;
    groupGettingStarted: string;
    groupResumeStudio: string;
    groupBrowserExtension: string;
    groupJobDiscovery: string;
    groupApplicationTracking: string;
    groupDataSupervision: string;
    groupDeveloper: string;
    groupHelp: string;
    githubRepo: string;
    reportIssue: string;
    discussions: string;
    watchDemo: string;
    copyCode: string;
    copied: string;
    searchNoResults: string;
  };
  mockInterview: {
    setup: {
      title: string;
      subtitle: string;
      domainLabel: string;
      roleLabel: string;
      difficultyLabel: string;
      durationLabel: string;
      detectDomainBtn: string;
      analyzingResume: string;
      aiSuggestedBadge: string;
      aiSuggestedNote: string;
      startBtn: string;
      historyBtn: string;
      plannedQuestions: string;
      difficultyFundamental: string;
      difficultyIntermediate: string;
      difficultyAdvanced: string;
      difficultyMixed: string;
      minutes: string;
    };
    permission: {
      title: string;
      micRequired: string;
      micDesc: string;
      cameraNotice: string;
      privacyHeader: string;
      sttLocal: string;
      audioDiscarded: string;
      llmLocal: string;
      testMicBtn: string;
      micReady: string;
      micError: string;
      beginInterviewBtn: string;
      backBtn: string;
    };
    interview: {
      interviewerStateSpeaking: string;
      interviewerStateListening: string;
      interviewerStateProcessing: string;
      turnIndicator: string;
      followUpBadge: string;
      timeRemaining: string;
      recordBtn: string;
      stopRecordBtn: string;
      skipBtn: string;
      endInterviewBtn: string;
      confirmEndTitle: string;
      confirmEndDesc: string;
      confirmEndYes: string;
      confirmEndCancel: string;
      liveTranscript: string;
      transcriptPlaceholder: string;
      ttsMute: string;
      ttsUnmute: string;
    };
    evaluating: {
      title: string;
      subtitle: string;
      stage1: string;
      stage2: string;
      stage3: string;
      stage4: string;
      waitNotice: string;
    };
    assessment: {
      title: string;
      overallScore: string;
      disclaimer: string;
      summaryTitle: string;
      skillMatrixTitle: string;
      weakAreasTitle: string;
      recommendationsTitle: string;
      questionReviewTitle: string;
      repracticeBtn: string;
      newInterviewBtn: string;
      backToPrepBtn: string;
      ratingStrong: string;
      ratingModerate: string;
      ratingWeak: string;
      correctness: string;
      completeness: string;
      technicalDepth: string;
      clarity: string;
      missingConcepts: string;
      incorrectClaims: string;
      positivePoints: string;
      improvementPoints: string;
      betterAnswer: string;
      yourAnswer: string;
    };
    history: {
      title: string;
      empty: string;
      startFirstBtn: string;
      score: string;
      date: string;
      duration: string;
      questions: string;
      viewAssessment: string;
      backBtn: string;
    };
  };
}

export const translations: Record<Language, Translations> = {
  en: {
    applications: applicationsTranslations.en,
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
    guide: {
      tableOfContents: 'Table of Contents',
      searchPlaceholder: 'Search documentation, extension, ATS, matching, FAQ...',
      groupGettingStarted: 'Getting Started',
      groupResumeStudio: 'Resume Studio',
      groupBrowserExtension: 'Browser Extension',
      groupJobDiscovery: 'Job Discovery',
      groupApplicationTracking: 'Application Tracking',
      groupDataSupervision: 'Data Supervision & Scraping',
      groupDeveloper: 'Developer Guide',
      groupHelp: 'Help & FAQ',
      githubRepo: 'GitHub Repository',
      reportIssue: 'Report Issue',
      discussions: 'Discussions',
      watchDemo: 'Watch Demo',
      copyCode: 'Copy',
      copied: 'Copied!',
      searchNoResults: 'No sections match your search.',
    },
    mockInterview: {
      setup: {
        title: 'AI Mock Technical Interview',
        subtitle: 'Simulate a realistic spoken technical interview with adaptive questions and a detailed assessment.',
        domainLabel: 'Technical Track',
        roleLabel: 'Target Role (Optional)',
        difficultyLabel: 'Difficulty Level',
        durationLabel: 'Interview Duration',
        detectDomainBtn: 'Analyze My Resume',
        analyzingResume: 'Analyzing resume...',
        aiSuggestedBadge: 'AI Suggested',
        aiSuggestedNote: 'Suggested based on your active resume. You can override anytime.',
        startBtn: 'Continue to Setup Check',
        historyBtn: 'Past Interviews',
        plannedQuestions: 'Estimated Questions',
        difficultyFundamental: 'Fundamental',
        difficultyIntermediate: 'Intermediate',
        difficultyAdvanced: 'Advanced',
        difficultyMixed: 'Mixed (Adaptive)',
        minutes: 'minutes',
      },
      permission: {
        title: 'Pre-Interview Check & Privacy',
        micRequired: 'Microphone Access Required',
        micDesc: 'Your microphone captures your spoken answers. Audio is processed locally on your machine.',
        cameraNotice: 'Camera is not required — this is a spoken technical interview.',
        privacyHeader: 'Local-First Privacy Guarantee',
        sttLocal: 'Speech-to-text runs locally via faster-whisper.',
        audioDiscarded: 'Raw audio is immediately deleted after transcription — never stored.',
        llmLocal: 'Evaluation and follow-ups run locally using Ollama.',
        testMicBtn: 'Test Microphone',
        micReady: 'Microphone verified & ready!',
        micError: 'Microphone access denied. Please grant microphone permissions in your browser.',
        beginInterviewBtn: 'Start Interview',
        backBtn: 'Back to Setup',
      },
      interview: {
        interviewerStateSpeaking: 'Interviewer Speaking...',
        interviewerStateListening: 'Listening to your answer...',
        interviewerStateProcessing: 'Processing response...',
        turnIndicator: 'Question',
        followUpBadge: 'Follow-up Question',
        timeRemaining: 'Time Remaining',
        recordBtn: 'Start Answering (Record)',
        stopRecordBtn: 'Finish Answer & Submit',
        skipBtn: 'Skip Question',
        endInterviewBtn: 'End Interview',
        confirmEndTitle: 'End Interview Early?',
        confirmEndDesc: 'Your answers so far will be saved and assessed. Unanswered questions will not be scored.',
        confirmEndYes: 'Yes, End Interview',
        confirmEndCancel: 'Continue Interview',
        liveTranscript: 'Your Spoken Transcript',
        transcriptPlaceholder: 'Your words will appear here once audio transcription finishes...',
        ttsMute: 'Mute Voice',
        ttsUnmute: 'Unmute Voice',
      },
      evaluating: {
        title: 'Generating Your Assessment...',
        subtitle: 'Analyzing your answers against technical rubrics for completeness, depth, and clarity.',
        stage1: 'Transcribing and organizing answers...',
        stage2: 'Evaluating semantic correctness & technical depth...',
        stage3: 'Aggregating skill matrix & identifying weak areas...',
        stage4: 'Synthesizing targeted recommendations...',
        waitNotice: 'Processing locally via Ollama. This may take 30–60 seconds.',
      },
      assessment: {
        title: 'Interview Assessment & Skills Report',
        overallScore: 'Overall Score',
        disclaimer: 'This is an AI-generated practice assessment only. It does not predict real interview outcomes or hiring decisions.',
        summaryTitle: 'Performance Summary',
        skillMatrixTitle: 'Technical Skill Matrix',
        weakAreasTitle: 'Identified Areas for Improvement',
        recommendationsTitle: 'Targeted Study Plan',
        questionReviewTitle: 'Question-by-Question Review',
        repracticeBtn: 'Practice My Weak Areas',
        newInterviewBtn: 'Start New Interview',
        backToPrepBtn: 'Back to Prep Center',
        ratingStrong: 'Strong',
        ratingModerate: 'Moderate',
        ratingWeak: 'Weak',
        correctness: 'Correctness',
        completeness: 'Completeness',
        technicalDepth: 'Technical Depth',
        clarity: 'Clarity',
        missingConcepts: 'Missing Concepts',
        incorrectClaims: 'Incorrect Claims',
        positivePoints: 'Demonstrated Strengths',
        improvementPoints: 'Improvement Points',
        betterAnswer: 'Better Answer Guidance',
        yourAnswer: 'Your Answer',
      },
      history: {
        title: 'Interview History',
        empty: 'No completed mock interviews yet.',
        startFirstBtn: 'Start Your First Mock Interview',
        score: 'Score',
        date: 'Date',
        duration: 'Duration',
        questions: 'Questions',
        viewAssessment: 'View Assessment',
        backBtn: 'Back to Setup',
      },
    },
  },
  fr: {
    applications: applicationsTranslations.fr,
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
    guide: {
      tableOfContents: 'Table des matières',
      searchPlaceholder: 'Rechercher dans la documentation, extension, ATS, matching, FAQ...',
      groupGettingStarted: 'Prise en main',
      groupResumeStudio: 'Studio CV',
      groupBrowserExtension: 'Extension Navigateur',
      groupJobDiscovery: 'Découverte d\'Offres',
      groupApplicationTracking: 'Suivi des Candidatures',
      groupDataSupervision: 'Supervision & Scraping',
      groupDeveloper: 'Guide Développeur',
      groupHelp: 'Aide & FAQ',
      githubRepo: 'Dépôt GitHub',
      reportIssue: 'Signaler un problème',
      discussions: 'Discussions',
      watchDemo: 'Voir la démo',
      copyCode: 'Copier',
      copied: 'Copié !',
      searchNoResults: 'Aucune section ne correspond à votre recherche.',
    },
    mockInterview: {
      setup: {
        title: 'Simulation d\'Entretien Technique IA',
        subtitle: 'Simulez un entretien oral réaliste avec questions adaptatives et évaluation détaillée.',
        domainLabel: 'Filière Technique',
        roleLabel: 'Rôle visé (Optionnel)',
        difficultyLabel: 'Niveau de Difficulté',
        durationLabel: 'Durée de l\'Entretien',
        detectDomainBtn: 'Analyser mon CV',
        analyzingResume: 'Analyse du CV...',
        aiSuggestedBadge: 'Suggéré par l\'IA',
        aiSuggestedNote: 'Suggéré à partir de votre CV actif. Modifiable à tout moment.',
        startBtn: 'Vérifier la Configuration',
        historyBtn: 'Entretiens Passés',
        plannedQuestions: 'Questions Estimées',
        difficultyFundamental: 'Fondamental',
        difficultyIntermediate: 'Intermédiaire',
        difficultyAdvanced: 'Avancé',
        difficultyMixed: 'Mixte (Adaptatif)',
        minutes: 'minutes',
      },
      permission: {
        title: 'Vérification Pré-Entretien & Confidentialité',
        micRequired: 'Accès Microphone Requis',
        micDesc: 'Votre micro enregistre vos réponses orales. Le son est traité localement sur votre appareil.',
        cameraNotice: 'La caméra n\'est pas requise — c\'est un entretien purement vocal.',
        privacyHeader: 'Garantie de Confidentialité Locale',
        sttLocal: 'La reconnaissance vocale s\'exécute localement avec faster-whisper.',
        audioDiscarded: 'L\'audio brut est immédiatement supprimé après transcription — jamais conservé.',
        llmLocal: 'L\'évaluation et les relances sont gérées en local par Ollama.',
        testMicBtn: 'Tester le Microphone',
        micReady: 'Microphone vérifié et prêt !',
        micError: 'Accès micro refusé. Veuillez autoriser le microphone dans votre navigateur.',
        beginInterviewBtn: 'Démarrer l\'Entretien',
        backBtn: 'Retour à la Configuration',
      },
      interview: {
        interviewerStateSpeaking: 'L\'interviewer parle...',
        interviewerStateListening: 'Écoute de votre réponse...',
        interviewerStateProcessing: 'Traitement de la réponse...',
        turnIndicator: 'Question',
        followUpBadge: 'Question de Suivi',
        timeRemaining: 'Temps Restant',
        recordBtn: 'Répondre (Enregistrer)',
        stopRecordBtn: 'Terminer & Soumettre',
        skipBtn: 'Passer la Question',
        endInterviewBtn: 'Mettre Fin à l\'Entretien',
        confirmEndTitle: 'Arrêter l\'entretien plus tôt ?',
        confirmEndDesc: 'Vos réponses fournies seront enregistrées et évaluées.',
        confirmEndYes: 'Oui, terminer',
        confirmEndCancel: 'Continuer l\'entretien',
        liveTranscript: 'Votre Transcription Orale',
        transcriptPlaceholder: 'Vos propos apparaîtront ici après la transcription...',
        ttsMute: 'Couper la voix',
        ttsUnmute: 'Activer la voix',
      },
      evaluating: {
        title: 'Génération de votre Évaluation...',
        subtitle: 'Analyse de vos réponses par rapport aux rubriques techniques de précision et clarté.',
        stage1: 'Transcription et organisation des réponses...',
        stage2: 'Évaluation de la justesse sémantique et profondeur...',
        stage3: 'Calcul de la matrice de compétences et points faibles...',
        stage4: 'Génération de recommandations ciblées...',
        waitNotice: 'Traitement local via Ollama. Cela peut prendre 30 à 60 secondes.',
      },
      assessment: {
        title: 'Rapport d\'Évaluation & Compétences',
        overallScore: 'Score Global',
        disclaimer: 'Ceci est un outil d\'entraînement assisté par IA. Il ne prédit pas un résultat de recrutement réel.',
        summaryTitle: 'Résumé de Performance',
        skillMatrixTitle: 'Matrice de Compétences Techniques',
        weakAreasTitle: 'Axes d\'Amélioration Identifiés',
        recommendationsTitle: 'Plan d\'Étude Personnalisé',
        questionReviewTitle: 'Revue Question par Question',
        repracticeBtn: 'Travailler mes Points Faibles',
        newInterviewBtn: 'Nouvel Entretien',
        backToPrepBtn: 'Retour au Centre de Préparation',
        ratingStrong: 'Solide',
        ratingModerate: 'Moyen',
        ratingWeak: 'Faible',
        correctness: 'Exactitude',
        completeness: 'Complétude',
        technicalDepth: 'Profondeur Technique',
        clarity: 'Clarté',
        missingConcepts: 'Concepts Manquants',
        incorrectClaims: 'Affirmations Incorrectes',
        positivePoints: 'Points Forts Démontrés',
        improvementPoints: 'Points à Améliorer',
        betterAnswer: 'Conseils pour une Meilleure Réponse',
        yourAnswer: 'Votre Réponse',
      },
      history: {
        title: 'Historique des Entretiens',
        empty: 'Aucun entretien simulé terminé pour l\'instant.',
        startFirstBtn: 'Lancer votre premier entretien',
        score: 'Score',
        date: 'Date',
        duration: 'Durée',
        questions: 'Questions',
        viewAssessment: 'Voir l\'évaluation',
        backBtn: 'Retour',
      },
    },
  },
  de: {
    applications: applicationsTranslations.de,
    nav: {
      opportunities: 'Stellenangebote',
      internships: 'Praktika',
      profile: 'Match-Profil',
      applications: 'Bewerbungen',
      interviewPrep: 'Interview-Vorbereitung',
      companies: 'Unternehmens-Einblicke',
      supervision: 'Datenaufsicht',
      scraperHub: 'Scraper-Hub',
      guide: 'Anleitung & Docs',
      extension: 'Browser-Erweiterung',
      aiSettings: 'KI-Einstellungen',
      login: 'Anmelden',
      logout: 'Abmelden',
    },
    hero: {
      badge: 'Echtzeit-Karriereintelligenz',
      titlePrefix: 'Verifizierte Stellen, ',
      titleHighlight: 'Weltweit & Regional',
      titleSuffix: '',
      subtitle: 'Direkt von verifizierten Karriereportalen weltweit ohne Zwischenhändler.',
    },
    search: {
      placeholder: 'Nach Rolle, Fähigkeit, Tech-Stack oder Arbeitgeber suchen...',
      allCountries: 'Alle Länder',
      allModes: 'Alle Arbeitsmodelle',
      savedJobs: 'Gespeicherte Stellen',
      remote: 'Remote',
      hybrid: 'Hybrid',
      onsite: 'Vor Ort',
    },
    directory: {
      opportunitiesCount: 'aktive Stellenangebote gefunden',
      page: 'Seite',
      of: 'von',
      prev: 'Zurück',
      next: 'Weiter',
      noJobsFound: 'Keine Stellenangebote gefunden.',
      noJobsSub: 'Passen Sie Ihre Suchbegriffe, Filter oder das Land an.',
    },
    card: {
      match: 'Übereinstimmung',
      viewDetails: 'Details anzeigen',
      saved: 'Gespeichert',
      save: 'Speichern',
    },
    internships: {
      title: 'Kuratierte Tech-Praktika',
      subtitle: 'Direkt aus führenden GitHub-Repositories mit Visa-Status und Firmenlogos.',
      searchPlaceholder: 'Nach Firma, Rolle, Standort oder Stichwort suchen...',
      allRepos: 'Alle Repositories',
      allVisas: 'Alle Visa-Status',
      sponsorsVisa: 'Visum-Sponsoring',
      noSponsorship: 'Kein Sponsoring',
      usCitizenOnly: 'Nur US-Bürger',
      canadaEligible: 'Kanada-berechtigt',
      notSpecified: 'Nicht angegeben',
      allCategories: 'Alle Kategorien',
      openOnly: 'Nur Offene',
      totalListings: 'Gesamte Einträge',
      activeOpenings: 'Aktive Stellen',
      syncGithub: 'Mit GitHub synchronisieren',
      syncing: 'Synchronisiere...',
      clearFilters: 'Filter zurücksetzen',
      applyNow: 'Bewerben',
      closed: 'Geschlossen',
      matchingCount: 'passende Angebote',
      viewGrid: 'Rasteransicht',
      viewTable: 'Tabellenansicht',
    },
    modal: {
      posted: 'Veröffentlicht',
      employmentType: 'Anstellung',
      workMode: 'Modell',
      salary: 'Gehalt',
      matchAnalysis: 'Regelbasierte Match-Analyse',
      strengths: 'Übereinstimmende Stärken',
      missingSkills: 'Fehlende Fähigkeiten',
      description: 'Stellenbeschreibung',
      applyOnPortal: 'Auf Karriereportal bewerben',
      close: 'Schließen',
    },
    profile: {
      title: 'Kandidatenprofil & Match-Einstellungen',
      subtitle: 'Passen Sie Fähigkeiten, Präferenzen und Gehaltserwartungen an.',
      preferences: 'Karrierepräferenzen',
      skills: 'Fähigkeiten & Technologien',
      workMode: 'Bevorzugtes Arbeitsmodell',
      location: 'Bevorzugter Standort',
      expectedSalary: 'Mindestgehaltserwartung',
      saveChanges: 'Präferenzen speichern',
    },
    scraper: {
      title: 'Scraper Hub & Zielmonitor',
      subtitle: 'Live-Arbeitgeberziele, Robots.txt-Status und Synchronisationsläufe.',
      liveTargets: 'Konfigurierte Ziele',
      complianceNote: 'Alle Portale beachten robots.txt-Richtlinien.',
      sync: 'Ziel synchronisieren',
      syncing: 'Synchronisiere...',
      cooldown: 'In Wartezeit',
      disallowed: 'Durch Robots.txt gesperrt',
    },
    common: {
      loading: 'Wird geladen...',
      retry: 'Wiederholen',
      cancel: 'Abbrechen',
      save: 'Speichern',
      close: 'Schließen',
      export: 'Exportieren',
      all: 'Alle',
    },
    guide: {
      tableOfContents: 'Inhaltsverzeichnis',
      searchPlaceholder: 'Dokumentation, Erweiterung, ATS, FAQ durchsuchen...',
      groupGettingStarted: 'Erste Schritte',
      groupResumeStudio: 'Lebenslauf-Studio',
      groupBrowserExtension: 'Browser-Erweiterung',
      groupJobDiscovery: 'Stellensuche',
      groupApplicationTracking: 'Bewerbungsverwaltung',
      groupDataSupervision: 'Datenaufsicht & Scraping',
      groupDeveloper: 'Entwicklerhandbuch',
      groupHelp: 'Hilfe & FAQ',
      githubRepo: 'GitHub-Repository',
      reportIssue: 'Problem melden',
      discussions: 'Diskussionen',
      watchDemo: 'Demo ansehen',
      copyCode: 'Kopieren',
      copied: 'Kopiert!',
      searchNoResults: 'Keine passenden Abschnitte gefunden.',
    },
    mockInterview: {
      setup: {
        title: 'KI-Mock-Technik-Interview',
        subtitle: 'Simulieren Sie ein realistisches technisches Interview mit adaptiven Fragen und detaillierter Bewertung.',
        domainLabel: 'Fachbereich',
        roleLabel: 'Zielrolle (Optional)',
        difficultyLabel: 'Schwierigkeitsgrad',
        durationLabel: 'Interviewdauer',
        detectDomainBtn: 'Lebenslauf Analysieren',
        analyzingResume: 'Lebenslauf wird analysiert...',
        aiSuggestedBadge: 'KI-Vorschlag',
        aiSuggestedNote: 'Basierend auf Ihrem aktiven Lebenslauf. Jederzeit anpassbar.',
        startBtn: 'Weiter zur Überprüfung',
        historyBtn: 'Vergangene Interviews',
        plannedQuestions: 'Geschätzte Fragen',
        difficultyFundamental: 'Grundlagen',
        difficultyIntermediate: 'Mittelstufe',
        difficultyAdvanced: 'Fortgeschritten',
        difficultyMixed: 'Gemischt (Adaptiv)',
        minutes: 'Minuten',
      },
      permission: {
        title: 'Interview-Vorbereitung & Datenschutz',
        micRequired: 'Mikrofonzugriff Erforderlich',
        micDesc: 'Ihr Mikrofon erfasst Ihre gesprochenen Antworten. Das Audio wird lokal verarbeitet.',
        cameraNotice: 'Kamera wird nicht benötigt — rein sprachbasiertes technisches Interview.',
        privacyHeader: 'Lokale Datenschutz-Garantie',
        sttLocal: 'Spracherkennung läuft lokal über faster-whisper.',
        audioDiscarded: 'Audioaufnahmen werden sofort nach der Transkription gelöscht.',
        llmLocal: 'Bewertung und Nachfragen laufen lokal mit Ollama.',
        testMicBtn: 'Mikrofon Testen',
        micReady: 'Mikrofon geprüft & bereit!',
        micError: 'Mikrofonzugriff verweigert. Bitte Berechtigung im Browser erteilen.',
        beginInterviewBtn: 'Interview Starten',
        backBtn: 'Zurück zur Konfiguration',
      },
      interview: {
        interviewerStateSpeaking: 'Interviewer spricht...',
        interviewerStateListening: 'Hört Ihrer Antwort zu...',
        interviewerStateProcessing: 'Antwort wird verarbeitet...',
        turnIndicator: 'Frage',
        followUpBadge: 'Nachfrage',
        timeRemaining: 'Verbleibende Zeit',
        recordBtn: 'Antworten (Aufnahme)',
        stopRecordBtn: 'Antwort Absenden',
        skipBtn: 'Frage Überspringen',
        endInterviewBtn: 'Interview Beenden',
        confirmEndTitle: 'Interview vorzeitig beenden?',
        confirmEndDesc: 'Ihre bisherigen Antworten werden gespeichert und bewertet.',
        confirmEndYes: 'Ja, beenden',
        confirmEndCancel: 'Weiter interviewen',
        liveTranscript: 'Ihre Gesprochene Transkription',
        transcriptPlaceholder: 'Ihre Worte erscheinen hier nach der Transkription...',
        ttsMute: 'Stummschalten',
        ttsUnmute: 'Ton Einschalten',
      },
      evaluating: {
        title: 'Bewertung wird Erstellt...',
        subtitle: 'Antworten werden anhand technischer Kriterien auf Tiefe und Genauigkeit geprüft.',
        stage1: 'Antworten transkribieren und strukturieren...',
        stage2: 'Semantische Korrektheit & Fachtiefe bewerten...',
        stage3: 'Kompetenzmatrix erstellen & Schwachstellen ermitteln...',
        stage4: 'Gezielte Empfehlungen zusammenstellen...',
        waitNotice: 'Lokale Verarbeitung mit Ollama. Kann 30–60 Sekunden dauern.',
      },
      assessment: {
        title: 'Interview-Bewertung & Kompetenzbericht',
        overallScore: 'Gesamtpunktzahl',
        disclaimer: 'Dies ist eine KI-Übungsbewertung. Sie prognostiziert keine tatsächliche Einstellungsentscheidung.',
        summaryTitle: 'Leistungszusammenfassung',
        skillMatrixTitle: 'Technische Kompetenzmatrix',
        weakAreasTitle: 'Identifizierte Verbesserungsbereiche',
        recommendationsTitle: 'Gezielter Lernplan',
        questionReviewTitle: 'Fragenanalyse',
        repracticeBtn: 'Schwachstellen Wiederholen',
        newInterviewBtn: 'Neues Interview Starten',
        backToPrepBtn: 'Zurück zum Vorbereitungszentrum',
        ratingStrong: 'Stark',
        ratingModerate: 'Mäßig',
        ratingWeak: 'Schwach',
        correctness: 'Korrektheit',
        completeness: 'Vollständigkeit',
        technicalDepth: 'Technische Tiefe',
        clarity: 'Klarheit',
        missingConcepts: 'Fehlende Konzepte',
        incorrectClaims: 'Fehlerhafte Aussagen',
        positivePoints: 'Stärken',
        improvementPoints: 'Verbesserungspotenzial',
        betterAnswer: 'Musterantwort-Hinweise',
        yourAnswer: 'Ihre Antwort',
      },
      history: {
        title: 'Interview-Historie',
        empty: 'Noch keine Mock-Interviews abgeschlossen.',
        startFirstBtn: 'Erstes Mock-Interview Starten',
        score: 'Punktzahl',
        date: 'Datum',
        duration: 'Dauer',
        questions: 'Fragen',
        viewAssessment: 'Bewertung Ansehen',
        backBtn: 'Zurück',
      },
    },
  },
  nl: {
    applications: applicationsTranslations.nl,
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
    guide: {
      tableOfContents: 'Inhoudsopgave',
      searchPlaceholder: 'Zoek in documentatie, extensie, ATS, matching, FAQ...',
      groupGettingStarted: 'Aan de slag',
      groupResumeStudio: 'CV Studio',
      groupBrowserExtension: 'Browserextensie',
      groupJobDiscovery: 'Vacature Ontdekking',
      groupApplicationTracking: 'Sollicitatiebeheer',
      groupDataSupervision: 'Gegevenstoezicht & Scraping',
      groupDeveloper: 'Ontwikkelaarsgids',
      groupHelp: 'Hulp & FAQ',
      githubRepo: 'GitHub Repository',
      reportIssue: 'Probleem Melden',
      discussions: 'Discussies',
      watchDemo: 'Demo Bekijken',
      copyCode: 'Kopiëren',
      copied: 'Gekopieerd!',
      searchNoResults: 'Geen secties gevonden die overeenkomen met uw zoekopdracht.',
    },
    mockInterview: {
      setup: {
        title: 'AI Proefinterview Techniek',
        subtitle: 'Simuleer een realistisch technisch mondeling interview met adaptieve vragen en diepgaande analyse.',
        domainLabel: 'Technisch Traject',
        roleLabel: 'Doelfunctie (Optioneel)',
        difficultyLabel: 'Moeilijkheidsgraad',
        durationLabel: 'Interviewduur',
        detectDomainBtn: 'Analyseer Mijn CV',
        analyzingResume: 'CV analyseren...',
        aiSuggestedBadge: 'AI-Suggestie',
        aiSuggestedNote: 'Voorgesteld op basis van uw actieve CV. U kunt dit altijd aanpassen.',
        startBtn: 'Doorgaan naar Controle',
        historyBtn: 'Eerdere Interviews',
        plannedQuestions: 'Geschatte Vragen',
        difficultyFundamental: 'Basis',
        difficultyIntermediate: 'Gemiddeld',
        difficultyAdvanced: 'Gevorderd',
        difficultyMixed: 'Gemengd (Adaptief)',
        minutes: 'minuten',
      },
      permission: {
        title: 'Voorbereiding & Privacy',
        micRequired: 'Microfoontoegang Vereist',
        micDesc: 'Uw microfoon registreert uw gesproken antwoorden. Audio wordt lokaal op uw apparaat verwerkt.',
        cameraNotice: 'Camera is niet nodig — dit is een puur mondeling technisch interview.',
        privacyHeader: 'Lokaal Privacybeleid',
        sttLocal: 'Spraak-naar-tekst draait lokaal via faster-whisper.',
        audioDiscarded: 'Ruwe audio wordt direct na transcriptie verwijderd — nooit opgeslagen.',
        llmLocal: 'Evaluatie en vervolgvragen draaien lokaal via Ollama.',
        testMicBtn: 'Microfoon Testen',
        micReady: 'Microfoon gecontroleerd & gereed!',
        micError: 'Microfoontoegang geweigerd. Geef toestemming in uw browser.',
        beginInterviewBtn: 'Interview Starten',
        backBtn: 'Terug naar Instellingen',
      },
      interview: {
        interviewerStateSpeaking: 'Interviewer spreekt...',
        interviewerStateListening: 'Luistert naar uw antwoord...',
        interviewerStateProcessing: 'Antwoord verwerken...',
        turnIndicator: 'Vraag',
        followUpBadge: 'Vervolgvraag',
        timeRemaining: 'Resterende Tijd',
        recordBtn: 'Antwoorden (Opnemen)',
        stopRecordBtn: 'Voltooien & Verzenden',
        skipBtn: 'Vraag Overslaan',
        endInterviewBtn: 'Interview Beëindigen',
        confirmEndTitle: 'Interview vroegtijdig beëindigen?',
        confirmEndDesc: 'Uw tot nu toe gegeven antwoorden worden bewaard en geëvalueerd.',
        confirmEndYes: 'Ja, beëindigen',
        confirmEndCancel: 'Doorgaan met interview',
        liveTranscript: 'Uw Gesproken Transcript',
        transcriptPlaceholder: 'Uw gesproken woorden verschijnen hier na transcriptie...',
        ttsMute: 'Geluid Dempen',
        ttsUnmute: 'Geluid Inschakelen',
      },
      evaluating: {
        title: 'Beoordeling Wordt Gegenereerd...',
        subtitle: 'Uw antwoorden worden geanalyseerd op technische volledigheid, diepgang en helderheid.',
        stage1: 'Antwoorden transcriberen en ordenen...',
        stage2: 'Semantische juistheid & diepgang beoordelen...',
        stage3: 'Vaardighedenmatrix samenstellen & verbeterpunten bepalen...',
        stage4: 'Gerichte studieaanbevelingen formuleren...',
        waitNotice: 'Lokale verwerking via Ollama. Dit kan 30–60 seconden duren.',
      },
      assessment: {
        title: 'Interviewbeoordeling & Vaardighedenrapport',
        overallScore: 'Totaalscore',
        disclaimer: 'Dit is een AI-oefenbeoordeling. Dit voorspelt geen daadwerkelijke selectie-uitslag.',
        summaryTitle: 'Prestatieoverzicht',
        skillMatrixTitle: 'Technische Vaardighedenmatrix',
        weakAreasTitle: 'Geïdentificeerde Verbeterpunten',
        recommendationsTitle: 'Gericht Studieplan',
        questionReviewTitle: 'Vraag-voor-Vraag Evaluatie',
        repracticeBtn: 'Mijn Zwakke Punten Oefenen',
        newInterviewBtn: 'Nieuw Interview Starten',
        backToPrepBtn: 'Terug naar Voorbereiding',
        ratingStrong: 'Sterk',
        ratingModerate: 'Matig',
        ratingWeak: 'Zwak',
        correctness: 'Juistheid',
        completeness: 'Volledigheid',
        technicalDepth: 'Technische Diepgang',
        clarity: 'Helderheid',
        missingConcepts: 'Ontbrekende Concepten',
        incorrectClaims: 'Onjuiste Beweringen',
        positivePoints: 'Sterke Punten',
        improvementPoints: 'Verbesserpunten',
        betterAnswer: 'Tips voor een Beter Antwoord',
        yourAnswer: 'Uw Antwoord',
      },
      history: {
        title: 'Interviewgeschiedenis',
        empty: 'Nog geen afgeronde proefinterviews.',
        startFirstBtn: 'Start Uw Eerste Proefinterview',
        score: 'Score',
        date: 'Datum',
        duration: 'Duur',
        questions: 'Vragen',
        viewAssessment: 'Beoordeling Bekijken',
        backBtn: 'Terug',
      },
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
      return saved === 'fr' || saved === 'de' || saved === 'nl' ? saved : 'en';
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
