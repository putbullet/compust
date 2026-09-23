import { describe, it, expect } from 'vitest';
import {
  scanVisaAndWorkAuthorization,
  splitIntoSentences,
} from '../../src/content/common/visaAnalysis';

describe('Deep Analysis: Multilingual Visa & Work-Authorization Screening', () => {
  describe('English Postings', () => {
    it('detects US Citizen only, active security clearance, and no sponsorship with exact quotes', () => {
      const desc = `
        Join our aerospace engineering division.
        We build next-generation satellite communications software.
        Must be a US Citizen due to federal contract requirements.
        Active security clearance is required before start date.
        We cannot provide visa sponsorship for this position.
        Competitive salary and 401(k) matching.
      `;

      const result = scanVisaAndWorkAuthorization(desc);
      expect(result.hasRestriction).toBe(true);
      expect(result.triggerSentences.length).toBeGreaterThanOrEqual(3);
      expect(result.triggerSentences).toContain('Must be a US Citizen due to federal contract requirements.');
      expect(result.triggerSentences).toContain('Active security clearance is required before start date.');
      expect(result.triggerSentences).toContain('We cannot provide visa sponsorship for this position.');

      const labels = result.restrictions.map((r) => r.label);
      expect(labels).toContain('US Citizen Required');
      expect(labels).toContain('Security Clearance Required');
      expect(labels).toContain('No Visa Sponsorship');
    });

    it('detects specific named visa types (H-1B, OPT/CPT, TN)', () => {
      const desc = `
        Software Engineer position in San Francisco.
        Candidates on H-1B, STEM OPT, or TN status are welcome to apply.
        Please provide details of your current employment authorization.
      `;

      const result = scanVisaAndWorkAuthorization(desc);
      expect(result.hasRestriction).toBe(true);
      expect(result.namedVisaTypes).toContain('H-1B Visa');
      expect(result.namedVisaTypes).toContain('OPT/CPT Authorization');
      expect(result.namedVisaTypes).toContain('TN Visa');
    });

    it('asserts zero hallucinated restrictions on clean English posting', () => {
      const cleanDesc = `
        We are looking for a Senior React Developer to join our remote-first team.
        You will build modern user interfaces with TypeScript, Next.js, and Tailwind CSS.
        Flexible hours, generous PTO, and continuous learning stipend provided.
        Apply today to shape the future of our product!
      `;

      const result = scanVisaAndWorkAuthorization(cleanDesc);
      expect(result.hasRestriction).toBe(false);
      expect(result.restrictions).toHaveLength(0);
      expect(result.triggerSentences).toHaveLength(0);
      expect(result.namedVisaTypes).toHaveLength(0);
      expect(result.summaryText).toBe('No restriction language detected.');
    });
  });

  describe('French Postings', () => {
    it('detects French citizenship, carte de séjour, habilitation défense, and no sponsorship', () => {
      const frenchDesc = `
        Nous recherchons un(e) Consultant(e) Cybersécurité pour intervenir auprès de ministères.
        Nationalité française requise pour cette mission régalienne.
        Habilitation défense nécessaire avant le début de la mission.
        Titre de séjour valide ou carte de séjour salarié exigé.
        Pas de parrainage de visa possible pour ce poste.
      `;

      const result = scanVisaAndWorkAuthorization(frenchDesc);
      expect(result.hasRestriction).toBe(true);
      expect(result.triggerSentences.some((s) => s.includes('Nationalité française requise'))).toBe(true);
      expect(result.triggerSentences.some((s) => s.includes('Habilitation défense'))).toBe(true);
      expect(result.triggerSentences.some((s) => s.includes('Titre de séjour'))).toBe(true);
      expect(result.triggerSentences.some((s) => s.includes('Pas de parrainage de visa'))).toBe(true);

      const labels = result.restrictions.map((r) => r.label);
      expect(labels).toContain('Nationalité française requise');
      expect(labels).toContain('Habilitation défense requise');
      expect(labels).toContain('Carte de séjour salarié requise');
      expect(labels).toContain('Aucun parrainage de visa');
    });

    it('detects French Passeport Talent and Carte bleue européenne', () => {
      const desc = `
        Entreprise en pleine expansion à Paris.
        Poste éligible au passeport talent et à la carte bleue européenne.
      `;

      const result = scanVisaAndWorkAuthorization(desc);
      expect(result.hasRestriction).toBe(true);
      expect(result.namedVisaTypes).toContain('Passeport Talent');
      expect(result.namedVisaTypes).toContain('Carte bleue européenne');
    });

    it('asserts zero hallucinated restrictions on clean French posting', () => {
      const cleanFrenchDesc = `
        Tech Innovations Paris recherche un Développeur Full Stack H/F en CDI.
        Vous participerez au développement de notre application web en React et Python.
        Poste basé à Paris avec deux jours de télétravail par semaine.
        Tickets restaurant, mutuelle d'entreprise prise en charge à 100%.
      `;

      const result = scanVisaAndWorkAuthorization(cleanFrenchDesc);
      expect(result.hasRestriction).toBe(false);
      expect(result.restrictions).toHaveLength(0);
      expect(result.triggerSentences).toHaveLength(0);
      expect(result.summaryText).toBe('No restriction language detected.');
    });
  });

  describe('German Postings', () => {
    it('detects German citizenship, Arbeitserlaubnis, and no visa sponsoring', () => {
      const germanDesc = `
        Wir suchen einen IT-Sicherheitsspezialisten für Behördenprojekte in Berlin.
        Deutsche Staatsbürgerschaft erforderlich aufgrund behördlicher Vorgaben.
        Gültige Arbeitserlaubnis für Deutschland erforderlich.
        Kein Visasponsoring für diese Position möglich.
        Attraktives Gehalt und flexible Arbeitszeiten.
      `;

      const result = scanVisaAndWorkAuthorization(germanDesc);
      expect(result.hasRestriction).toBe(true);
      expect(result.triggerSentences.some((s) => s.includes('Deutsche Staatsbürgerschaft'))).toBe(true);
      expect(result.triggerSentences.some((s) => s.includes('Gültige Arbeitserlaubnis'))).toBe(true);
      expect(result.triggerSentences.some((s) => s.includes('Kein Visasponsoring'))).toBe(true);

      const labels = result.restrictions.map((r) => r.label);
      expect(labels).toContain('Deutsche Staatsbürgerschaft erforderlich');
      expect(labels).toContain('Arbeitserlaubnis für Deutschland erforderlich');
      expect(labels).toContain('Kein Visumsponsoring');
    });

    it('asserts zero hallucinated restrictions on clean German posting', () => {
      const cleanGermanDesc = `
        Wir suchen einen Frontend-Entwickler (m/w/d) für unser Team in München.
        Zu Ihren Aufgaben gehört die Entwicklung moderner Webanwendungen mit Vue.js.
        Wir bieten Ihnen 30 Tage Urlaub, ein modernes Büro und regelmäßige Teamevents.
      `;

      const result = scanVisaAndWorkAuthorization(cleanGermanDesc);
      expect(result.hasRestriction).toBe(false);
      expect(result.restrictions).toHaveLength(0);
      expect(result.triggerSentences).toHaveLength(0);
      expect(result.summaryText).toBe('No restriction language detected.');
    });
  });

  describe('User Profile Alignment Check', () => {
    it('handles unspecified user profile work authorization without guessing', () => {
      const desc = 'Must be a US Citizen required for defense contracts.';
      const result = scanVisaAndWorkAuthorization(desc, null);

      expect(result.profileCheck?.profileHasAuthInfo).toBe(false);
      expect(result.profileCheck?.status).toBe('unspecified');
      expect(result.profileCheck?.message).toContain('User profile does not specify work authorization');
    });

    it('flags potential incompatibility when posting requires citizenship but profile specifies visa', () => {
      const desc = 'US Citizenship required for this defense role.';
      const result = scanVisaAndWorkAuthorization(desc, {
        nationality: 'France',
        work_authorization: 'H-1B Visa',
      });

      expect(result.profileCheck?.profileHasAuthInfo).toBe(true);
      expect(result.profileCheck?.status).toBe('potential_incompatibility');
      expect(result.profileCheck?.message).toContain('requires citizenship');
    });

    it('confirms compatibility when profile authorization satisfies criteria', () => {
      const desc = 'No visa sponsorship provided. Candidates must be authorized to work.';
      const result = scanVisaAndWorkAuthorization(desc, {
        nationality: 'United States',
        work_authorization: 'US Citizen',
      });

      expect(result.profileCheck?.profileHasAuthInfo).toBe(true);
      expect(result.profileCheck?.status).toBe('compatible');
    });
  });
});
