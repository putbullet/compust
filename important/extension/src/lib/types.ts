export interface JobPayload {
  title: string | null;
  company: string | null;
  location: string | null;
  description: string | null;
  employment_type?: string | null;
  remote_type?: string | null;
  url: string;
  source: string;
}

export interface JobQuickAddResult {
  job_id: number;
  title: string;
  company: string;
  location: string | null;
  url: string;
  dedup_status: 'created' | 'existing';
  is_duplicate: boolean;
  resume_suggestions?: any;
  application_id?: number | null;
  application_status?: string | null;
}

export interface ResumeEditSuggestionItem {
  id: string;
  section: 'skills' | 'experience' | 'summary' | 'projects';
  item_label: string;
  action: 'add' | 'emphasize' | 'clarify' | 'missing';
  where: string;
  suggested_text: string;
  reason: string;
  grounded: boolean;
}

export interface EphemeralAnalyzeResult {
  title: string;
  company: string;
  location: string | null;
  url: string;
  has_active_resume: boolean;
  message: string | null;
  match_score: number | null;
  positive_factors: string[];
  missing_factors: string[];
  demonstrated_skills: string[];
  missing_skills: string[];
  resume_suggestions: ResumeEditSuggestionItem[];
  visa_analysis?: { mentioned: boolean; snippet?: string | null } | null;
  content_hash: string;
}

export interface GenericExtractResult {
  title: string | null;
  company: string | null;
  location: string | null;
  description: string | null;
  employment_type?: string | null;
  remote_type?: string | null;
  confidence: 'high' | 'medium' | 'low';
  normalized_title?: string | null;
  message?: string | null;
}

export interface MatchAnalysis {
  job_id: number;
  job_title: string;
  already_demonstrated: string[];
  missing_or_weak: string[];
  ats_improvements?: string[];
  actionable_recommendations?: Array<{
    requirement: string;
    status: string;
    weakness: string;
    suggested_action: string;
    location: string;
  }>;
  suggestions: string[];
  requirements_status: string;
  ai_enhanced?: boolean;
  provider?: string;
}

export interface ScoreBreakdown {
  overall_score: number;
  positive_factors: string[];
  missing_factors: string[];
  category_scores?: Record<string, number>;
}

export interface QuickAddAndAnalyzeResult {
  job: JobQuickAddResult;
  dedup_status: 'created' | 'existing';
  is_duplicate: boolean;
  has_active_resume: boolean;
  message: string | null;
  match_analysis: MatchAnalysis | null;
  score_breakdown: ScoreBreakdown | null;
}

export interface ExtensionSettings {
  backendUrl: string;
}

export interface UserProfile {
  id: number;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
}

export interface ActiveResumeInfo {
  id: number;
  title?: string;
  filename: string;
  is_active: boolean;
}

export type ExtensionMessage =
  | { type: 'CHECK_STATUS' }
  | { type: 'GET_SETTINGS' }
  | { type: 'SAVE_SETTINGS'; settings: ExtensionSettings }
  | { type: 'LOGIN'; email: string; password: string }
  | { type: 'LOGOUT' }
  | { type: 'CAPTURE_JOB'; payload: JobPayload }
  | { type: 'ANALYZE_EPHEMERAL_JOB'; payload: JobPayload }
  | {
      type: 'SAVE_JOB_ACTION';
      payload: JobPayload;
      applicationStatus: 'untracked' | 'saved' | 'applied';
      resumeSuggestions?: ResumeEditSuggestionItem[];
    }
  | { type: 'EXTRACT_GENERIC_JOB'; html: string; url: string }
  | { type: 'TOGGLE_CAPTURE_PANEL' }
  | { type: 'TRACK_APPLICATION'; jobId: number; status: 'applied' | 'saved' }
  | { type: 'ACTIVATE_CAPTURE_ON_TAB'; tabId?: number }
  | { type: 'TEST_CONNECTION'; url?: string };
