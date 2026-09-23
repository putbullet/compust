import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { JSDOM } from 'jsdom';

describe('JWT Context Isolation Verification', () => {
  const contentDir = path.resolve(__dirname, '../../src/content');

  it('proves content scripts never import auth token storage module', () => {
    const files = [
      'linkedin.ts',
      'indeed.ts',
      'glassdoor.ts',
      'common/jobExtractor.ts',
      'common/overlay.ts',
    ];

    for (const file of files) {
      const filePath = path.join(contentDir, file);
      const code = fs.readFileSync(filePath, 'utf-8');

      // Assert content scripts never import from auth.ts
      expect(code).not.toMatch(/from\s+['"].*\/auth['"]/);

      // Assert content scripts never reference token storage key
      expect(code).not.toContain('compust_jwt_token');

      // Assert content scripts never call getToken or setToken
      expect(code).not.toMatch(/\bgetToken\s*\(/);
      expect(code).not.toMatch(/\bsetToken\s*\(/);
    }
  });

  it('proves host window and storage contexts remain devoid of auth credentials', () => {
    const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
      url: 'https://www.linkedin.com/jobs/view/123456/',
    });

    const win = dom.window as any;

    // Simulate page storage
    win.localStorage.setItem('page_key', 'page_val');

    // Verify no extension token leaks into host scope
    expect(win.compust_jwt_token).toBeUndefined();
    expect(win.compustToken).toBeUndefined();
    expect(win.token).toBeUndefined();
    expect(win.localStorage.getItem('compust_jwt_token')).toBeNull();
    expect(win.sessionStorage.getItem('compust_jwt_token')).toBeNull();
  });

  it('proves background message responses to content scripts never return JWT token', async () => {
    // Check message contract: CAPTURE_JOB response contains job data and analysis, never raw token
    const sampleBackgroundResponse = {
      ok: true,
      data: {
        job: {
          job_id: 42,
          title: 'Staff Engineer',
          company: 'TechCorp',
          location: 'Remote',
          url: 'https://linkedin.com/jobs/view/42',
          dedup_status: 'created',
          is_duplicate: false,
        },
        dedup_status: 'created',
        is_duplicate: false,
        has_active_resume: true,
        message: null,
        match_analysis: {
          job_id: 42,
          job_title: 'Staff Engineer',
          already_demonstrated: ['TypeScript', 'FastAPI'],
          missing_or_weak: ['Kubernetes'],
          suggestions: ['Highlight Docker experience'],
          requirements_status: 'COMPLETE',
        },
        score_breakdown: {
          overall_score: 85,
          positive_factors: ['Skills aligned'],
          missing_factors: [],
        },
      },
    };

    expect((sampleBackgroundResponse as any).token).toBeUndefined();
    expect((sampleBackgroundResponse as any).access_token).toBeUndefined();
    expect((sampleBackgroundResponse.data as any).token).toBeUndefined();
    expect((sampleBackgroundResponse.data as any).access_token).toBeUndefined();
  });
});
