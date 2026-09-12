export const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

export interface Country {
  id: number;
  name: string;
  code: string;
}

export interface Company {
  id: number;
  name: string;
  website_url: string;
  careers_url: string | null;
  active: boolean;
  countries: Country[];
}

export interface ScrapeTarget {
  id: number;
  company_id: number;
  url: string;
  type: string | null;
  active: boolean;
  last_scraped_at: string | null;
  status: string | null;
  cooldown_until: string | null;
  robots_txt_allowed: boolean | null;
  robots_txt_checked_at: string | null;
}

export interface Job {
  id: number;
  company_id: number;
  country_id: number;
  title: string;
  location: string | null;
  job_url: string;
  employment_type: string | null;
  remote_type: string | null;
  department: string | null;
  source: string | null;
  external_job_id: string | null;
  posted_at: string | null;
  discovered_at: string;
  last_seen_at: string | null;
  active: boolean;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  salary_period: string | null;
  description?: string | null;
  match_score?: number | null;
}

export interface JobDetail extends Job {
  description: string | null;
  skills: string[];
  positive_factors: string[];
  missing_factors: string[];
  category_scores?: Record<string, number>;
}

export interface JobTranslationItem {
  id: number;
  job_id: number;
  language: string;
  title: string;
  description: string | null;
  source_language: string;
  created_at: string;
  updated_at: string;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface UserExperienceItem {
  id: number;
  user_id: number;
  title: string;
  company_name: string;
  experience_type: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
}

export interface UserEducationItem {
  id: number;
  user_id: number;
  institution: string;
  degree: string | null;
  field_of_study: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
}

export interface UserLanguageItem {
  id: number;
  user_id: number;
  language: string;
  proficiency: string | null;
}

export interface CountryPreferenceItem {
  id: number;
  name: string;
  code: string;
}

export interface ResumeProfileData {
  full_name: string;
  headline: string;
  email: string;
  phone: string;
  location: string;
  website: string;
  github: string;
  linkedin: string;
  summary: string;
}

export interface ResumeExperienceEntry {
  id: string;
  company: string;
  title: string;
  location: string;
  employment_type: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  description: string;
  highlights: string[];
}

export interface ResumeEducationEntry {
  id: string;
  institution: string;
  degree: string;
  field: string;
  location: string;
  start_date: string;
  end_date: string;
  gpa: string;
  description: string;
}

export interface ResumeSkillEntry {
  id: string;
  name: string;
  category: string;
  proficiency: string;
}

export interface ResumeProjectEntry {
  id: string;
  name: string;
  description: string;
  technologies: string;
  url: string;
  start_date: string;
  end_date: string;
}

export interface ResumeCertificationEntry {
  id: string;
  name: string;
  issuer: string;
  issue_date: string;
  expiration_date: string;
  url: string;
}

export interface ResumeLanguageEntry {
  id: string;
  language: string;
  proficiency: string;
}

export interface ResumeCustomSectionEntry {
  id: string;
  title: string;
  items: string[];
}

export interface StructuredResumeData {
  profile: ResumeProfileData;
  experience: ResumeExperienceEntry[];
  education: ResumeEducationEntry[];
  skills: ResumeSkillEntry[];
  projects: ResumeProjectEntry[];
  certifications: ResumeCertificationEntry[];
  languages: ResumeLanguageEntry[];
  custom_sections: ResumeCustomSectionEntry[];
}

export type ResumeTemplateType = 'modern' | 'classic' | 'minimal' | 'technical';

export interface ResumeSettings {
  template: ResumeTemplateType;
  theme_color: string;
  font_family: string;
  font_size: string;
  document_size: 'A4' | 'LETTER';
  section_order: string[];
  section_visibility: Record<string, boolean>;
}

export interface StructuredResumeItem {
  id: number;
  user_id: number;
  title: string;
  is_active: boolean;
  is_default: boolean;
  target_job_id: number | null;
  source_resume_id: number | null;
  structured_data: StructuredResumeData;
  settings: ResumeSettings;
  created_at: string;
  updated_at: string;
}

export interface ResumeTailorSuggestionSummary {
  original: string;
  suggested: string;
  reason: string;
}

export interface ResumeTailorSuggestionExperience {
  item_id: string;
  company: string;
  title: string;
  original_description: string;
  suggested_highlights: string[];
  reason: string;
}

export interface ResumeTailorSuggestions {
  job_id: number;
  job_title: string;
  base_resume_id: number;
  base_resume_title: string;
  match_score: number;
  summary: ResumeTailorSuggestionSummary;
  skills_to_emphasize: string[];
  missing_job_skills: string[];
  experience_refinements: ResumeTailorSuggestionExperience[];
  key_advice: string[];
}

export interface ResumeSaveTailoredCopyRequest {
  title: string;
  apply_suggested_summary: boolean;
  apply_emphasized_skills: boolean;
  accepted_experience_refinements: string[];
}

export interface ApplicationItem {
  id: number;
  user_id: number;
  job_id: number;
  status: 'saved' | 'applied' | 'interviewing' | 'offer' | 'rejected';
  notes: string | null;
  applied_at: string | null;
  created_at: string;
  updated_at: string;
  job?: Job | null;
}

export interface ScraperTelemetry {
  total_runs: number;
  runs_by_status: Record<string, number>;
  success_rate_percent: number;
  avg_duration_seconds: number;
  total_jobs_found: number;
  total_jobs_added: number;
  total_jobs_updated: number;
  duplicate_rate_percent: number;
  total_targets: number;
  active_targets: number;
  cooldown_targets: number;
  robots_blocked_targets: number;
  recent_errors: Array<{ run_id: string; company_id: string; started_at: string; error: string }>;
}

export interface UserProfile {
  id: number;
  email: string;
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  email_verified: boolean;
  preferences: {
    preferred_job_type: string | null;
    preferred_work_mode: string | null;
    preferred_location: string | null;
    min_salary: number | null;
    max_salary: number | null;
    salary_currency: string | null;
  } | null;
  skills: string[];
  experience?: UserExperienceItem[];
  education?: UserEducationItem[];
  languages?: UserLanguageItem[];
  country_preferences?: CountryPreferenceItem[];
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface SyncResponse {
  jobs_found: number;
  jobs_added: number;
  jobs_updated: number;
  parser_errors: string[];
}

// Token helper
export const getStoredToken = (): string | null => localStorage.getItem('compust_token');
export const setStoredToken = (token: string | null) => {
  if (token) localStorage.setItem('compust_token', token);
  else localStorage.removeItem('compust_token');
};

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) errorDetail = errorJson.detail;
    } catch {
      // Keep statusText fallback
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  // Countries & Companies
  getCountries: () => request<Country[]>('/countries'),
  getCompanies: () => request<Company[]>('/companies'),

  // Scrape Targets
  getScrapeTargets: (companyId?: number) =>
    request<ScrapeTarget[]>(companyId ? `/scrape-targets?company_id=${companyId}` : '/scrape-targets'),
  syncScrapeTarget: (targetId: number, maxPages: number = 5) =>
    request<SyncResponse>(`/scrape-targets/${targetId}/sync?max_pages=${maxPages}`, { method: 'POST' }),

  // Jobs
  getJobs: (params: {
    country_id?: number | null;
    company_id?: number | null;
    remote_type?: string | null;
    employment_type?: string | null;
    search?: string | null;
    active_only?: boolean;
    page?: number;
    page_size?: number;
  } = {}) => {
    const query = new URLSearchParams();
    if (params.country_id) query.set('country_id', params.country_id.toString());
    if (params.company_id) query.set('company_id', params.company_id.toString());
    if (params.remote_type) query.set('remote_type', params.remote_type);
    if (params.employment_type) query.set('employment_type', params.employment_type);
    if (params.search) query.set('search', params.search);
    if (params.active_only !== undefined) query.set('active_only', params.active_only.toString());
    if (params.page) query.set('page', params.page.toString());
    if (params.page_size) query.set('page_size', params.page_size.toString());
    return request<JobListResponse>(`/jobs?${query.toString()}`);
  },

  getJobDetail: (jobId: number) => request<JobDetail>(`/jobs/${jobId}`),

  // Auth
  login: (email: string, password: string) =>
    request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (data: { email: string; password: string; first_name?: string; last_name?: string }) =>
    request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getMe: () => request<UserProfile>('/auth/me'),

  // Profile
  getProfile: () => request<UserProfile>('/profile'),
  updatePreferences: (preferences: {
    preferred_work_mode?: string | null;
    preferred_location?: string | null;
    min_salary?: number | null;
    max_salary?: number | null;
    salary_currency?: string | null;
  }) =>
    request<UserProfile>('/profile/preferences', {
      method: 'PUT',
      body: JSON.stringify(preferences),
    }),

  updateSkills: (skills: string[]) =>
    request<UserProfile>('/profile/skills', {
      method: 'PUT',
      body: JSON.stringify({ skills }),
    }),

  // Multi-dimensional Profile (Experience, Education, Languages)
  addExperience: (data: {
    title: string;
    company_name: string;
    experience_type?: string;
    start_date?: string | null;
    end_date?: string | null;
    description?: string | null;
  }) =>
    request<UserProfile>('/profile/experiences', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteExperience: (experienceId: number) =>
    request<UserProfile>(`/profile/experiences/${experienceId}`, {
      method: 'DELETE',
    }),

  addEducation: (data: {
    institution: string;
    degree?: string | null;
    field_of_study?: string | null;
    start_date?: string | null;
    end_date?: string | null;
    description?: string | null;
  }) =>
    request<UserProfile>('/profile/educations', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteEducation: (educationId: number) =>
    request<UserProfile>(`/profile/educations/${educationId}`, {
      method: 'DELETE',
    }),

  addLanguage: (data: {
    language: string;
    proficiency?: string;
  }) =>
    request<UserProfile>('/profile/languages', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteLanguage: (languageId: number) =>
    request<UserProfile>(`/profile/languages/${languageId}`, {
      method: 'DELETE',
    }),

  updateCountryPreferences: (countryIds: number[]) =>
    request<UserProfile>('/profile/countries', {
      method: 'PUT',
      body: JSON.stringify({ country_ids: countryIds }),
    }),

  // Application Tracking & Pipeline
  getApplications: (status?: string) =>
    request<ApplicationItem[]>(status ? `/applications?status=${encodeURIComponent(status)}` : '/applications'),

  trackApplication: (jobId: number, data?: { status?: string; notes?: string }) =>
    request<ApplicationItem>(`/applications/${jobId}`, {
      method: 'POST',
      body: JSON.stringify(data || { status: 'saved' }),
    }),

  updateApplication: (applicationId: number, data: { status?: string; notes?: string }) =>
    request<ApplicationItem>(`/applications/${applicationId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteApplication: (applicationId: number) =>
    request<{ status: string }>(`/applications/${applicationId}`, {
      method: 'DELETE',
    }),

  deleteApplicationByJob: (jobId: number) =>
    request<{ status: string }>(`/applications/jobs/${jobId}`, {
      method: 'DELETE',
    }),

  // Scraper Telemetry & Metrics
  getScraperMetrics: () => request<ScraperTelemetry>('/admin/metrics'),

  // Job Translations (Decoupled & Non-destructive)
  getJobTranslations: (jobId: number) =>
    request<JobTranslationItem[]>(`/jobs/${jobId}/translations`),

  requestJobTranslation: (
    jobId: number,
    data: { language: string; title?: string; description?: string; source_language?: string }
  ) =>
    request<JobTranslationItem>(`/jobs/${jobId}/translations`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Phase 16 — Company & Source Management
  createCompany: (data: CompanyCreate) =>
    request<Company>('/companies', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateCompany: (companyId: number, data: CompanyUpdate) =>
    request<Company>(`/companies/${companyId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  toggleCompany: (companyId: number) =>
    request<Company>(`/companies/${companyId}/toggle`, {
      method: 'PATCH',
    }),

  deleteCompany: (companyId: number, confirmHard: boolean = false) =>
    request<{ status: string; company_id: number; message: string }>(
      `/companies/${companyId}?confirm_hard_delete=${confirmHard}`,
      {
        method: 'DELETE',
      }
    ),

  createScrapeTarget: (data: ScrapeTargetCreate) =>
    request<ScrapeTarget>('/scrape-targets', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateScrapeTarget: (targetId: number, data: ScrapeTargetUpdate) =>
    request<ScrapeTarget>(`/scrape-targets/${targetId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  toggleScrapeTarget: (targetId: number) =>
    request<ScrapeTarget>(`/scrape-targets/${targetId}/toggle`, {
      method: 'PATCH',
    }),

  deleteScrapeTarget: (targetId: number) =>
    request<{ status: string; target_id: number }>(`/scrape-targets/${targetId}`, {
      method: 'DELETE',
    }),

  // Phase 17 & 18 — Ollama AI Integration & Assistant
  getAIStatus: () => request<AIStatus>('/ai/status'),

  getAIProviders: () => request<AIProvider[]>('/ai/providers'),

  setAISettings: (selectedModel: string) =>
    request<AIStatus>('/ai/settings', {
      method: 'POST',
      body: JSON.stringify({ selected_model: selectedModel }),
    }),

  sendAIChat: (query: string, model?: string) =>
    request<AIChatResponse>('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ query, model }),
    }),

  // Phase 19 — Resume Upload & Structuring
  uploadResume: async (file: File): Promise<ResumeItem> => {
    const formData = new FormData();
    formData.append('file', file);
    const token = getStoredToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const response = await fetch(`${API_BASE_URL}/profile/resume`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Resume upload failed');
    }
    return response.json();
  },

  getActiveResume: () => request<ResumeItem>('/profile/resume'),

  getResumes: () => request<ResumeItem[]>('/profile/resumes'),

  activateResume: (resumeId: number) =>
    request<ResumeItem>(`/profile/resume/${resumeId}/activate`, {
      method: 'PUT',
    }),

  deleteResume: (resumeId: number) =>
    request<{ status: string; resume_id: number }>(`/profile/resume/${resumeId}`, {
      method: 'DELETE',
    }),

  // Phase 20 — Resume Customization Suggestions
  getResumeSuggestions: (jobId: number) =>
    request<ResumeSuggestion>(`/jobs/${jobId}/resume-suggestions`, {
      method: 'POST',
    }),

  recreateResume: (jobId: number) =>
    request<CustomizedResumeItem>(`/jobs/${jobId}/resume-customizations/recreate`, {
      method: 'POST',
    }),

  getCustomizedResumesForJob: (jobId: number) =>
    request<CustomizedResumeItem[]>(`/jobs/${jobId}/customized-resumes`),

  getCustomizedResumeDownloadUrl: (resumeId: number, format: 'pdf' | 'docx') => {
    const token = getStoredToken();
    const query = token ? `?token=${encodeURIComponent(token)}` : '';
    return `${API_BASE_URL}/customized-resumes/${resumeId}/download/${format}${query}`;
  },

  downloadCustomizedResume: async (resumeId: number, format: 'pdf' | 'docx', defaultFilename?: string): Promise<void> => {
    const token = getStoredToken();
    if (!token) {
      throw new Error('Please log in to download customized resumes');
    }

    const downloadUrl = api.getCustomizedResumeDownloadUrl(resumeId, format);
    const link = document.createElement('a');
    link.style.display = 'none';
    link.href = downloadUrl;
    if (defaultFilename) {
      link.setAttribute('download', defaultFilename);
    }
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      try {
        if (link.parentNode) {
          link.parentNode.removeChild(link);
        }
      } catch (_) {}
    }, 3000);
  },

  // First-Class Structured Resume Builder API
  listStructuredResumes: () =>
    request<StructuredResumeItem[]>('/resumes'),

  createStructuredResume: (data: {
    title: string;
    is_default?: boolean;
    structured_data?: StructuredResumeData;
    settings?: ResumeSettings;
    target_job_id?: number | null;
    source_resume_id?: number | null;
  }) =>
    request<StructuredResumeItem>('/resumes', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getStructuredResume: (resumeId: number) =>
    request<StructuredResumeItem>(`/resumes/${resumeId}`),

  updateStructuredResume: (
    resumeId: number,
    data: {
      title?: string;
      is_default?: boolean;
      structured_data?: StructuredResumeData;
      settings?: ResumeSettings;
    }
  ) =>
    request<StructuredResumeItem>(`/resumes/${resumeId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  duplicateStructuredResume: (resumeId: number, newTitle?: string) =>
    request<StructuredResumeItem>(`/resumes/${resumeId}/duplicate`, {
      method: 'POST',
      body: JSON.stringify({ new_title: newTitle }),
    }),

  deleteStructuredResume: (resumeId: number) =>
    request<{ status: string; id: number }>(`/resumes/${resumeId}`, {
      method: 'DELETE',
    }),

  setDefaultStructuredResume: (resumeId: number) =>
    request<StructuredResumeItem>(`/resumes/${resumeId}/set-default`, {
      method: 'POST',
    }),

  importProfileToResume: (resumeId: number) =>
    request<StructuredResumeItem>(`/resumes/${resumeId}/import-profile`, {
      method: 'POST',
    }),

  getStructuredResumeExportUrl: (resumeId: number, format: 'pdf' | 'docx') => {
    const token = getStoredToken();
    const query = token ? `?token=${encodeURIComponent(token)}` : '';
    return `${API_BASE_URL}/resumes/${resumeId}/export/${format}${query}`;
  },

  downloadStructuredResume: async (
    resumeId: number,
    format: 'pdf' | 'docx',
    defaultFilename?: string
  ): Promise<void> => {
    const token = getStoredToken();
    if (!token) {
      throw new Error('Please log in to export your resume');
    }
    const downloadUrl = api.getStructuredResumeExportUrl(resumeId, format);
    const link = document.createElement('a');
    link.style.display = 'none';
    link.href = downloadUrl;
    if (defaultFilename) {
      link.setAttribute('download', defaultFilename);
    }
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      try {
        if (link.parentNode) {
          link.parentNode.removeChild(link);
        }
      } catch (_) {}
    }, 3000);
  },

  // Structured AI Job Tailoring
  getJobResumeTailorSuggestions: (jobId: number, resumeId: number) =>
    request<ResumeTailorSuggestions>(`/jobs/${jobId}/resumes/${resumeId}/tailor`),

  saveJobTailoredResumeCopy: (
    jobId: number,
    resumeId: number,
    data: ResumeSaveTailoredCopyRequest
  ) =>
    request<StructuredResumeItem>(`/jobs/${jobId}/resumes/${resumeId}/tailor/save-copy`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Supervision & Data Management
  superviseUpdateJob: (jobId: number, data: JobSupervisionUpdate) =>
    request<Job>(`/admin/jobs/${jobId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  superviseDeleteJob: (jobId: number, force: boolean = false) =>
    request<{ status: string; job_id: number; forced: boolean }>(`/admin/jobs/${jobId}?force=${force}`, {
      method: 'DELETE',
    }),

  getAllScrapingRuns: (limit: number = 50) =>
    request<ScrapingRunItem[]>(`/admin/scraping-runs?limit=${limit}`),

  testScraperDiagnostic: (data: ScraperDiagnosticRequest) =>
    request<ScraperDiagnosticResponse>('/admin/scraper/test', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

export interface CompanyCreate {
  name: string;
  website_url: string;
  careers_url?: string | null;
  active?: boolean;
  country_ids?: number[];
}

export interface CompanyUpdate {
  name?: string;
  website_url?: string;
  careers_url?: string | null;
  active?: boolean;
  country_ids?: number[];
}

export interface ScrapeTargetCreate {
  company_id: number;
  url: string;
  type?: string | null;
  active?: boolean;
}

export interface ScrapeTargetUpdate {
  url?: string;
  type?: string | null;
  active?: boolean;
}

export interface AIModel {
  name: string;
  size?: number;
  modified_at?: string;
  parameter_size?: string;
  quantization_level?: string;
}

export interface AIStatus {
  provider: string;
  url: string;
  status: string;
  models: AIModel[];
  selected_model: string | null;
  selected_model_available: boolean;
  error: string | null;
}

export interface AIProvider {
  id: string;
  name: string;
  status: string;
  enabled: boolean;
  is_local: boolean;
  endpoint?: string | null;
  models_count: number;
}

export interface AIChatResponse {
  answer: string;
  facts: Record<string, any>;
  provider: string;
  model: string | null;
  ollama_available: boolean;
}

export interface ResumeSections {
  summary?: string;
  experience?: string;
  education?: string;
  skills?: string[];
  projects?: string;
  certifications?: string;
  languages?: string[];
}

export interface ResumeItem {
  id: number;
  user_id: number;
  filename: string;
  parsed_sections?: ResumeSections | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ActionableRecommendation {
  requirement: string;
  status: string;
  weakness: string;
  suggested_action: string;
  location: string;
}

export interface ResumeSuggestion {
  job_id: number;
  job_title: string;
  already_demonstrated: string[];
  missing_or_weak: string[];
  ats_improvements?: string[];
  actionable_recommendations?: ActionableRecommendation[];
  suggestions: string[];
  requirements_status: string;
  ai_enhanced: boolean;
  provider: string;
}

export interface CustomizedResumeItem {
  id: number;
  user_id: number;
  base_resume_id: number;
  job_id: number;
  version: number;
  pdf_filename?: string | null;
  docx_filename?: string | null;
  ats_analysis?: Record<string, any> | null;
  recommendations?: ActionableRecommendation[] | null;
  created_at: string;
}

export interface JobSupervisionUpdate {
  title?: string;
  description?: string;
  location?: string;
  department?: string;
  employment_type?: string;
  remote_type?: string;
  job_url?: string;
  active?: boolean;
}

export interface ScrapingRunItem {
  id: number;
  company_id: number;
  status: string;
  started_at: string;
  finished_at?: string | null;
  jobs_found: number;
  jobs_added: number;
  jobs_updated: number;
  error_message?: string | null;
}

export interface ScraperDiagnosticRequest {
  url: string;
  strategy?: string;
  max_pages?: number;
}

export interface ScraperDiagnosticResponse {
  target_url: string;
  strategy_used: string;
  platform_detected?: string | null;
  execution_time_seconds: number;
  jobs_discovered: number;
  jobs_accepted: number;
  jobs_rejected: number;
  confidence_score: number;
  status: string;
  errors: string[];
  sample_jobs: Array<{
    title: string;
    location?: string;
    job_url: string;
    employment_type?: string;
    skills_count?: number;
  }>;
  http_status?: number | null;
  content_type?: string | null;
  rendering_mode?: string | null;
  discovery_method?: string | null;
  failure_reason?: string | null;
}
