import { JobPayload, QuickAddAndAnalyzeResult, UserProfile, ActiveResumeInfo } from './types';

export class CompustApiError extends Error {
  status?: number;
  isNetworkError: boolean;

  constructor(message: string, status?: number, isNetworkError = false) {
    super(message);
    this.name = 'CompustApiError';
    this.status = status;
    this.isNetworkError = isNetworkError;
  }
}

export async function checkBackendHealth(backendUrl: string): Promise<{ ok: boolean; database?: string; error?: string }> {
  try {
    const res = await fetch(`${backendUrl}/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      return { ok: false, error: `Backend responded with HTTP ${res.status}` };
    }
    const data = await res.json();
    return { ok: true, database: data.database };
  } catch (err: any) {
    return {
      ok: false,
      error: "Compust isn't running — start the app and try again",
    };
  }
}

export async function loginToBackend(
  backendUrl: string,
  email: string,
  password: string
): Promise<{ token: string; user: UserProfile }> {
  try {
    const res = await fetch(`${backendUrl}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      const detail = errorBody.detail || `Login failed (HTTP ${res.status})`;
      throw new CompustApiError(detail, res.status);
    }

    const data = await res.json();
    return {
      token: data.access_token,
      user: data.user,
    };
  } catch (err: any) {
    if (err instanceof CompustApiError) throw err;
    throw new CompustApiError("Compust isn't running — start the app and try again", undefined, true);
  }
}

export async function quickAddAndAnalyzeJob(
  backendUrl: string,
  token: string,
  payload: JobPayload
): Promise<QuickAddAndAnalyzeResult> {
  try {
    const res = await fetch(`${backendUrl}/api/v1/jobs/quick-add-and-analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (res.status === 401) {
      throw new CompustApiError('Session expired. Please log in to Compust.', 401);
    }
    if (res.status === 405) {
      throw new CompustApiError('Backend API mismatch — please restart Compust and reload the extension.', 405);
    }
    if (res.status === 429) {
      throw new CompustApiError('Rate limit exceeded. Please wait a moment before capturing more jobs.', 429);
    }
    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      throw new CompustApiError(errorBody.detail || `Server error (${res.status})`, res.status);
    }

    return await res.json();
  } catch (err: any) {
    if (err instanceof CompustApiError) throw err;
    throw new CompustApiError("Compust isn't running — start the app and try again", undefined, true);
  }
}

export async function trackJobApplication(
  backendUrl: string,
  token: string,
  jobId: number,
  status: 'applied' | 'saved'
): Promise<any> {
  try {
    const res = await fetch(`${backendUrl}/api/v1/applications/${jobId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ status, source: 'Compust Extension' }),
    });

    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      throw new CompustApiError(errorBody.detail || `Failed to track application (${res.status})`, res.status);
    }

    return await res.json();
  } catch (err: any) {
    if (err instanceof CompustApiError) throw err;
    throw new CompustApiError("Compust isn't running — start the app and try again", undefined, true);
  }
}

export async function fetchActiveResume(
  backendUrl: string,
  token: string
): Promise<ActiveResumeInfo | null> {
  try {
    const res = await fetch(`${backendUrl}/api/v1/resumes/active`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });

    if (res.status === 404) {
      return null;
    }
    if (!res.ok) {
      return null;
    }

    return await res.json();
  } catch {
    return null;
  }
}

export async function analyzeEphemeralJob(
  backendUrl: string,
  token: string,
  payload: JobPayload
): Promise<import('./types').EphemeralAnalyzeResult> {
  try {
    const res = await fetch(`${backendUrl}/api/v1/jobs/analyze-ephemeral`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (res.status === 401) {
      throw new CompustApiError('Session expired. Please log in to Compust.', 401);
    }
    if (res.status === 405) {
      throw new CompustApiError('Backend API mismatch — please restart Compust and reload the extension.', 405);
    }
    if (res.status === 429) {
      throw new CompustApiError('Rate limit exceeded. Please wait a moment before analyzing more jobs.', 429);
    }
    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      throw new CompustApiError(errorBody.detail || `Server error (${res.status})`, res.status);
    }

    return await res.json();
  } catch (err: any) {
    if (err instanceof CompustApiError) throw err;
    throw new CompustApiError("Compust isn't running — start the app and try again", undefined, true);
  }
}

export async function saveJobWithAction(
  backendUrl: string,
  token: string,
  payload: JobPayload,
  applicationStatus: 'untracked' | 'saved' | 'applied',
  resumeSuggestions?: any
): Promise<import('./types').JobQuickAddResult> {
  try {
    const statusParam = applicationStatus === 'untracked' ? null : applicationStatus;
    const bodyPayload = {
      ...payload,
      application_status: statusParam,
      resume_suggestions: resumeSuggestions,
    };

    const res = await fetch(`${backendUrl}/api/v1/jobs/quick-add`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(bodyPayload),
    });

    if (res.status === 401) {
      throw new CompustApiError('Session expired. Please log in to Compust.', 401);
    }
    if (res.status === 405) {
      throw new CompustApiError('Backend API mismatch — please restart Compust and reload the extension.', 405);
    }
    if (res.status === 429) {
      throw new CompustApiError('Rate limit exceeded. Please wait a moment before saving more jobs.', 429);
    }
    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      throw new CompustApiError(errorBody.detail || `Server error (${res.status})`, res.status);
    }

    return await res.json();
  } catch (err: any) {
    if (err instanceof CompustApiError) throw err;
    throw new CompustApiError("Compust isn't running — start the app and try again", undefined, true);
  }
}

export async function extractJobFromHtml(
  backendUrl: string,
  token: string,
  html: string,
  url: string
): Promise<import('./types').GenericExtractResult> {
  try {
    const res = await fetch(`${backendUrl}/api/v1/jobs/extract-from-html`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ html, url }),
    });

    if (res.status === 401) {
      throw new CompustApiError('Session expired. Please log in to Compust.', 401);
    }
    if (res.status === 405) {
      throw new CompustApiError('Backend API mismatch — please restart Compust and reload the extension.', 405);
    }
    if (res.status === 429) {
      throw new CompustApiError('Rate limit exceeded. Please wait a moment before extracting jobs.', 429);
    }
    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      throw new CompustApiError(errorBody.detail || `Server error (${res.status})`, res.status);
    }

    return await res.json();
  } catch (err: any) {
    if (err instanceof CompustApiError) throw err;
    throw new CompustApiError("Compust isn't running — start the app and try again", undefined, true);
  }
}
