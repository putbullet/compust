export interface VisaRestrictionItem {
  category: 'citizenship' | 'sponsorship' | 'visa_type' | 'clearance' | 'work_permit';
  label: string;
  language: 'en' | 'fr' | 'de';
  quotedSentence: string;
}

export interface UserProfileWorkAuth {
  nationality?: string | null;
  work_authorization?: string | null; // e.g. "US Citizen", "EU Citizen", "H-1B", "Carte de séjour", "Aufenthaltstitel"
}

export interface VisaAnalysisResult {
  hasRestriction: boolean;
  restrictions: VisaRestrictionItem[];
  triggerSentences: string[];
  namedVisaTypes: string[];
  summaryText: string;
  profileCheck?: {
    profileHasAuthInfo: boolean;
    status: 'compatible' | 'potential_incompatibility' | 'unspecified';
    message: string;
  };
}

interface PatternDef {
  regex: RegExp;
  category: 'citizenship' | 'sponsorship' | 'visa_type' | 'clearance' | 'work_permit';
  label: string;
  language: 'en' | 'fr' | 'de';
}

const MULTILINGUAL_PATTERNS: PatternDef[] = [
  // --- ENGLISH ---
  {
    regex: /\b(?:u\.?s\.?|united states)?\s*citizen(?:ship)?\s+(?:only|required|mandatory)\b/i,
    category: 'citizenship',
    label: 'US Citizenship Required',
    language: 'en',
  },
  {
    regex: /\bmust be a (?:u\.?s\.?|united states) citizen\b/i,
    category: 'citizenship',
    label: 'US Citizen Required',
    language: 'en',
  },
  {
    regex: /\b(?:active\s+)?security clearance (?:is\s+)?(?:required|mandatory|active)\b/i,
    category: 'clearance',
    label: 'Security Clearance Required',
    language: 'en',
  },
  {
    regex: /\b(?:no|not|cannot|unable to|will not|does not)\s+(?:provide\s+|offer\s+)?(?:visa\s+)?(?:sponsor(?:ship)?|sponsoring)\b/i,
    category: 'sponsorship',
    label: 'No Visa Sponsorship',
    language: 'en',
  },
  {
    regex: /\bwithout (?:requiring\s+)?(?:company\s+|visa\s+)?sponsorship\b/i,
    category: 'sponsorship',
    label: 'Must not require sponsorship',
    language: 'en',
  },
  {
    regex: /\bnot eligible for (?:visa\s+)?sponsorship\b/i,
    category: 'sponsorship',
    label: 'Ineligible for Visa Sponsorship',
    language: 'en',
  },
  {
    regex: /\bH-?1B\b/i,
    category: 'visa_type',
    label: 'H-1B Visa',
    language: 'en',
  },
  {
    regex: /\b(?:STEM\s+)?(?:OPT|CPT)\b/i,
    category: 'visa_type',
    label: 'OPT/CPT Authorization',
    language: 'en',
  },
  {
    regex: /\bTN (?:visa|status)\b/i,
    category: 'visa_type',
    label: 'TN Visa',
    language: 'en',
  },

  // --- FRENCH ---
  {
    regex: /\bnationalit[ée] fran[çc]aise (?:requise|obligatoire|exig[ée]e)\b/i,
    category: 'citizenship',
    label: 'Nationalité française requise',
    language: 'fr',
  },
  {
    regex: /\bhabilitation (?:d[ée]fense|confidentiel d[ée]fense|secret d[ée]fense)\b/i,
    category: 'clearance',
    label: 'Habilitation défense requise',
    language: 'fr',
  },
  {
    regex: /\b(?:titre|carte) de s[ée]jour (?:salari[ée]|valide|exig[ée]|requis)\b/i,
    category: 'work_permit',
    label: 'Carte de séjour salarié requise',
    language: 'fr',
  },
  {
    regex: /\b(?:disposer d'une?|avec) autorisation de travail (?:en france|valide)?\b/i,
    category: 'work_permit',
    label: 'Autorisation de travail en France requise',
    language: 'fr',
  },
  {
    regex: /\bcarte bleue europ[ée]enne\b/i,
    category: 'visa_type',
    label: 'Carte bleue européenne',
    language: 'fr',
  },
  {
    regex: /\bpasseport talent\b/i,
    category: 'visa_type',
    label: 'Passeport Talent',
    language: 'fr',
  },
  {
    regex: /\b(?:pas de|aucun) (?:parrainage|prise en charge|sponsoring) (?:de\s+)?visa\b/i,
    category: 'sponsorship',
    label: 'Aucun parrainage de visa',
    language: 'fr',
  },
  {
    regex: /\bne (?:peut|pourra) pas (?:fournir|financer|sponsoriser) (?:de\s+)?visa\b/i,
    category: 'sponsorship',
    label: 'Non éligible au parrainage de visa',
    language: 'fr',
  },

  // --- GERMAN ---
  {
    regex: /\bdeutsche(?:r)? staatsb[üu]rgerschaft (?:erforderlich|vorausgesetzt|zwingend)\b/i,
    category: 'citizenship',
    label: 'Deutsche Staatsbürgerschaft erforderlich',
    language: 'de',
  },
  {
    regex: /\barbeitserlaubnis (?:f[üu]r deutschland\s+)?(?:erforderlich|notwendig|vorausgesetzt|vorhanden)\b/i,
    category: 'work_permit',
    label: 'Arbeitserlaubnis für Deutschland erforderlich',
    language: 'de',
  },
  {
    regex: /\bg[üu]ltige(?:r)? aufenthaltstitel\b/i,
    category: 'work_permit',
    label: 'Gültiger Aufenthaltstitel erforderlich',
    language: 'de',
  },
  {
    regex: /\bblaue karte eu\b/i,
    category: 'visa_type',
    label: 'Blaue Karte EU',
    language: 'de',
  },
  {
    regex: /\bsicherheits[üu]berpr[üu]fung (?:erforderlich|notwendig|vorausgesetzt)\b/i,
    category: 'clearance',
    label: 'Sicherheitsüberprüfung erforderlich',
    language: 'de',
  },
  {
    regex: /\bkeine? (?:visasponsoring|visumsunterst[üu]tzung|visabeschaffung)\b/i,
    category: 'sponsorship',
    label: 'Kein Visumsponsoring',
    language: 'de',
  },
  {
    regex: /\bkann kein visum (?:sponsern|bereitstellen)\b/i,
    category: 'sponsorship',
    label: 'Kann kein Visum sponsern',
    language: 'de',
  },
];

export function splitIntoSentences(text: string): string[] {
  if (!text) return [];
  // Strip HTML tags for clean sentence boundary detection
  const clean = text.replace(/<[^>]*>/g, ' ');
  // Split on period, exclamation, question mark, newline, or bullet points
  const rawSentences = clean.split(/(?<=[.!?\n•\-])\s+/);
  return rawSentences
    .map((s) => s.trim().replace(/\s+/g, ' '))
    .filter((s) => s.length >= 10);
}

export function scanVisaAndWorkAuthorization(
  description: string | null | undefined,
  userProfile?: UserProfileWorkAuth | null
): VisaAnalysisResult {
  if (!description || description.trim().length === 0) {
    return {
      hasRestriction: false,
      restrictions: [],
      triggerSentences: [],
      namedVisaTypes: [],
      summaryText: 'No restriction language detected.',
    };
  }

  const sentences = splitIntoSentences(description);
  const detectedRestrictions: VisaRestrictionItem[] = [];
  const triggerSentencesSet = new Set<string>();
  const namedVisaTypesSet = new Set<string>();

  for (const sentence of sentences) {
    for (const pattern of MULTILINGUAL_PATTERNS) {
      if (pattern.regex.test(sentence)) {
        detectedRestrictions.push({
          category: pattern.category,
          label: pattern.label,
          language: pattern.language,
          quotedSentence: sentence,
        });
        triggerSentencesSet.add(sentence);

        if (pattern.category === 'visa_type') {
          namedVisaTypesSet.add(pattern.label);
        }
      }
    }
  }

  if (detectedRestrictions.length === 0) {
    return {
      hasRestriction: false,
      restrictions: [],
      triggerSentences: [],
      namedVisaTypes: [],
      summaryText: 'No restriction language detected.',
    };
  }

  const triggerSentences = Array.from(triggerSentencesSet);
  const namedVisaTypes = Array.from(namedVisaTypesSet);

  // Profile cross-reference logic
  let profileCheck: VisaAnalysisResult['profileCheck'];
  const userAuth = userProfile?.work_authorization?.trim() || userProfile?.nationality?.trim();

  if (!userAuth) {
    profileCheck = {
      profileHasAuthInfo: false,
      status: 'unspecified',
      message: 'User profile does not specify work authorization or nationality.',
    };
  } else {
    // Cross reference against restrictions
    const authLower = userAuth.toLowerCase();
    const hasCitizenReq = detectedRestrictions.some((r) => r.category === 'citizenship');
    const hasNoSponsorship = detectedRestrictions.some((r) => r.category === 'sponsorship');

    if (hasCitizenReq && !authLower.includes('citizen') && !authLower.includes('citoyen') && !authLower.includes('staatsbürger')) {
      profileCheck = {
        profileHasAuthInfo: true,
        status: 'potential_incompatibility',
        message: `Posting requires citizenship, but profile indicates: "${userAuth}".`,
      };
    } else if (hasNoSponsorship && (authLower.includes('h-1b') || authLower.includes('opt') || authLower.includes('requires sponsorship'))) {
      profileCheck = {
        profileHasAuthInfo: true,
        status: 'potential_incompatibility',
        message: `Posting does not provide visa sponsorship, but profile indicates: "${userAuth}".`,
      };
    } else {
      profileCheck = {
        profileHasAuthInfo: true,
        status: 'compatible',
        message: `Profile authorization ("${userAuth}") matches posting criteria.`,
      };
    }
  }

  const summary = `Detected ${detectedRestrictions.length} restriction(s): ${detectedRestrictions.map((r) => r.label).join(', ')}.`;

  return {
    hasRestriction: true,
    restrictions: detectedRestrictions,
    triggerSentences,
    namedVisaTypes,
    summaryText: summary,
    profileCheck,
  };
}
