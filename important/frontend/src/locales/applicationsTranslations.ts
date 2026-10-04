import type { Language } from '../i18n';

export interface ApplicationsTranslations {
  // Page header & navigation
  pageTitle: string;
  pageSubtitle: string;
  tabApplications: string;
  tabContacts: string;
  viewSpreadsheet: string;
  viewKanban: string;
  viewFunnel: string;
  btnAddApplication: string;
  btnRefresh: string;
  btnExportXlsx: string;
  btnImportXlsx: string;
  exporting: string;
  refreshing: string;

  // Statistics KPI Bar
  statTotalApplications: string;
  statInterviewRate: string;
  statResponseRate: string;
  statOffers: string;
  statAcceptedOffers: string;
  statActivePipeline: string;
  statInterviewsScheduled: string;
  statAppsThisWeek: string;
  statAvgResponseTime: string;
  daysUnit: string;

  // Action Needed Section
  actionNeededTitle: string;
  actionNeededSubtitle: string;
  actionWaitingResponse: string;
  actionFollowUp: string;
  actionPriorityFollowUp: string;
  actionUpcomingInterviews: string;
  actionOverdue: string;
  actionNoResponse: string;
  actionNextStep: string;
  actionNoActionsNeeded: string;
  actionBtnComplete: string;
  actionBtnSnooze: string;
  actionBtnReschedule: string;
  actionBtnCancel: string;
  timeToday: string;
  timeTomorrow: string;
  timeYesterday: string;
  timeDaysAgo: string; // e.g. "{n} days ago"
  timeInDays: string; // e.g. "In {n} days"
  timeOverdueBy: string; // e.g. "Overdue by {n} days"

  // Workspace Controls & Filters
  searchPlaceholder: string;
  filterAllSources: string;
  filterAllStatuses: string;
  filterAllPriorities: string;
  filterStageActive: string;
  btnClearFilter: string;
  showingCount: string; // e.g. "Showing {count} of {total} applications"
  loadingApplications: string;
  noAppsFoundTitle: string;
  noAppsFoundSubtitle: string;

  // Stages & Statuses
  stageSaved: string;
  stageApplied: string;
  stageInterviewing: string;
  stage1stInterview: string;
  stage2ndInterview: string;
  stage3rdInterview: string;
  stageFinalInterview: string;
  stageOffer: string;
  stageAccepted: string;
  stageRejected: string;
  stageWithdrawn: string;
  stageNoAnswer: string;

  // Priorities
  priorityHigh: string;
  priorityMedium: string;
  priorityLow: string;

  // Table Columns & UI
  colJobTitle: string;
  colCompany: string;
  colStatus: string;
  colPriority: string;
  colSource: string;
  colLocation: string;
  colSalary: string;
  colAppliedDate: string;
  colFollowUp: string;
  colRecruiter: string;
  colNotes: string;
  colActions: string;
  editNotesPlaceholder: string;
  btnSave: string;
  btnCancel: string;

  // Kanban View
  kanbanColSaved: string;
  kanbanColApplied: string;
  kanbanColInterviewing: string;
  kanbanColOffers: string;
  kanbanColArchived: string;
  kanbanDragHint: string;
  kanbanEmptyCol: string;

  // Funnel View
  funnelTitle: string;
  funnelSubtitle: string;
  funnelInteractiveHint: string;
  funnelApplications: string;
  funnelInterviews: string;
  funnelOffers: string;
  funnelAccepted: string;

  // Application Detail Drawer
  drawerTitle: string;
  drawerTabOverview: string;
  drawerTabTimeline: string;
  drawerTabIntelligence: string;
  drawerTabResume: string;
  drawerFieldCompany: string;
  drawerFieldTitle: string;
  drawerFieldLocation: string;
  drawerFieldSource: string;
  drawerFieldSalary: string;
  drawerFieldEmploymentType: string;
  drawerFieldAppliedDate: string;
  drawerFieldFollowUp: string;
  drawerFieldRecruiter: string;
  drawerFieldPriority: string;
  drawerFieldStatus: string;
  drawerFieldNotes: string;
  drawerBtnEdit: string;
  drawerBtnDelete: string;
  drawerConfirmDelete: string;

  // Contacts & Recruiter CRM
  contactsTitle: string;
  contactsSubtitle: string;
  contactsSearchPlaceholder: string;
  contactsAllCompanies: string;
  btnAddContact: string;
  btnImportContacts: string;
  btnExportContacts: string;
  contactsLoading: string;
  contactsEmptyTitle: string;
  contactsEmptySubtitle: string;
  contactsEmptySearch: string;
  contactsAddFirstBtn: string;
  contactsImportFirstBtn: string;

  // Communication Statuses
  commNotContacted: string;
  commContactedNoResponse: string;
  commResponded: string;
  commAwaitingReply: string;
  commStateLabel: string;
  commLastContacted: string;
  commLastResponse: string;
  commNextAction: string;
  commRelatedApps: string;
  commMethodEmail: string;
  commMethodLinkedIn: string;
  commMethodPhone: string;
  commMethodOther: string;

  // Add Contact Modal
  addContactModalTitle: string;
  addContactModalSubtitle: string;
  addContactSecIdentity: string;
  addContactSecCommunication: string;
  addContactSecAdditional: string;
  addContactFirstName: string;
  addContactLastName: string;
  addContactCompany: string;
  addContactRole: string;
  addContactEmail: string;
  addContactPhone: string;
  addContactLinkedIn: string;
  addContactLocation: string;
  addContactTags: string;
  addContactNotes: string;
  addContactQuestionContacted: string;
  addContactOptionYes: string;
  addContactOptionNo: string;
  addContactMethodLabel: string;
  addContactDateLabel: string;
  addContactEmailUsedLabel: string;
  addContactQuestionResponse: string;
  addContactResponseDateLabel: string;
  addContactResponseNotesLabel: string;
  addContactBtnCreate: string;
  addContactBtnSaving: string;
  addContactDuplicateWarning: string;
  addContactFirstNameRequired: string;

  // Contact Detail Drawer
  contactDrawerLoading: string;
  contactDrawerNotFound: string;
  contactDrawerEditTitle: string;
  contactDrawerSaveEdit: string;
  contactDrawerLogInteractionBtn: string;
  contactDrawerInteractionTitle: string;
  contactDrawerInteractionType: string;
  contactDrawerInteractionNotes: string;
  contactDrawerInteractionDate: string;
  contactDrawerTimelineTitle: string;
  contactDrawerNoInteractions: string;
  contactDrawerConfirmDelete: string;

  // Analytics Section
  analyticsSectionTitle: string;
  analyticsSectionSubtitle: string;
  analyticsSourceTitle: string;
  analyticsSourceSubtitle: string;
  analyticsStageTitle: string;
  analyticsStageSubtitle: string;
  analyticsRadarTitle: string;
  analyticsRadarSubtitle: string;
  analyticsRadarVolume: string;
  analyticsRadarResponseRate: string;
  analyticsRadarInterviewYield: string;
  analyticsRadarOfferRate: string;
  analyticsRadarMomentum: string;
  analyticsRadarDiversity: string;
  analyticsHeatmapTitle: string;
  analyticsHeatmapSubtitle: string;
  analyticsHeatmapLess: string;
  analyticsHeatmapMore: string;
  analyticsHeatmapTooltip: string; // e.g. "{count} applications on {date}"

  // Quick Navigation Dock
  quickNavAnalytics: string;
  quickNavTop: string;
  quickNavBottom: string;
  quickNavScrollToAnalytics: string;
  quickNavScrollToTop: string;
  quickNavScrollToBottom: string;
}

export const applicationsTranslations: Record<Language, ApplicationsTranslations> = {
  en: {
    pageTitle: 'Job Applications',
    pageSubtitle: 'Track, organize, and accelerate your job search pipeline with verified intelligence.',
    tabApplications: 'Applications Workspace',
    tabContacts: 'Contacts & Recruiters',
    viewSpreadsheet: 'Table',
    viewKanban: 'Board',
    viewFunnel: 'Funnel',
    btnAddApplication: 'Add Application',
    btnRefresh: 'Refresh',
    btnExportXlsx: 'Export Excel (.xlsx)',
    btnImportXlsx: 'Import Excel',
    exporting: 'Exporting...',
    refreshing: 'Refreshing...',

    statTotalApplications: 'Total Applications',
    statInterviewRate: 'Interview Rate',
    statResponseRate: 'Response Rate',
    statOffers: 'Offers',
    statAcceptedOffers: 'Accepted Offers',
    statActivePipeline: 'Active Pipeline',
    statInterviewsScheduled: 'Interviews Scheduled',
    statAppsThisWeek: 'This Week',
    statAvgResponseTime: 'Avg Response Time',
    daysUnit: 'days',

    actionNeededTitle: 'Action Needed',
    actionNeededSubtitle: 'Priority tasks, upcoming interviews, and follow-ups requiring your attention.',
    actionWaitingResponse: 'Waiting for Response',
    actionFollowUp: 'Follow-Up Due',
    actionPriorityFollowUp: 'Priority Follow-Up',
    actionUpcomingInterviews: 'Upcoming Interviews',
    actionOverdue: 'Overdue',
    actionNoResponse: 'No Response Yet',
    actionNextStep: 'Next Step',
    actionNoActionsNeeded: 'All caught up! No urgent follow-ups or pending actions right now.',
    actionBtnComplete: 'Done',
    actionBtnSnooze: 'Snooze',
    actionBtnReschedule: 'Reschedule',
    actionBtnCancel: 'Dismiss',
    timeToday: 'Today',
    timeTomorrow: 'Tomorrow',
    timeYesterday: 'Yesterday',
    timeDaysAgo: '{n} days ago',
    timeInDays: 'In {n} days',
    timeOverdueBy: 'Overdue by {n} days',

    searchPlaceholder: 'Search applications by title, company, or location...',
    filterAllSources: 'All Sources',
    filterAllStatuses: 'All Statuses',
    filterAllPriorities: 'All Priorities',
    filterStageActive: 'Filtered by funnel stage: {stage}',
    btnClearFilter: 'Clear filter',
    showingCount: 'Showing {count} of {total} applications',
    loadingApplications: 'Loading applications and pipeline data...',
    noAppsFoundTitle: 'No applications found',
    noAppsFoundSubtitle: 'No applications match your active search and filter criteria.',

    stageSaved: 'Saved / Bookmarked',
    stageApplied: 'Applied',
    stageInterviewing: 'Interviewing',
    stage1stInterview: '1st Interview',
    stage2ndInterview: '2nd Interview',
    stage3rdInterview: '3rd Interview',
    stageFinalInterview: 'Final Interview',
    stageOffer: 'Offer Received',
    stageAccepted: 'Offer Accepted',
    stageRejected: 'Archived / Rejected',
    stageWithdrawn: 'Withdrawn',
    stageNoAnswer: 'No Answer',

    priorityHigh: 'High',
    priorityMedium: 'Medium',
    priorityLow: 'Low',

    colJobTitle: 'Job Title',
    colCompany: 'Company',
    colStatus: 'Status',
    colPriority: 'Priority',
    colSource: 'Source',
    colLocation: 'Location',
    colSalary: 'Salary',
    colAppliedDate: 'Applied Date',
    colFollowUp: 'Follow-Up',
    colRecruiter: 'Contact / Recruiter',
    colNotes: 'Notes',
    colActions: 'Actions',
    editNotesPlaceholder: 'Add private notes...',
    btnSave: 'Save',
    btnCancel: 'Cancel',

    kanbanColSaved: 'Saved / Bookmarked',
    kanbanColApplied: 'Applied',
    kanbanColInterviewing: 'Interviewing',
    kanbanColOffers: 'Offers',
    kanbanColArchived: 'Archived / Rejected',
    kanbanDragHint: 'Drag cards to transition status',
    kanbanEmptyCol: 'No applications in this stage',

    funnelTitle: 'Recruitment Pipeline Funnel',
    funnelSubtitle: 'Track progression through each stage of your hiring pipeline with direct conversion metrics.',
    funnelInteractiveHint: 'Click any funnel stage to filter the table below',
    funnelApplications: 'Applications',
    funnelInterviews: 'Interviews',
    funnelOffers: 'Offers',
    funnelAccepted: 'Accepted',

    drawerTitle: 'Application Details',
    drawerTabOverview: 'Overview',
    drawerTabTimeline: 'Timeline',
    drawerTabIntelligence: 'AI Insights',
    drawerTabResume: 'Resume Tailoring',
    drawerFieldCompany: 'Company',
    drawerFieldTitle: 'Job Title',
    drawerFieldLocation: 'Location',
    drawerFieldSource: 'Source',
    drawerFieldSalary: 'Salary',
    drawerFieldEmploymentType: 'Employment Type',
    drawerFieldAppliedDate: 'Applied Date',
    drawerFieldFollowUp: 'Next Follow-Up',
    drawerFieldRecruiter: 'Recruiter / Contact',
    drawerFieldPriority: 'Priority',
    drawerFieldStatus: 'Status',
    drawerFieldNotes: 'Notes & Context',
    drawerBtnEdit: 'Edit Application',
    drawerBtnDelete: 'Delete',
    drawerConfirmDelete: 'Are you sure you want to delete this application?',

    contactsTitle: 'Application Contacts & Recruiters',
    contactsSubtitle: 'Manage relationships with recruiters, talent partners, and hiring managers across your pipeline.',
    contactsSearchPlaceholder: 'Search contacts by name, company, email, role, or tags...',
    contactsAllCompanies: 'All Companies',
    btnAddContact: 'Add Contact',
    btnImportContacts: 'Import Excel',
    btnExportContacts: 'Export Excel (.xlsx)',
    contactsLoading: 'Loading application contacts and interaction logs...',
    contactsEmptyTitle: 'No contacts found',
    contactsEmptySubtitle: 'Contacts linked to job applications or imported from Excel will appear here.',
    contactsEmptySearch: 'No contacts match your current search criteria.',
    contactsAddFirstBtn: 'Add First Contact',
    contactsImportFirstBtn: 'Import from Excel',

    commNotContacted: 'Not Contacted',
    commContactedNoResponse: 'Contacted, No Response',
    commResponded: 'Contacted & Responded',
    commAwaitingReply: 'Awaiting Reply',
    commStateLabel: 'Communication State',
    commLastContacted: 'Last Contacted',
    commLastResponse: 'Last Response',
    commNextAction: 'Next Action',
    commRelatedApps: 'Related Applications',
    commMethodEmail: 'Email',
    commMethodLinkedIn: 'LinkedIn',
    commMethodPhone: 'Phone',
    commMethodOther: 'Other',

    addContactModalTitle: 'Add Contact / Recruiter',
    addContactModalSubtitle: 'Keep track of recruiters, hiring managers, and HR partners for your applications.',
    addContactSecIdentity: 'Contact Information',
    addContactSecCommunication: 'Communication & Relationship (Optional)',
    addContactSecAdditional: 'Additional Information',
    addContactFirstName: 'First Name *',
    addContactLastName: 'Last Name',
    addContactCompany: 'Company',
    addContactRole: 'Role / Title',
    addContactEmail: 'Email Address',
    addContactPhone: 'Phone Number',
    addContactLinkedIn: 'LinkedIn Profile URL',
    addContactLocation: 'Location',
    addContactTags: 'Tags (comma separated)',
    addContactNotes: 'Notes & Context',
    addContactQuestionContacted: 'Have you contacted this person?',
    addContactOptionYes: 'Yes',
    addContactOptionNo: 'No (Not Contacted)',
    addContactMethodLabel: 'Contact Method',
    addContactDateLabel: 'Date Contacted (Optional)',
    addContactEmailUsedLabel: 'Email Address Used (Optional)',
    addContactQuestionResponse: 'Response received?',
    addContactResponseDateLabel: 'Response Date (Optional)',
    addContactResponseNotesLabel: 'Response Notes (Optional)',
    addContactBtnCreate: 'Create Contact',
    addContactBtnSaving: 'Saving Contact...',
    addContactDuplicateWarning: 'Existing Contact Found',
    addContactFirstNameRequired: 'First name is required.',

    contactDrawerLoading: 'Loading contact details & communication history...',
    contactDrawerNotFound: 'Contact not found.',
    contactDrawerEditTitle: 'Edit Contact Info',
    contactDrawerSaveEdit: 'Save Changes',
    contactDrawerLogInteractionBtn: 'Log Interaction',
    contactDrawerInteractionTitle: 'Log Communication / Interaction',
    contactDrawerInteractionType: 'Interaction Type',
    contactDrawerInteractionNotes: 'Summary / Notes',
    contactDrawerInteractionDate: 'Date',
    contactDrawerTimelineTitle: 'Interaction History',
    contactDrawerNoInteractions: 'No interactions logged yet. Log an email, call, or outreach above.',
    contactDrawerConfirmDelete: 'Are you sure you want to remove this contact?',

    analyticsSectionTitle: 'Job Search Analytics',
    analyticsSectionSubtitle: 'Comprehensive insights into your application conversion, sources, and submission cadence.',
    analyticsSourceTitle: 'Source Analytics & Channel Yield',
    analyticsSourceSubtitle: 'Compare response and interview rates across job boards and platforms.',
    analyticsStageTitle: 'Stage Distribution',
    analyticsStageSubtitle: 'Current distribution of applications across pipeline stages.',
    analyticsRadarTitle: 'Pipeline Health Radar',
    analyticsRadarSubtitle: 'Multi-axis evaluation of your application momentum and response efficiency.',
    analyticsRadarVolume: 'Volume',
    analyticsRadarResponseRate: 'Response Rate',
    analyticsRadarInterviewYield: 'Interview Yield',
    analyticsRadarOfferRate: 'Offer Rate',
    analyticsRadarMomentum: 'Momentum',
    analyticsRadarDiversity: 'Source Diversity',
    analyticsHeatmapTitle: 'Application Activity Heatmap',
    analyticsHeatmapSubtitle: 'Submission consistency over the past 365 days.',
    analyticsHeatmapLess: 'Less',
    analyticsHeatmapMore: 'More',
    analyticsHeatmapTooltip: '{count} applications on {date}',

    quickNavAnalytics: 'Analytics',
    quickNavTop: 'Top',
    quickNavBottom: 'Bottom',
    quickNavScrollToAnalytics: 'Scroll down to Job Search Analytics',
    quickNavScrollToTop: 'Scroll back to top',
    quickNavScrollToBottom: 'Scroll down to bottom',
  },
  fr: {
    pageTitle: 'Candidatures',
    pageSubtitle: 'Suivez, organisez et accélérez votre pipeline de recherche avec des données vérifiées.',
    tabApplications: 'Espace Candidatures',
    tabContacts: 'Contacts & Recruteurs',
    viewSpreadsheet: 'Tableau',
    viewKanban: 'Tableau Kanban',
    viewFunnel: 'Entonnoir',
    btnAddApplication: 'Ajouter une Candidature',
    btnRefresh: 'Actualiser',
    btnExportXlsx: 'Exporter Excel (.xlsx)',
    btnImportXlsx: 'Importer Excel',
    exporting: 'Exportation...',
    refreshing: 'Actualisation...',

    statTotalApplications: 'Total Candidatures',
    statInterviewRate: "Taux d'Entretien",
    statResponseRate: 'Taux de Réponse',
    statOffers: 'Offres Reçues',
    statAcceptedOffers: 'Offres Acceptées',
    statActivePipeline: 'Pipeline Actif',
    statInterviewsScheduled: 'Entretiens Prévus',
    statAppsThisWeek: 'Cette Semaine',
    statAvgResponseTime: 'Délai Moyen de Réponse',
    daysUnit: 'jours',

    actionNeededTitle: 'Actions Requises',
    actionNeededSubtitle: 'Tâches prioritaires, entretiens à venir et relances nécessitant votre attention.',
    actionWaitingResponse: 'En Attente de Réponse',
    actionFollowUp: 'Relance à Effectuer',
    actionPriorityFollowUp: 'Relance Prioritaire',
    actionUpcomingInterviews: 'Entretiens à Venir',
    actionOverdue: 'En Retard',
    actionNoResponse: 'Sans Réponse pour l’instant',
    actionNextStep: 'Étape Suivante',
    actionNoActionsNeeded: 'Tout est à jour ! Aucune relance urgente ou action en attente actuellement.',
    actionBtnComplete: 'Terminé',
    actionBtnSnooze: 'Reporter',
    actionBtnReschedule: 'Reprogrammer',
    actionBtnCancel: 'Ignorer',
    timeToday: "Aujourd'hui",
    timeTomorrow: 'Demain',
    timeYesterday: 'Hier',
    timeDaysAgo: 'Il y a {n} jours',
    timeInDays: 'Dans {n} jours',
    timeOverdueBy: 'En retard de {n} jours',

    searchPlaceholder: 'Rechercher par poste, entreprise ou lieu...',
    filterAllSources: 'Toutes les Sources',
    filterAllStatuses: 'Tous les Statuts',
    filterAllPriorities: 'Toutes les Priorités',
    filterStageActive: "Filtré par étape d'entonnoir : {stage}",
    btnClearFilter: 'Effacer le filtre',
    showingCount: 'Affichage de {count} sur {total} candidatures',
    loadingApplications: 'Chargement des candidatures et du pipeline...',
    noAppsFoundTitle: 'Aucune candidature trouvée',
    noAppsFoundSubtitle: 'Aucune candidature ne correspond à vos critères de recherche actuels.',

    stageSaved: 'Enregistrée / Favori',
    stageApplied: 'Postulée',
    stageInterviewing: 'Entretiens en cours',
    stage1stInterview: '1er Entretien',
    stage2ndInterview: '2ème Entretien',
    stage3rdInterview: '3ème Entretien',
    stageFinalInterview: 'Entretien Final',
    stageOffer: 'Offre Reçue',
    stageAccepted: 'Offre Acceptée',
    stageRejected: 'Archivée / Refusée',
    stageWithdrawn: 'Candidature Retirée',
    stageNoAnswer: 'Sans Réponse',

    priorityHigh: 'Haute',
    priorityMedium: 'Moyenne',
    priorityLow: 'Basse',

    colJobTitle: 'Intitulé du Poste',
    colCompany: 'Entreprise',
    colStatus: 'Statut',
    colPriority: 'Priorité',
    colSource: 'Source',
    colLocation: 'Localisation',
    colSalary: 'Salaire',
    colAppliedDate: 'Date de Candidature',
    colFollowUp: 'Relance',
    colRecruiter: 'Contact / Recruteur',
    colNotes: 'Notes',
    colActions: 'Actions',
    editNotesPlaceholder: 'Ajouter des notes privées...',
    btnSave: 'Enregistrer',
    btnCancel: 'Annuler',

    kanbanColSaved: 'Enregistrées',
    kanbanColApplied: 'Postulées',
    kanbanColInterviewing: 'Entretiens',
    kanbanColOffers: 'Offres',
    kanbanColArchived: 'Archivées / Refusées',
    kanbanDragHint: 'Glissez les cartes pour changer de statut',
    kanbanEmptyCol: 'Aucune candidature dans cette colonne',

    funnelTitle: 'Entonnoir de Recrutement',
    funnelSubtitle: 'Suivez la progression de vos candidatures à chaque étape avec les taux de conversion directs.',
    funnelInteractiveHint: "Cliquez sur une étape pour filtrer le tableau ci-dessous",
    funnelApplications: 'Candidatures',
    funnelInterviews: 'Entretiens',
    funnelOffers: 'Offres',
    funnelAccepted: 'Acceptées',

    drawerTitle: 'Détails de la Candidature',
    drawerTabOverview: 'Vue générale',
    drawerTabTimeline: 'Historique',
    drawerTabIntelligence: 'Analyses IA',
    drawerTabResume: 'Adaptation du CV',
    drawerFieldCompany: 'Entreprise',
    drawerFieldTitle: 'Intitulé du Poste',
    drawerFieldLocation: 'Localisation',
    drawerFieldSource: 'Source',
    drawerFieldSalary: 'Salaire',
    drawerFieldEmploymentType: "Type de contrat",
    drawerFieldAppliedDate: 'Date de candidature',
    drawerFieldFollowUp: 'Prochaine relance',
    drawerFieldRecruiter: 'Recruteur / Contact',
    drawerFieldPriority: 'Priorité',
    drawerFieldStatus: 'Statut',
    drawerFieldNotes: 'Notes & Contexte',
    drawerBtnEdit: 'Modifier',
    drawerBtnDelete: 'Supprimer',
    drawerConfirmDelete: 'Êtes-vous sûr de vouloir supprimer cette candidature ?',

    contactsTitle: 'Contacts & Recruteurs',
    contactsSubtitle: 'Gérez vos relations avec les recruteurs, RH et responsables de recrutement de votre pipeline.',
    contactsSearchPlaceholder: 'Rechercher par nom, entreprise, email, poste ou tags...',
    contactsAllCompanies: 'Toutes les Entreprises',
    btnAddContact: 'Ajouter un Contact',
    btnImportContacts: 'Importer Excel',
    btnExportContacts: 'Exporter Excel (.xlsx)',
    contactsLoading: 'Chargement des contacts et historiques de communication...',
    contactsEmptyTitle: 'Aucun contact trouvé',
    contactsEmptySubtitle: 'Les contacts associés à vos candidatures ou importés apparaîtront ici.',
    contactsEmptySearch: 'Aucun contact ne correspond à votre recherche.',
    contactsAddFirstBtn: 'Ajouter le Premier Contact',
    contactsImportFirstBtn: 'Importer depuis Excel',

    commNotContacted: 'Non contacté',
    commContactedNoResponse: 'Contacté, sans réponse',
    commResponded: 'Contacté & Répondu',
    commAwaitingReply: 'En attente de réponse',
    commStateLabel: 'État de communication',
    commLastContacted: 'Dernier contact',
    commLastResponse: 'Dernière réponse',
    commNextAction: 'Prochaine action',
    commRelatedApps: 'Candidatures associées',
    commMethodEmail: 'E-mail',
    commMethodLinkedIn: 'LinkedIn',
    commMethodPhone: 'Téléphone',
    commMethodOther: 'Autre',

    addContactModalTitle: 'Ajouter un Contact / Recruteur',
    addContactModalSubtitle: 'Enregistrez les recruteurs et responsables RH pour vos candidatures.',
    addContactSecIdentity: 'Informations de Contact',
    addContactSecCommunication: 'Communication & Relation (Optionnel)',
    addContactSecAdditional: 'Informations Complémentaires',
    addContactFirstName: 'Prénom *',
    addContactLastName: 'Nom',
    addContactCompany: 'Entreprise',
    addContactRole: 'Poste / Fonction',
    addContactEmail: 'Adresse E-mail',
    addContactPhone: 'Numéro de Téléphone',
    addContactLinkedIn: 'Profil LinkedIn',
    addContactLocation: 'Localisation',
    addContactTags: 'Tags (séparés par des virgules)',
    addContactNotes: 'Notes & Contexte',
    addContactQuestionContacted: 'Avez-vous déjà contacté cette personne ?',
    addContactOptionYes: 'Oui',
    addContactOptionNo: 'Non (Pas encore contacté)',
    addContactMethodLabel: 'Moyen de contact',
    addContactDateLabel: 'Date du premier contact (Optionnel)',
    addContactEmailUsedLabel: 'E-mail utilisé (Optionnel)',
    addContactQuestionResponse: 'Réponse reçue ?',
    addContactResponseDateLabel: 'Date de la réponse (Optionnel)',
    addContactResponseNotesLabel: 'Notes sur la réponse (Optionnel)',
    addContactBtnCreate: 'Créer le Contact',
    addContactBtnSaving: 'Enregistrement...',
    addContactDuplicateWarning: 'Contact existant trouvé',
    addContactFirstNameRequired: 'Le prénom est requis.',

    contactDrawerLoading: 'Chargement des détails et de l’historique...',
    contactDrawerNotFound: 'Contact introuvable.',
    contactDrawerEditTitle: 'Modifier les Informations',
    contactDrawerSaveEdit: 'Enregistrer les Modifications',
    contactDrawerLogInteractionBtn: 'Ajouter une Interaction',
    contactDrawerInteractionTitle: 'Enregistrer une Interaction',
    contactDrawerInteractionType: "Type d'interaction",
    contactDrawerInteractionNotes: 'Résumé / Notes',
    contactDrawerInteractionDate: 'Date',
    contactDrawerTimelineTitle: 'Historique des Échanges',
    contactDrawerNoInteractions: 'Aucune interaction enregistrée pour le moment.',
    contactDrawerConfirmDelete: 'Êtes-vous sûr de vouloir supprimer ce contact ?',

    analyticsSectionTitle: 'Analyses de Recherche d’Emploi',
    analyticsSectionSubtitle: 'Indicateurs complets sur vos taux de conversion, sources et rythme de candidature.',
    analyticsSourceTitle: 'Performance par Source & Canal',
    analyticsSourceSubtitle: 'Comparez les taux de réponse et d’entretiens par plateforme.',
    analyticsStageTitle: 'Distribution par Étape',
    analyticsStageSubtitle: 'Répartition actuelle des candidatures par statut.',
    analyticsRadarTitle: 'Radar de Santé du Pipeline',
    analyticsRadarSubtitle: 'Évaluation multi-axes de votre dynamique de recherche et conversion.',
    analyticsRadarVolume: 'Volume',
    analyticsRadarResponseRate: 'Taux de Réponse',
    analyticsRadarInterviewYield: 'Taux d’Entretien',
    analyticsRadarOfferRate: 'Taux d’Offre',
    analyticsRadarMomentum: 'Dynamique',
    analyticsRadarDiversity: 'Diversité des Sources',
    analyticsHeatmapTitle: 'Calendrier d’Activité des Candidatures',
    analyticsHeatmapSubtitle: 'Régularité des envois sur les 365 derniers jours.',
    analyticsHeatmapLess: 'Moins',
    analyticsHeatmapMore: 'Plus',
    analyticsHeatmapTooltip: '{count} candidatures le {date}',

    quickNavAnalytics: 'Analyses',
    quickNavTop: 'Haut',
    quickNavBottom: 'Bas',
    quickNavScrollToAnalytics: 'Défiler vers les Analyses de Recherche',
    quickNavScrollToTop: 'Remonter en haut',
    quickNavScrollToBottom: 'Défiler vers le bas',
  },
  de: {
    pageTitle: 'Bewerbungen',
    pageSubtitle: 'Verfolgen, organisieren und beschleunigen Sie Ihre Bewerbungspipeline mit geprüften Daten.',
    tabApplications: 'Bewerbungsbereich',
    tabContacts: 'Kontakte & Recruiter',
    viewSpreadsheet: 'Tabelle',
    viewKanban: 'Kanban-Board',
    viewFunnel: 'Trichter',
    btnAddApplication: 'Bewerbung Hinzufügen',
    btnRefresh: 'Aktualisieren',
    btnExportXlsx: 'Excel Exportieren (.xlsx)',
    btnImportXlsx: 'Excel Importieren',
    exporting: 'Exportieren...',
    refreshing: 'Aktualisieren...',

    statTotalApplications: 'Gesamte Bewerbungen',
    statInterviewRate: 'Interview-Quote',
    statResponseRate: 'Rückmelde-Quote',
    statOffers: 'Angebote',
    statAcceptedOffers: 'Angenommene Angebote',
    statActivePipeline: 'Aktive Pipeline',
    statInterviewsScheduled: 'Geplante Interviews',
    statAppsThisWeek: 'Diese Woche',
    statAvgResponseTime: 'Durchschnittliche Antwortzeit',
    daysUnit: 'Tage',

    actionNeededTitle: 'Handlungsbedarf',
    actionNeededSubtitle: 'Wichtige Aufgaben, anstehende Interviews und Nachfassaktionen im Überblick.',
    actionWaitingResponse: 'Warten auf Rückmeldung',
    actionFollowUp: 'Nachfassen fällig',
    actionPriorityFollowUp: 'Prioritäres Nachfassen',
    actionUpcomingInterviews: 'Anstehende Interviews',
    actionOverdue: 'Überfällig',
    actionNoResponse: 'Bisher keine Rückmeldung',
    actionNextStep: 'Nächster Schritt',
    actionNoActionsNeeded: 'Alles erledigt! Derzeit stehen keine dringenden Nachfassaktionen an.',
    actionBtnComplete: 'Erledigt',
    actionBtnSnooze: 'Zurückstellen',
    actionBtnReschedule: 'Verschieben',
    actionBtnCancel: 'Verwerfen',
    timeToday: 'Heute',
    timeTomorrow: 'Morgen',
    timeYesterday: 'Gestern',
    timeDaysAgo: 'Vor {n} Tagen',
    timeInDays: 'In {n} Tagen',
    timeOverdueBy: '{n} Tage überfällig',

    searchPlaceholder: 'Bewerbungen nach Stelle, Firma oder Standort durchsuchen...',
    filterAllSources: 'Alle Quellen',
    filterAllStatuses: 'Alle Status',
    filterAllPriorities: 'Alle Prioritäten',
    filterStageActive: 'Gefiltert nach Trichterstufe: {stage}',
    btnClearFilter: 'Filter aufheben',
    showingCount: '{count} von {total} Bewerbungen angezeigt',
    loadingApplications: 'Bewerbungen und Pipelinedaten werden geladen...',
    noAppsFoundTitle: 'Keine Bewerbungen gefunden',
    noAppsFoundSubtitle: 'Keine Bewerbungen entsprechen Ihren aktuellen Such- und Filterkriterien.',

    stageSaved: 'Gespeichert / Favorit',
    stageApplied: 'Beworben',
    stageInterviewing: 'Im Gespräch',
    stage1stInterview: '1. Vorstellungsgespräch',
    stage2ndInterview: '2. Vorstellungsgespräch',
    stage3rdInterview: '3. Vorstellungsgespräch',
    stageFinalInterview: 'Abschlussgespräch',
    stageOffer: 'Angebot Erhalten',
    stageAccepted: 'Angebot Angenommen',
    stageRejected: 'Archiviert / Abgelehnt',
    stageWithdrawn: 'Zurückgezogen',
    stageNoAnswer: 'Keine Rückmeldung',

    priorityHigh: 'Hoch',
    priorityMedium: 'Mittel',
    priorityLow: 'Niedrig',

    colJobTitle: 'Stellenbezeichnung',
    colCompany: 'Unternehmen',
    colStatus: 'Status',
    colPriority: 'Priorität',
    colSource: 'Quelle',
    colLocation: 'Standort',
    colSalary: 'Gehalt',
    colAppliedDate: 'Bewerbungsdatum',
    colFollowUp: 'Nachfassen',
    colRecruiter: 'Kontakt / Recruiter',
    colNotes: 'Notizen',
    colActions: 'Aktionen',
    editNotesPlaceholder: 'Persönliche Notizen hinzufügen...',
    btnSave: 'Speichern',
    btnCancel: 'Abbrechen',

    kanbanColSaved: 'Gespeichert',
    kanbanColApplied: 'Beworben',
    kanbanColInterviewing: 'Interviews',
    kanbanColOffers: 'Angebote',
    kanbanColArchived: 'Archiviert / Abgelehnt',
    kanbanDragHint: 'Karten ziehen, um den Status zu ändern',
    kanbanEmptyCol: 'Keine Bewerbungen in dieser Spalte',

    funnelTitle: 'Bewerbungstrichter',
    funnelSubtitle: 'Verfolgen Sie die Konvertierungsraten von der Bewerbung bis zur Zusage.',
    funnelInteractiveHint: 'Klicken Sie auf eine Stufe, um die Tabelle zu filtern',
    funnelApplications: 'Bewerbungen',
    funnelInterviews: 'Interviews',
    funnelOffers: 'Angebote',
    funnelAccepted: 'Angenommen',

    drawerTitle: 'Bewerbungsdetails',
    drawerTabOverview: 'Übersicht',
    drawerTabTimeline: 'Zeitverlauf',
    drawerTabIntelligence: 'KI-Einblicke',
    drawerTabResume: 'Lebenslauf-Anpassung',
    drawerFieldCompany: 'Unternehmen',
    drawerFieldTitle: 'Stellenbezeichnung',
    drawerFieldLocation: 'Standort',
    drawerFieldSource: 'Quelle',
    drawerFieldSalary: 'Gehalt',
    drawerFieldEmploymentType: 'Anstellungsart',
    drawerFieldAppliedDate: 'Bewerbungsdatum',
    drawerFieldFollowUp: 'Nächstes Nachfassen',
    drawerFieldRecruiter: 'Recruiter / Kontakt',
    drawerFieldPriority: 'Priorität',
    drawerFieldStatus: 'Status',
    drawerFieldNotes: 'Notizen & Kontext',
    drawerBtnEdit: 'Bearbeiten',
    drawerBtnDelete: 'Löschen',
    drawerConfirmDelete: 'Möchten Sie diese Bewerbung wirklich löschen?',

    contactsTitle: 'Bewerbungskontakte & Recruiter',
    contactsSubtitle: 'Verwalten Sie Kontakte zu Recruitern, Personalberatern und Einstellungsmanagern.',
    contactsSearchPlaceholder: 'Kontakte nach Name, Firma, E-Mail oder Rolle durchsuchen...',
    contactsAllCompanies: 'Alle Unternehmen',
    btnAddContact: 'Kontakt Hinzufügen',
    btnImportContacts: 'Excel Importieren',
    btnExportContacts: 'Excel Exportieren (.xlsx)',
    contactsLoading: 'Kontakte und Kommunikationsverlauf werden geladen...',
    contactsEmptyTitle: 'Keine Kontakte gefunden',
    contactsEmptySubtitle: 'Mit Bewerbungen verknüpfte oder importierte Kontakte erscheinen hier.',
    contactsEmptySearch: 'Keine Kontakte entsprechen Ihrer Suche.',
    contactsAddFirstBtn: 'Ersten Kontakt Anlegen',
    contactsImportFirstBtn: 'Aus Excel Importieren',

    commNotContacted: 'Nicht kontaktiert',
    commContactedNoResponse: 'Kontaktiert, keine Antwort',
    commResponded: 'Kontaktiert & Geantwortet',
    commAwaitingReply: 'Warten auf Antwort',
    commStateLabel: 'Kommunikationsstatus',
    commLastContacted: 'Zuletzt kontaktiert',
    commLastResponse: 'Letzte Rückmeldung',
    commNextAction: 'Nächste Aktion',
    commRelatedApps: 'Verknüpfte Bewerbungen',
    commMethodEmail: 'E-Mail',
    commMethodLinkedIn: 'LinkedIn',
    commMethodPhone: 'Telefon',
    commMethodOther: 'Sonstige',

    addContactModalTitle: 'Kontakt / Recruiter Hinzufügen',
    addContactModalSubtitle: 'Erfassen Sie wichtige Ansprechpartner und Personalverantwortliche für Ihre Bewerbungen.',
    addContactSecIdentity: 'Kontaktinformationen',
    addContactSecCommunication: 'Kommunikation & Beziehung (Optional)',
    addContactSecAdditional: 'Zusätzliche Informationen',
    addContactFirstName: 'Vorname *',
    addContactLastName: 'Nachname',
    addContactCompany: 'Unternehmen',
    addContactRole: 'Rolle / Position',
    addContactEmail: 'E-Mail-Adresse',
    addContactPhone: 'Telefonnummer',
    addContactLinkedIn: 'LinkedIn Profil-URL',
    addContactLocation: 'Standort',
    addContactTags: 'Schlagwörter (kommagetrennt)',
    addContactNotes: 'Notizen & Kontext',
    addContactQuestionContacted: 'Wurde diese Person bereits kontaktiert?',
    addContactOptionYes: 'Ja',
    addContactOptionNo: 'Nein (Noch nicht kontaktiert)',
    addContactMethodLabel: 'Kontaktmethode',
    addContactDateLabel: 'Kontaktdatum (Optional)',
    addContactEmailUsedLabel: 'Verwendete E-Mail-Adresse (Optional)',
    addContactQuestionResponse: 'Rückmeldung erhalten?',
    addContactResponseDateLabel: 'Antwortdatum (Optional)',
    addContactResponseNotesLabel: 'Notizen zur Antwort (Optional)',
    addContactBtnCreate: 'Kontakt Erstellen',
    addContactBtnSaving: 'Speichern...',
    addContactDuplicateWarning: 'Bestehender Kontakt Gefunden',
    addContactFirstNameRequired: 'Vorname ist erforderlich.',

    contactDrawerLoading: 'Kontaktdetails und Kommunikationshistorie werden geladen...',
    contactDrawerNotFound: 'Kontakt nicht gefunden.',
    contactDrawerEditTitle: 'Kontaktinformationen Bearbeiten',
    contactDrawerSaveEdit: 'Änderungen Speichern',
    contactDrawerLogInteractionBtn: 'Interaktion Erfassen',
    contactDrawerInteractionTitle: 'Kommunikation / Interaktion Protokollieren',
    contactDrawerInteractionType: 'Interaktionsart',
    contactDrawerInteractionNotes: 'Zusammenfassung / Notizen',
    contactDrawerInteractionDate: 'Datum',
    contactDrawerTimelineTitle: 'Interaktionsverlauf',
    contactDrawerNoInteractions: 'Bisher keine Interaktionen erfasst.',
    contactDrawerConfirmDelete: 'Möchten Sie diesen Kontakt wirklich entfernen?',

    analyticsSectionTitle: 'Bewerbungsanalytik',
    analyticsSectionSubtitle: 'Umfassende Einblicke in Konversionsraten, Quellen und Bewerbungsaktivität.',
    analyticsSourceTitle: 'Quellenanalytik & Kanalausbeute',
    analyticsSourceSubtitle: 'Vergleichen Sie Rückmelde- und Interviewquoten nach Plattform.',
    analyticsStageTitle: 'Stufenverteilung',
    analyticsStageSubtitle: 'Aktuelle Verteilung der Bewerbungen nach Status.',
    analyticsRadarTitle: 'Pipeline-Gesundheitsradar',
    analyticsRadarSubtitle: 'Mehrdimensionale Analyse Ihrer Bewerbungsdynamik.',
    analyticsRadarVolume: 'Volumen',
    analyticsRadarResponseRate: 'Rückmelde-Quote',
    analyticsRadarInterviewYield: 'Interview-Ausbeute',
    analyticsRadarOfferRate: 'Angebots-Quote',
    analyticsRadarMomentum: 'Dynamik',
    analyticsRadarDiversity: 'Quellenvielfalt',
    analyticsHeatmapTitle: 'Bewerbungs-Aktivitätskalender',
    analyticsHeatmapSubtitle: 'Bewerbungsintensität der letzten 365 Tage.',
    analyticsHeatmapLess: 'Weniger',
    analyticsHeatmapMore: 'Mehr',
    analyticsHeatmapTooltip: '{count} Bewerbungen am {date}',

    quickNavAnalytics: 'Analytik',
    quickNavTop: 'Nach oben',
    quickNavBottom: 'Nach unten',
    quickNavScrollToAnalytics: 'Nach unten zur Bewerbungsanalytik springen',
    quickNavScrollToTop: 'Zurück nach oben scrollen',
    quickNavScrollToBottom: 'Nach ganz unten scrollen',
  },
  nl: {
    // Dutch fallback to ensure total safety
    pageTitle: 'Sollicitaties',
    pageSubtitle: 'Volg, organiseer en versnel uw sollicitatieproces met geverifieerde gegevens.',
    tabApplications: 'Sollicitaties Werkplek',
    tabContacts: 'Contacten & Recruiters',
    viewSpreadsheet: 'Tabel',
    viewKanban: 'Bord',
    viewFunnel: 'Trechter',
    btnAddApplication: 'Sollicitatie Toevoegen',
    btnRefresh: 'Vernieuwen',
    btnExportXlsx: 'Excel Exporteren (.xlsx)',
    btnImportXlsx: 'Excel Importeren',
    exporting: 'Exporteren...',
    refreshing: 'Vernieuwen...',

    statTotalApplications: 'Totaal Sollicitaties',
    statInterviewRate: 'Interviewpercentage',
    statResponseRate: 'Responspercentage',
    statOffers: 'Aanbiedingen',
    statAcceptedOffers: 'Geaccepteerde Aanbiedingen',
    statActivePipeline: 'Actieve Pipeline',
    statInterviewsScheduled: 'Geplande Gesprekken',
    statAppsThisWeek: 'Deze Week',
    statAvgResponseTime: 'Gemiddelde Reactietijd',
    daysUnit: 'dagen',

    actionNeededTitle: 'Actie Vereist',
    actionNeededSubtitle: 'Prioritaire taken en opvolgingen die uw aandacht vereisen.',
    actionWaitingResponse: 'Wachten op Reactie',
    actionFollowUp: 'Opvolging Nodig',
    actionPriorityFollowUp: 'Prioritaire Opvolging',
    actionUpcomingInterviews: 'Aankomende Gesprekken',
    actionOverdue: 'Achterstallig',
    actionNoResponse: 'Nog Geen Reactie',
    actionNextStep: 'Volgende Stap',
    actionNoActionsNeeded: 'Alles bijgewerkt! Geen dringende opvolgingen op dit moment.',
    actionBtnComplete: 'Voltooid',
    actionBtnSnooze: 'Uitstellen',
    actionBtnReschedule: 'Herplannen',
    actionBtnCancel: 'Negeren',
    timeToday: 'Vandaag',
    timeTomorrow: 'Morgen',
    timeYesterday: 'Gisteren',
    timeDaysAgo: '{n} dagen geleden',
    timeInDays: 'Over {n} dagen',
    timeOverdueBy: '{n} dagen te laat',

    searchPlaceholder: 'Zoek sollicitaties op functie, bedrijf of locatie...',
    filterAllSources: 'Alle Bronnen',
    filterAllStatuses: 'Alle Statussen',
    filterAllPriorities: 'Alle Prioriteiten',
    filterStageActive: 'Gefilterd op trechterfase: {stage}',
    btnClearFilter: 'Filter wissen',
    showingCount: 'Toont {count} van {total} sollicitaties',
    loadingApplications: 'Sollicitaties laden...',
    noAppsFoundTitle: 'Geen sollicitaties gevonden',
    noAppsFoundSubtitle: 'Geen sollicitaties komen overeen met uw criteria.',

    stageSaved: 'Opgeslagen',
    stageApplied: 'Gesolliciteerd',
    stageInterviewing: 'In Gesprek',
    stage1stInterview: '1e Gesprek',
    stage2ndInterview: '2e Gesprek',
    stage3rdInterview: '3e Gesprek',
    stageFinalInterview: 'Eindgesprek',
    stageOffer: 'Aanbod Ontvangen',
    stageAccepted: 'Aanbod Geaccepteerd',
    stageRejected: 'Afgewezen',
    stageWithdrawn: 'Ingetrokken',
    stageNoAnswer: 'Geen Reactie',

    priorityHigh: 'Hoog',
    priorityMedium: 'Gemiddeld',
    priorityLow: 'Laag',

    colJobTitle: 'Functietitel',
    colCompany: 'Bedrijf',
    colStatus: 'Status',
    colPriority: 'Prioriteit',
    colSource: 'Bron',
    colLocation: 'Locatie',
    colSalary: 'Salaris',
    colAppliedDate: 'Sollicitatiedatum',
    colFollowUp: 'Opvolging',
    colRecruiter: 'Contactpersoon',
    colNotes: 'Notities',
    colActions: 'Acties',
    editNotesPlaceholder: 'Notities toevoegen...',
    btnSave: 'Opslaan',
    btnCancel: 'Annuleren',

    kanbanColSaved: 'Opgeslagen',
    kanbanColApplied: 'Gesolliciteerd',
    kanbanColInterviewing: 'In Gesprek',
    kanbanColOffers: 'Aanbiedingen',
    kanbanColArchived: 'Afgewezen',
    kanbanDragHint: 'Sleep kaarten om status te wijzigen',
    kanbanEmptyCol: 'Geen sollicitaties in deze fase',

    funnelTitle: 'Wervingsfunnel',
    funnelSubtitle: 'Volg de conversie van sollicitatie tot aanbod.',
    funnelInteractiveHint: 'Klik op een fase om de tabel te filteren',
    funnelApplications: 'Sollicitaties',
    funnelInterviews: 'Gesprekken',
    funnelOffers: 'Aanbiedingen',
    funnelAccepted: 'Geaccepteerd',

    drawerTitle: 'Sollicitatiedetails',
    drawerTabOverview: 'Overzicht',
    drawerTabTimeline: 'Tijdlijn',
    drawerTabIntelligence: 'AI Inzichten',
    drawerTabResume: 'CV Aanpassing',
    drawerFieldCompany: 'Bedrijf',
    drawerFieldTitle: 'Functietitel',
    drawerFieldLocation: 'Locatie',
    drawerFieldSource: 'Bron',
    drawerFieldSalary: 'Salaris',
    drawerFieldEmploymentType: 'Type Dienstverband',
    drawerFieldAppliedDate: 'Sollicitatiedatum',
    drawerFieldFollowUp: 'Volgende Opvolging',
    drawerFieldRecruiter: 'Contactpersoon',
    drawerFieldPriority: 'Prioriteit',
    drawerFieldStatus: 'Status',
    drawerFieldNotes: 'Notities',
    drawerBtnEdit: 'Bewerken',
    drawerBtnDelete: 'Verwijderen',
    drawerConfirmDelete: 'Weet u zeker dat u deze sollicitatie wilt verwijderen?',

    contactsTitle: 'Contacten & Recruiters',
    contactsSubtitle: 'Beheer relaties met recruiters en hiring managers.',
    contactsSearchPlaceholder: 'Zoek contacten...',
    contactsAllCompanies: 'Alle Bedrijven',
    btnAddContact: 'Contact Toevoegen',
    btnImportContacts: 'Excel Importeren',
    btnExportContacts: 'Excel Exporteren',
    contactsLoading: 'Contacten laden...',
    contactsEmptyTitle: 'Geen contacten gevonden',
    contactsEmptySubtitle: 'Gekoppelde contacten verschijnen hier.',
    contactsEmptySearch: 'Geen resultaten.',
    contactsAddFirstBtn: 'Eerste Contact Toevoegen',
    contactsImportFirstBtn: 'Importeren uit Excel',

    commNotContacted: 'Niet gecontacteerd',
    commContactedNoResponse: 'Gecontacteerd, geen antwoord',
    commResponded: 'Gecontacteerd & Geantwoord',
    commAwaitingReply: 'Wachten op antwoord',
    commStateLabel: 'Communicatiestatus',
    commLastContacted: 'Laatst gecontacteerd',
    commLastResponse: 'Laatste reactie',
    commNextAction: 'Volgende actie',
    commRelatedApps: 'Gekoppelde sollicitaties',
    commMethodEmail: 'E-mail',
    commMethodLinkedIn: 'LinkedIn',
    commMethodPhone: 'Telefoon',
    commMethodOther: 'Overig',

    addContactModalTitle: 'Contactpersoon Toevoegen',
    addContactModalSubtitle: 'Houd contactpersonen en recruiters bij.',
    addContactSecIdentity: 'Contactgegevens',
    addContactSecCommunication: 'Communicatie & Relatie (Optioneel)',
    addContactSecAdditional: 'Extra Informatie',
    addContactFirstName: 'Voornaam *',
    addContactLastName: 'Achternaam',
    addContactCompany: 'Bedrijf',
    addContactRole: 'Functietitel',
    addContactEmail: 'E-mailadres',
    addContactPhone: 'Telefoonnummer',
    addContactLinkedIn: 'LinkedIn URL',
    addContactLocation: 'Locatie',
    addContactTags: 'Tags',
    addContactNotes: 'Notities',
    addContactQuestionContacted: 'Heeft u al contact gehad?',
    addContactOptionYes: 'Ja',
    addContactOptionNo: 'Nee (Nog niet gecontacteerd)',
    addContactMethodLabel: 'Contactmethode',
    addContactDateLabel: 'Datum gecontacteerd (Optioneel)',
    addContactEmailUsedLabel: 'Gebruikt e-mailadres (Optioneel)',
    addContactQuestionResponse: 'Reactie ontvangen?',
    addContactResponseDateLabel: 'Datum reactie (Optioneel)',
    addContactResponseNotesLabel: 'Notities reactie (Optioneel)',
    addContactBtnCreate: 'Contact Aanmaken',
    addContactBtnSaving: 'Opslaan...',
    addContactDuplicateWarning: 'Bestaand contact gevonden',
    addContactFirstNameRequired: 'Voornaam is verplicht.',

    contactDrawerLoading: 'Contact laden...',
    contactDrawerNotFound: 'Contact niet gevonden.',
    contactDrawerEditTitle: 'Contact Bewerken',
    contactDrawerSaveEdit: 'Opslaan',
    contactDrawerLogInteractionBtn: 'Interactie Toevoegen',
    contactDrawerInteractionTitle: 'Interactie Registreren',
    contactDrawerInteractionType: 'Type',
    contactDrawerInteractionNotes: 'Notities',
    contactDrawerInteractionDate: 'Datum',
    contactDrawerTimelineTitle: 'Interactiegeschiedenis',
    contactDrawerNoInteractions: 'Nog geen interacties geregistreerd.',
    contactDrawerConfirmDelete: 'Weet u zeker dat u dit contact wilt verwijderen?',

    analyticsSectionTitle: 'Sollicitatie Analytics',
    analyticsSectionSubtitle: 'Inzichten in uw sollicitatievoortgang.',
    analyticsSourceTitle: 'Bronanalyse',
    analyticsSourceSubtitle: 'Vergelijk responspercentages per platform.',
    analyticsStageTitle: 'Fasendistributie',
    analyticsStageSubtitle: 'Huidige verdeling van sollicitaties.',
    analyticsRadarTitle: 'Pipeline Gezondheidsradar',
    analyticsRadarSubtitle: 'Multi-dimensionale analyse.',
    analyticsRadarVolume: 'Volume',
    analyticsRadarResponseRate: 'Responspercentage',
    analyticsRadarInterviewYield: 'Gesprekpercentage',
    analyticsRadarOfferRate: 'Aanbiedingspercentage',
    analyticsRadarMomentum: 'Dynamiek',
    analyticsRadarDiversity: 'Brondiversiteit',
    analyticsHeatmapTitle: 'Activiteitskalender',
    analyticsHeatmapSubtitle: 'Sollicitaties over de afgelopen 365 dagen.',
    analyticsHeatmapLess: 'Minder',
    analyticsHeatmapMore: 'Meer',
    analyticsHeatmapTooltip: '{count} sollicitaties op {date}',

    quickNavAnalytics: 'Analytics',
    quickNavTop: 'Omhoog',
    quickNavBottom: 'Omlaag',
    quickNavScrollToAnalytics: 'Naar Analytics scrollen',
    quickNavScrollToTop: 'Terug naar boven',
    quickNavScrollToBottom: 'Naar beneden scrollen',
  },
};

// Helper function for dynamic relative dates
export function formatRelativeTime(
  dateInput: string | Date | null | undefined,
  lang: Language = 'en'
): string {
  if (!dateInput) return '';
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  if (isNaN(date.getTime())) return '';

  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const targetStart = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const diffDays = Math.round((targetStart - todayStart) / (1000 * 60 * 60 * 24));

  const t = applicationsTranslations[lang] || applicationsTranslations.en;

  if (diffDays === 0) return t.timeToday;
  if (diffDays === 1) return t.timeTomorrow;
  if (diffDays === -1) return t.timeYesterday;
  if (diffDays < -1) return t.timeDaysAgo.replace('{n}', String(Math.abs(diffDays)));
  return t.timeInDays.replace('{n}', String(diffDays));
}

// Helper function for status labels
export function getStatusLabel(status: string | null | undefined, lang: Language = 'en'): string {
  if (!status) return '';
  const t = applicationsTranslations[lang] || applicationsTranslations.en;
  switch (status.toLowerCase()) {
    case 'saved':
      return t.stageSaved;
    case 'applied':
      return t.stageApplied;
    case 'interviewing':
      return t.stageInterviewing;
    case '1st_interview':
      return t.stage1stInterview;
    case '2nd_interview':
      return t.stage2ndInterview;
    case '3rd_interview':
      return t.stage3rdInterview;
    case 'final_interview':
      return t.stageFinalInterview;
    case 'offer':
      return t.stageOffer;
    case 'accepted':
      return t.stageAccepted;
    case 'rejected':
      return t.stageRejected;
    case 'withdrawn':
      return t.stageWithdrawn;
    case 'no_answer':
      return t.stageNoAnswer;
    default:
      return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

// Helper function for priority labels
export function getPriorityLabel(priority: string | null | undefined, lang: Language = 'en'): string {
  if (!priority) return '';
  const t = applicationsTranslations[lang] || applicationsTranslations.en;
  switch (priority.toLowerCase()) {
    case 'high':
      return t.priorityHigh;
    case 'medium':
      return t.priorityMedium;
    case 'low':
      return t.priorityLow;
    default:
      return priority;
  }
}

// Helper function for communication status
export function getCommunicationStatusLabel(
  commStatus: string | null | undefined,
  lang: Language = 'en'
): string {
  const t = applicationsTranslations[lang] || applicationsTranslations.en;
  switch (commStatus) {
    case 'responded':
      return t.commResponded;
    case 'contacted_no_response':
      return t.commContactedNoResponse;
    case 'not_contacted':
    default:
      return t.commNotContacted;
  }
}
