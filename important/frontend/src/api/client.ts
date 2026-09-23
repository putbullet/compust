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

export interface ResumeEditSuggestionItem {
  section: string;
  original_text?: string | null;
  suggested_text: string;
  rationale: string;
  target_location?: string | null;
  grounded: boolean;
  warning?: string | null;
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
  company_name?: string | null;
  country_name?: string | null;
  resume_suggestions?: ResumeEditSuggestionItem[] | { suggestions: ResumeEditSuggestionItem[] } | any;
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
  proficiency?: string | null;
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
  proficiency?: string | null;
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
  language?: 'en' | 'fr' | 'de' | string;
  theme_color: string;
  font_family: string;
  font_size: string;
  document_size: 'A4' | 'LETTER';
  section_order: string[];
  section_visibility: Record<string, boolean>;
  section_titles?: Record<string, string>;
}


export interface StructuredResumeItem {
  id: number;
  user_id: number;
  title: string;
  is_active: boolean;
  is_default: boolean;
  target_job_id: number | null;
  source_resume_id: number | null;
  is_original_upload?: boolean;
  structured_data: StructuredResumeData;
  settings: ResumeSettings;
  created_at: string;
  updated_at: string;
}

export interface RenderResumePreviewResponse {
  pages: string[];
  page_count: number;
  engine: string;
  theme: string;
}

export interface ATSCategoryScore {
  category: 'parseability' | 'keywords' | 'sections' | 'impact' | 'formatting' | 'contact' | string;
  name: string;
  score: number;
  max_score: number;
  status: 'pass' | 'warning' | 'critical';
  notes: string;
}

export interface ATSFeedbackItem {
  id: string;
  category: string;
  severity: 'critical' | 'warning' | 'tip' | 'pass';
  title: string;
  message: string;
  recommendation: string;
  grounded_quote?: string | null;
}

export interface ATSCheckResult {
  overall_score: number;
  verdict: 'Strong Match' | 'Competitive' | 'Needs Optimization' | 'High ATS Rejection Risk' | string;
  categories: ATSCategoryScore[];
  feedback: ATSFeedbackItem[];
  keywords_found: string[];
  keywords_missing: string[];
  recommended_action_verbs: string[];
  provider: 'ollama' | 'deterministic' | string;
  model?: string | null;
}

export interface ResumeATSCheckPayload {
  target_role?: string;
  target_field?: string;
  job_id?: number;
  structured_data?: StructuredResumeData;
  raw_text?: string;
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

export type ApplicationStatus =
  | 'saved'
  | 'applied'
  | 'no_answer'
  | 'interviewing'
  | '1st_interview'
  | '2nd_interview'
  | '3rd_interview'
  | 'final_interview'
  | 'offer'
  | 'accepted'
  | 'rejected'
  | 'withdrawn';

export interface ApplicationHistoryItem {
  id: number;
  application_id: number;
  from_status: string | null;
  to_status: string;
  changed_at: string;
  notes: string | null;
}

export interface ApplicationItem {
  id: number;
  user_id: number;
  job_id: number | null;
  status: ApplicationStatus;
  notes: string | null;
  applied_at: string | null;
  created_at: string;
  updated_at: string;
  source: string;
  custom_job_title?: string | null;
  custom_company_name?: string | null;
  custom_location?: string | null;
  custom_country?: string | null;
  custom_job_url?: string | null;
  salary?: string | null;
  employment_type?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  recruiter?: string | null;
  referral?: string | null;
  priority?: 'low' | 'medium' | 'high' | string;
  next_follow_up?: string | null;
  interview_date?: string | null;
  effective_title: string;
  effective_company: string;
  effective_location?: string | null;
  effective_country?: string | null;
  effective_job_url?: string | null;
  job?: Job | null;
  history?: ApplicationHistoryItem[];
  resume_suggestions?: ResumeEditSuggestionItem[] | { suggestions: ResumeEditSuggestionItem[] } | any;
}

export interface ManualApplicationPayload {
  job_title: string;
  company_name: string;
  source?: string;
  status?: ApplicationStatus | string;
  location?: string;
  country?: string;
  job_url?: string;
  applied_at?: string;
  salary?: string;
  employment_type?: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  recruiter?: string;
  referral?: string;
  priority?: string;
  notes?: string;
  next_follow_up?: string;
  interview_date?: string;
}

export interface ApplicationUpdatePayload {
  status?: ApplicationStatus | string;
  notes?: string;
  applied_at?: string | null;
  job_title?: string;
  company_name?: string;
  location?: string;
  country?: string;
  job_url?: string;
  source?: string;
  salary?: string;
  employment_type?: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  recruiter?: string;
  referral?: string;
  priority?: string;
  next_follow_up?: string | null;
  interview_date?: string | null;
}

export interface ApplicationStats {
  total_applications: number;
  active_applications: number;
  status_breakdown: Record<string, number>;
  source_breakdown: Record<string, number>;
  interview_rate_percent: number;
  response_rate_percent: number;
  offer_rate_percent: number;
  acceptance_rate_percent: number;
  rejection_rate_percent: number;
  avg_days_to_interview: number | null;
  avg_days_to_offer: number | null;
}

export interface SankeyNode {
  id: string;
  label: string;
  stage_index: number;
  count: number;
  color: string;
}

export interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

export interface SankeyData {
  nodes: SankeyNode[];
  links: SankeyLink[];
  total: number;
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
      if (errorJson.detail) {
        if (typeof errorJson.detail === 'string') {
          errorDetail = errorJson.detail;
        } else if (Array.isArray(errorJson.detail)) {
          errorDetail = errorJson.detail
            .map((item: any) => {
              if (typeof item === 'string') return item;
              if (item && typeof item === 'object') {
                const loc = Array.isArray(item.loc)
                  ? item.loc.filter((x: any) => x !== 'body').join('.')
                  : '';
                const msg = item.msg || JSON.stringify(item);
                return loc ? `${loc}: ${msg}` : msg;
              }
              return String(item);
            })
            .join('; ');
        } else if (typeof errorJson.detail === 'object') {
          errorDetail = JSON.stringify(errorJson.detail);
        }
      }
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

  resetPassword: (email: string, new_password: string) =>
    request<AuthResponse>('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ email, new_password }),
    }),

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
  getApplications: (params?: {
    status?: string;
    source?: string;
    country?: string;
    search?: string;
    start_date?: string;
    end_date?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.status) q.append('status', params.status);
    if (params?.source) q.append('source', params.source);
    if (params?.country) q.append('country', params.country);
    if (params?.search) q.append('search', params.search);
    if (params?.start_date) q.append('start_date', params.start_date);
    if (params?.end_date) q.append('end_date', params.end_date);
    const qs = q.toString();
    return request<ApplicationItem[]>(qs ? `/applications?${qs}` : '/applications');
  },

  createManualApplication: (data: ManualApplicationPayload) =>
    request<ApplicationItem>('/applications', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  trackApplication: (jobId: number, data?: { status?: string; notes?: string; source?: string }) =>
    request<ApplicationItem>(`/applications/${jobId}`, {
      method: 'POST',
      body: JSON.stringify(data || { status: 'saved' }),
    }),

  updateApplication: (applicationId: number, data: ApplicationUpdatePayload) =>
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

  getApplicationStats: (startDate?: string, endDate?: string) => {
    const q = new URLSearchParams();
    if (startDate) q.append('start_date', startDate);
    if (endDate) q.append('end_date', endDate);
    const qs = q.toString();
    return request<ApplicationStats>(qs ? `/applications/stats?${qs}` : '/applications/stats');
  },

  getPipelineData: (params?: { source?: string; country?: string; start_date?: string; end_date?: string }) => {
    const q = new URLSearchParams();
    if (params?.source) q.append('source', params.source);
    if (params?.country) q.append('country', params.country);
    if (params?.start_date) q.append('start_date', params.start_date);
    if (params?.end_date) q.append('end_date', params.end_date);
    const qs = q.toString();
    return request<SankeyData>(qs ? `/applications/pipeline?${qs}` : '/applications/pipeline');
  },

  exportApplicationsXlsx: async () => {
    const token = getStoredToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(`${API_BASE_URL}/applications/export`, {
      method: 'GET',
      headers,
    });
    if (!res.ok) {
      throw new Error(`Export failed with status ${res.status}`);
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `compust_applications_${new Date().toISOString().slice(0, 10)}.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },

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

  refreshJobResumeSuggestions: (jobId: number) =>
    request<JobDetail>(`/jobs/${jobId}/resume-suggestions?refresh=true`, {
      method: 'PUT',
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

  createStudioCopy: (resumeId: number) =>
    request<StructuredResumeItem>(`/resumes/${resumeId}/create-studio-copy`, {
      method: 'POST',
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

  importProfileToStructuredResume: (resumeId: number) =>
    request<StructuredResumeItem>(`/resumes/${resumeId}/import-profile`, {
      method: 'POST',
    }),

  renderStructuredResumePreview: (
    resumeId: number,
    data?: {
      structured_data?: StructuredResumeData;
      settings?: ResumeSettings;
    }
  ) =>
    request<RenderResumePreviewResponse>(`/resumes/${resumeId}/render-preview`, {
      method: 'POST',
      body: JSON.stringify(data || {}),
    }),

  runResumeATSCheck: (resumeId: number, payload?: ResumeATSCheckPayload) =>
    request<ATSCheckResult>(`/resumes/${resumeId}/ats-check`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
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

  superviseBulkDeleteJobs: (jobIds: number[], force: boolean = false) =>
    request<{ status: string; deleted_count: number; deactivated_count: number; total_requested: number }>(
      '/admin/jobs/bulk-delete',
      {
        method: 'POST',
        body: JSON.stringify({ job_ids: jobIds, force }),
      }
    ),

  getAllScrapingRuns: (limit: number = 50) =>
    request<ScrapingRunItem[]>(`/admin/scraping-runs?limit=${limit}`),

  testScraperDiagnostic: (data: ScraperDiagnosticRequest) =>
    request<ScraperDiagnosticResponse>('/admin/scraper/test', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  explainScraperDiagnostic: (report: any) =>
    request<ScraperExplainResponse>('/admin/scraper/explain', {
      method: 'POST',
      body: JSON.stringify({ report }),
    }),

  applyScraperDecision: (data: ScraperDecisionRequest) =>
    request<ScraperDecisionResponse>('/admin/scraper/apply-decision', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  searchInternships: (params: InternshipSearchParams) =>
    request<InternshipSearchResponse>('/internships/search', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  getCuratedGitHubInternships: (params: GitHubInternshipsParams = {}) => {
    const q = new URLSearchParams();
    if (params.repo_id) q.set('repo_id', params.repo_id);
    if (params.visa_status) q.set('visa_status', params.visa_status);
    if (params.category) q.set('category', params.category);
    if (params.search) q.set('search', params.search);
    if (params.open_only !== undefined) q.set('open_only', params.open_only.toString());
    const queryStr = q.toString() ? `?${q.toString()}` : '';
    return request<GitHubInternshipsResponse>(`/internships/github-repos${queryStr}`);
  },

  syncCuratedGitHubInternships: () =>
    request<GitHubInternshipsResponse>('/internships/github-repos/sync', {
      method: 'POST',
    }),

  // Job-Specific Resume & Career Assistant
  analyzeJobTarget: (resumeId: number, input: ExternalJobInput) =>
    request<JobTargetAnalysisResult>(`/resumes/${resumeId}/job-target/analyze`, {
      method: 'POST',
      body: JSON.stringify(input),
    }),

  saveTailoredCopyFromJobTarget: (resumeId: number, data: SaveTailoredFromJobTargetRequest) =>
    request<StructuredResumeItem>(`/resumes/${resumeId}/job-target/save-tailored-copy`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  regenerateApplicationMaterial: (resumeId: number, data: RegenerateMaterialRequest) =>
    request<ApplicationMaterial>(`/resumes/${resumeId}/job-target/regenerate-material`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  exportMotivationLetter: async (
    resumeId: number,
    data: ExportDocumentRequest,
    defaultFilename?: string
  ): Promise<void> => {
    const token = getStoredToken();
    if (!token) throw new Error('Please log in to export documents');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };
    const response = await fetch(`${API_BASE_URL}/resumes/${resumeId}/job-target/export-letter`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Export failed' }));
      throw new Error(err.detail || 'Export failed');
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = defaultFilename || `${data.suggested_filename}.${data.file_format}`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { try { if (a.parentNode) a.parentNode.removeChild(a); } catch (_) {} }, 3000);
    window.URL.revokeObjectURL(url);
  },

  // Interview Prep Knowledge Center
  getBehavioralPrep: (lang: string = 'en') =>
    request<BehavioralPrepResponse>(`/interview-prep/behavioral?lang=${encodeURIComponent(lang)}`),

  getInterviewDomains: () =>
    request<InterviewDomainSummary[]>('/interview-prep/domains'),

  getInterviewDomainTree: (domainId: string) =>
    request<InterviewDomainTree>(`/interview-prep/domains/${encodeURIComponent(domainId)}/tree`),

  getInterviewQuestionDetail: (domainId: string, slug: string) =>
    request<InterviewQuestionDetail>(
      `/interview-prep/questions/${encodeURIComponent(domainId)}/${encodeURIComponent(slug)}`
    ),

  searchInterviewQuestions: (query: string, domainId?: string) => {
    const params = new URLSearchParams({ q: query });
    if (domainId) params.set('domain_id', domainId);
    return request<InterviewQuestionSummary[]>(`/interview-prep/search?${params.toString()}`);
  },

  explainInterviewQuestionAI: (
    domainId: string,
    slug: string,
    mode: string = 'simplify',
    userDraftAnswer?: string,
    language: string = 'en'
  ) =>
    request<QuestionAIExplainResponse>(
      `/interview-prep/questions/${encodeURIComponent(domainId)}/${encodeURIComponent(slug)}/ai-explain`,
      {
        method: 'POST',
        body: JSON.stringify({ mode, user_draft_answer: userDraftAnswer, language }),
      }
    ),

  evaluateSTARDraft: (payload: STAREvaluationRequest) =>
    request<STAREvaluationResponse>(
      '/interview-prep/evaluate-star',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),
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
  is_original_upload?: boolean;
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
  detected_result_count?: number | null;
  pages_crawled?: number;
  total_jobs_detected?: number;
  rejection_reasons?: Record<string, number>;
  rejected_items?: Array<{
    title?: string;
    url?: string;
    reason?: string;
    company?: string;
    location?: string;
    [key: string]: any;
  }>;
  max_pages?: number;
  stop_reason?: string;
  content_signal_count?: number;
  discrepancy_detected?: boolean;
  discrepancy_details?: string | null;
  explanation?: any;
  suggested_action?: string | null;
}

export interface ScraperExplainResponse {
  summary: string;
  reasons_breakdown: Record<string, string>;
  discrepancy_explanation: string | null;
  recommendations: string[];
  provider: string;
}

export interface ScraperDecisionRequest {
  target_url: string;
  decision: 'keep_accepted' | 'force_integrate_all' | string;
  rejected_items?: Array<Record<string, any>>;
}

export interface ScraperDecisionResponse {
  status: string;
  action: string;
  integrated_count: number;
  message: string;
}


export interface InternshipOpportunity {
  id: string;
  title: string;
  company: string;
  location: string;
  country: string;
  description: string;
  requirements: string[];
  qualifications: string[];
  internship_type: string;
  duration?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  application_deadline?: string | null;
  publication_date?: string | null;
  source_url: string;
  application_url: string;
  source_domain: string;
  language: string;
  confidence_score: number;
  is_year_match: boolean;
}

export interface InternshipSearchDiagnostics {
  queries_executed: string[];
  sources_discovered: number;
  sources_checked: number;
  sources_unavailable: number;
  sources_rejected_non_job: number;
  valid_opportunities_found: number;
  execution_time_ms: number;
}

export interface InternshipSearchResponse {
  opportunities: InternshipOpportunity[];
  diagnostics: InternshipSearchDiagnostics;
  related_titles: string[];
}

export interface InternshipSearchParams {
  field: string;
  country?: string | null;
  year?: number | string | null;
  max_results?: number;
}

export type GitHubVisaStatus =
  | 'sponsors_visa'
  | 'no_sponsorship'
  | 'us_citizen_only'
  | 'canada_authorized'
  | 'not_specified'
  | 'closed';

export interface GitHubInternshipItem {
  id: string;
  company: string;
  company_domain?: string | null;
  logo_url?: string | null;
  role: string;
  location: string;
  country?: string | null;
  category: string;
  season: string;
  source_repo_id: string;
  source_repo_name: string;
  source_repo_url: string;
  apply_url: string;
  date_posted?: string | null;
  visa_status: GitHubVisaStatus;
  visa_text: string;
  is_closed: boolean;
  notes?: string | null;
}

export interface GitHubRepoMeta {
  id: string;
  name: string;
  url: string;
  raw_url: string;
  region: string;
  year: string;
  description: string;
  item_count: number;
}

export interface GitHubInternshipStats {
  total_listings: number;
  active_listings: number;
  closed_listings: number;
  visa_sponsored_count: number;
  no_sponsorship_count: number;
  us_citizens_count: number;
  canada_authorized_count: number;
  not_specified_count: number;
  repos_count: number;
  last_synced_at?: string | null;
  by_repo: Record<string, number>;
  by_category: Record<string, number>;
}

export interface GitHubInternshipsResponse {
  items: GitHubInternshipItem[];
  stats: GitHubInternshipStats;
  repositories: GitHubRepoMeta[];
  categories: string[];
}

export interface GitHubInternshipsParams {
  repo_id?: string | null;
  visa_status?: string | null;
  category?: string | null;
  search?: string | null;
  open_only?: boolean;
}

// ---------------------------------------------------------------------------
// Job-Specific Resume & Career Assistant Types
// ---------------------------------------------------------------------------

export type SupportedLanguage = 'en' | 'fr' | 'de' | 'es';

export interface ExternalJobInput {
  target_role: string;
  job_description: string;
  additional_information?: string;
  language?: SupportedLanguage;
}

export type RequirementCategory =
  | 'technical_skill' | 'tool' | 'methodology' | 'education'
  | 'experience' | 'language' | 'certification' | 'domain'
  | 'soft_skill' | 'ats_keyword' | 'other';

export type RequirementImportance = 'required' | 'preferred' | 'nice_to_have';

export interface JobRequirement {
  text: string;
  category: RequirementCategory;
  importance: RequirementImportance;
  raw_keyword: string;
}

export type MatchStatus = 'strong' | 'partial' | 'missing' | 'verify' | 'unknown';

export interface CandidateEvidenceMatch {
  requirement: string;
  requirement_category: RequirementCategory;
  match_status: MatchStatus;
  evidence_sources: string[];
  note: string;
}

export interface MatchAnalysis {
  strong_matches: CandidateEvidenceMatch[];
  partial_matches: CandidateEvidenceMatch[];
  missing_or_unconfirmed: CandidateEvidenceMatch[];
  verify_items: CandidateEvidenceMatch[];
}

export interface DeterministicScore {
  technical_skills: number;
  experience_alignment: number;
  education: number;
  languages: number;
  ats_keywords: number;
  overall: number;
  methodology: string;
}

export type RecommendationType =
  | 'keep' | 'emphasize' | 'rewrite' | 'move'
  | 'add' | 'missing' | 'verify' | 'reduce' | 'remove';

export interface ResumeRecommendation {
  id: string;
  rec_type: RecommendationType;
  section: string;
  item_id: string;
  item_label: string;
  current_text: string;
  suggested_text: string;
  reason: string;
  evidence_sources: string[];
  grounded: boolean;
}

export type MaterialType = 'cold_email' | 'short_message' | 'motivation_letter';

export interface ApplicationMaterial {
  material_type: MaterialType;
  subject: string;
  body: string;
  placeholders: string[];
  language: string;
  generated: boolean;
  error: string;
}

export type InterviewQuestionType = 'behavioral' | 'technical' | 'domain' | 'qualification_gap';

export interface STARResponse {
  situation: string;
  task: string;
  action: string;
  result: string;
}

export interface InterviewQuestion {
  id: string;
  question: string;
  question_type: InterviewQuestionType;
  category: string;
  context_reason: string;
  suggested_star: STARResponse;
  handling_missing_skill: string;
}

export interface InterviewPrep {
  questions: InterviewQuestion[];
  key_focus_areas: string[];
  confidence_tip: string;
}

export interface JobTargetAnalysisResult {
  resume_id: number;
  target_role: string;
  language: string;
  job_requirements: JobRequirement[];
  match_analysis: MatchAnalysis;
  deterministic_score: DeterministicScore;
  resume_recommendations: ResumeRecommendation[];
  cold_email: ApplicationMaterial;
  short_message: ApplicationMaterial;
  motivation_letter: ApplicationMaterial;
  interview_prep?: InterviewPrep;
  ollama_used: boolean;
  ollama_model: string | null;
  partial_failure: boolean;
  partial_failure_detail: string;
  data_conflicts: string[];
}

export interface SaveTailoredFromJobTargetRequest {
  new_title: string;
  accepted_recommendation_ids: string[];
  accepted_recommendations: ResumeRecommendation[];
}

export interface ExportDocumentRequest {
  content: string;
  file_format: 'pdf' | 'docx';
  suggested_filename: string;
}

export interface RegenerateMaterialRequest {
  material_type: MaterialType;
  target_role: string;
  job_description: string;
  additional_information?: string;
  language?: SupportedLanguage;
}

// ============================================================================
// Interview Prep Knowledge Center Types
// ============================================================================

export interface STARStep {
  step: string;
  definition: string;
  key_points: string[];
  example: string;
}

export interface STARGuide {
  title: string;
  what_is_star: string;
  when_to_use: string;
  how_to_structure: string;
  what_makes_answer_strong: string[];
  common_mistakes: string[];
  steps: STARStep[];
}

export interface BehavioralQuestionItem {
  id: string;
  category: string;
  question: string;
  intent: string;
  recommended_structure: string[];
  strong_example_answer: string;
  common_pitfalls: string[];
  self_reflection_prompt: string;
}

export interface StoryPillar {
  name: string;
  focus: string;
  applies_to: string[];
}

export interface StoryMatrix {
  title: string;
  description: string;
  pillars: StoryPillar[];
}

export interface InterviewModuleItem {
  id: string;
  title: string;
  summary: string;
}

export interface BehavioralPrepResponse {
  language: string;
  star_guide: STARGuide;
  questions: BehavioralQuestionItem[];
  story_matrix?: StoryMatrix;
  interview_modules?: InterviewModuleItem[];
}

export interface InterviewQuestionSummary {
  id: string;
  slug: string;
  title: string;
  category: string;
  topic: string;
  difficulty: string;
  experience_level?: string;
  target_roles?: string[];
  estimated_read_time_min: number;
  has_code: boolean;
  has_diagram: boolean;
}

export interface InterviewTopic {
  id: string;
  title: string;
  description?: string | null;
  questions: InterviewQuestionSummary[];
}

export interface InterviewCategory {
  id: string;
  title: string;
  description?: string | null;
  topics: InterviewTopic[];
}

export interface InterviewDomainSummary {
  id: string;
  title: string;
  short_title: string;
  tagline: string;
  description: string;
  hero_illustration: string;
  total_categories: number;
  total_questions: number;
  source_repository: string;
  source_license: string;
  source_url: string;
}

export interface InterviewDomainTree {
  domain: InterviewDomainSummary;
  categories: InterviewCategory[];
}

export interface SourceAttribution {
  repository_name: string;
  repository_url: string;
  source_path: string;
  commit_hash?: string | null;
  license_name: string;
  license_notice: string;
  imported_at: string;
}

export interface InterviewQuestionDetail {
  id: string;
  slug: string;
  domain_id: string;
  domain_title: string;
  category: string;
  topic: string;
  title: string;
  difficulty: string;
  experience_level?: string;
  target_roles?: string[];
  markdown_content: string;
  raw_content?: string | null;
  estimated_read_time_min: number;
  has_code: boolean;
  has_diagram: boolean;
  tags: string[];
  source: SourceAttribution;
  educational_diagram?: string | null;
  educational_diagram_alt?: string | null;
  previous_question?: { id: string; title: string; slug: string } | null;
  next_question?: { id: string; title: string; slug: string } | null;
}

export interface Actor {
  id: string;
  role: 'legitimate_user' | 'attacker' | 'system' | 'database' | 'client' | string;
  label: string;
  description: string;
}

export interface ScenarioStep {
  order: number;
  from?: string;
  from_actor?: string;
  to?: string;
  to_actor?: string;
  action: string;
  payload?: string | null;
  annotation?: string | null;
  status?: 'normal' | 'attack' | 'blocked' | 'secure' | string;
}

export interface ScenarioVariant {
  label: string;
  outcome: 'failure' | 'success' | 'partial' | string;
  steps: ScenarioStep[];
}

export interface Scenario {
  title: string;
  variants: ScenarioVariant[];
}

export interface CodeExplanationLine {
  line: number;
  note: string;
}

export interface CodeSample {
  language: string;
  code: string;
  explanation_lines: CodeExplanationLine[];
}

export interface ComparisonRow {
  criterion: string;
  option_a: string;
  option_b: string;
}

export interface StructuredAIExplanationPayload {
  concept_summary: string;
  analogy: string;
  actors: Actor[];
  scenario: Scenario;
  code_sample?: CodeSample | null;
  comparison_table: ComparisonRow[];
  takeaways: string[];
  common_mistakes: string[];
}

export interface STAREvaluationRequest {
  draft_answer: string;
  question_title?: string;
  language?: string;
}

export interface STAREvaluationResponse {
  star_coverage: {
    situation: boolean;
    task: boolean;
    action: boolean;
    result: boolean;
  };
  action_proportion_estimate: number;
  quantified_metrics_score: number;
  metrics_detected: string[];
  ownership_ratio: {
    i_count: number;
    we_count: number;
    i_percentage: number;
  };
  strengths: string[];
  missing_elements: string[];
  recommendations: string[];
}

export interface QuestionAIExplainResponse {
  question_id: string;
  mode: string;
  explanation: string;
  real_world_scenario?: string | null;
  code_sample?: string | null;
  key_interview_takeaways?: string[];
  structured_payload?: StructuredAIExplanationPayload | null;
  ai_model_used: string;
  is_ai_generated: boolean;
  disclaimer: string;
}



