import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import {
  Download,
  Copy,
  Check,
  Globe,
  Compass,
  Layers,
  ShieldCheck,
  ExternalLink,
  HelpCircle,
  Zap,
} from 'lucide-react';
import { useTranslation } from '../i18n';
import { API_BASE_URL } from '../api/client';

type DetectedBrowser = 'chrome' | 'edge' | 'brave' | 'firefox' | 'other';

export const ExtensionInstallView: React.FC = () => {
  const { language } = useTranslation();
  const [detectedBrowser, setDetectedBrowser] = useState<DetectedBrowser>('chrome');
  const [selectedBrowser, setSelectedBrowser] = useState<DetectedBrowser>('chrome');
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);
  const [isExtensionDetected, setIsExtensionDetected] = useState<boolean | null>(null);

  useEffect(() => {
    const ua = navigator.userAgent.toLowerCase();
    let detected: DetectedBrowser = 'other';

    if (ua.includes('edg/')) {
      detected = 'edge';
    } else if ((navigator as any).brave && typeof (navigator as any).brave.isBrave === 'function') {
      detected = 'brave';
    } else if (ua.includes('firefox') || ua.includes('fxios')) {
      detected = 'firefox';
    } else if (ua.includes('chrome') || ua.includes('chromium')) {
      detected = 'chrome';
    }

    setDetectedBrowser(detected);
    setSelectedBrowser(detected === 'other' ? 'chrome' : detected);

    // Light check for extension marker
    const checkExtension = () => {
      const hasMarker = Boolean(
        document.querySelector('[data-compust-extension-installed]') ||
        (window as any).__COMPUST_CAPTURE_INSTALLED__
      );
      setIsExtensionDetected(hasMarker);
    };
    checkExtension();
    const interval = setInterval(checkExtension, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedUrl(text);
    setTimeout(() => setCopiedUrl(null), 2500);
  };

  const getInternalUrl = (browser: DetectedBrowser) => {
    switch (browser) {
      case 'edge':
        return 'edge://extensions';
      case 'brave':
      case 'chrome':
      case 'other':
        return 'chrome://extensions';
      case 'firefox':
        return 'about:debugging#/runtime/this-firefox';
    }
  };

  const getDownloadUrl = (browser: DetectedBrowser) => {
    const target = browser === 'firefox' ? 'firefox' : 'chrome';
    return `${API_BASE_URL}/extension/download/${target}`;
  };

  const internalUrl = getInternalUrl(selectedBrowser);
  const isChromium = ['chrome', 'edge', 'brave', 'other'].includes(selectedBrowser);

  const tTxt = (en: string, fr: string, nl: string) => {
    if (language === 'fr') return fr;
    if (language === 'nl') return nl;
    return en;
  };

  return (
    <Container>
      <HeaderSection>
        <div className="badge">
          <Zap size={14} />
          <span>Compust Capture Browser Extension</span>
        </div>
        <h1>
          {tTxt(
            'Install Compust Capture Browser Extension',
            'Installez l’extension pour capturer vos offres',
            'Installeer de Compust Capture Browserextensie'
          )}
        </h1>
        <p className="subtitle">
          {tTxt(
            'Capture job listings directly from LinkedIn, Indeed, Glassdoor, and Welcome to the Jungle with instant resume match scoring.',
            'Capturez en un clic les offres d’emploi depuis LinkedIn, Indeed, Glassdoor et Welcome to the Jungle avec analyse instantanée de vos compétences.',
            'Verzamel vacatures rechtstreeks van LinkedIn, Indeed, Glassdoor en Welcome to the Jungle met directe matchscores voor je cv.'
          )}
        </p>

        {isExtensionDetected ? (
          <StatusBanner className="detected">
            <ShieldCheck size={18} />
            <span>
              {tTxt(
                'Compust Capture extension detected and active in your browser!',
                'Extension Compust Capture détectée et active dans votre navigateur !',
                'Compust Capture-extensie gedetecteerd en actief in uw browser!'
              )}
            </span>
          </StatusBanner>
        ) : (
          <StatusBanner className="neutral">
            <HelpCircle size={18} />
            <span>
              {tTxt(
                'Local Developer-Mode installation required (portable standalone offline architecture).',
                'Installation locale en mode Développeur requise (non disponible sur le Web Store public).',
                'Lokale installatie in ontwikkelaarsmodus vereist (veilige zelfstandige offline architectuur).'
              )}
            </span>
          </StatusBanner>
        )}
      </HeaderSection>

      {/* Browser Selector Tabs */}
      <BrowserTabs>
        <TabButton
          active={selectedBrowser === 'chrome'}
          onClick={() => setSelectedBrowser('chrome')}
        >
          <Globe size={18} />
          <span>Google Chrome</span>
          {detectedBrowser === 'chrome' && <span className="current-pill">Current</span>}
        </TabButton>
        <TabButton
          active={selectedBrowser === 'edge'}
          onClick={() => setSelectedBrowser('edge')}
        >
          <Compass size={18} />
          <span>Microsoft Edge</span>
          {detectedBrowser === 'edge' && <span className="current-pill">Current</span>}
        </TabButton>
        <TabButton
          active={selectedBrowser === 'brave'}
          onClick={() => setSelectedBrowser('brave')}
        >
          <Layers size={18} />
          <span>Brave</span>
          {detectedBrowser === 'brave' && <span className="current-pill">Current</span>}
        </TabButton>
        <TabButton
          active={selectedBrowser === 'firefox'}
          onClick={() => setSelectedBrowser('firefox')}
        >
          <ExternalLink size={18} />
          <span>Mozilla Firefox</span>
          {detectedBrowser === 'firefox' && <span className="current-pill">Current</span>}
        </TabButton>
      </BrowserTabs>

      {/* Main Instructions Card */}
      <InstructionsCard>
        <div className="card-top">
          <div className="browser-info">
            <h2>
              {tTxt(
                `Installation Guide for ${selectedBrowser === 'chrome' ? 'Google Chrome' : selectedBrowser === 'edge' ? 'Microsoft Edge' : selectedBrowser === 'brave' ? 'Brave' : 'Mozilla Firefox'}`,
                `Instructions d’installation pour ${selectedBrowser.toUpperCase()}`,
                `Installatiehandleiding voor ${selectedBrowser === 'chrome' ? 'Google Chrome' : selectedBrowser === 'edge' ? 'Microsoft Edge' : selectedBrowser === 'brave' ? 'Brave' : 'Mozilla Firefox'}`
              )}
            </h2>
            <p className="security-notice">
              {tTxt(
                'Security Note: Browser sandboxing prohibits web applications from silently auto-installing or directly linking to internal protocol URLs (chrome:// or about:). Follow the quick steps below to load unpacked.',
                'Note de sécurité : En raison des politiques de sécurité strictes des navigateurs, une page web ne peut pas ouvrir automatiquement les pages internes (chrome:// ou about:). Les étapes ci-dessous prennent moins de 60 secondes.',
                'Beveiligingsopmerking: Browsers isoleren webapplicaties en verhinderen automatische installatie of directe links naar interne protocol-URL\'s (chrome:// of about:). Volg de onderstaande stappen.'
              )}
            </p>
          </div>

          <a
            href={getDownloadUrl(selectedBrowser)}
            className="download-btn"
            download
          >
            <Download size={18} />
            <span>
              {tTxt(
                `Download ${selectedBrowser === 'firefox' ? 'Firefox' : 'Chromium'} ZIP`,
                `Télécharger le package (.ZIP)`,
                `Download ${selectedBrowser === 'firefox' ? 'Firefox' : 'Chromium'} ZIP`
              )}
            </span>
          </a>
        </div>

        {/* Step-by-Step */}
        <StepsList>
          <StepItem>
            <div className="step-num">1</div>
            <div className="step-content">
              <h4>
                {tTxt(
                  'Download & Extract the Extension Package',
                  'Téléchargez et décompressez l’archive',
                  'Download en pak het extensiepakket uit'
                )}
              </h4>
              <p>
                {tTxt(
                  'Click the download button above and extract the zip archive into a permanent directory on your machine (e.g., inside your Documents or Compust directory).',
                  'Cliquez sur le bouton de téléchargement ci-dessus, puis extrayez le fichier ZIP dans un dossier permanent sur votre ordinateur (par exemple dans Documents ou le dossier Compust).',
                  'Klik op de bovenstaande downloadknop en pak het zip-archief uit in een vaste map op uw computer (bijv. in Documenten of uw Compust-map).'
                )}
              </p>
            </div>
          </StepItem>

          <StepItem>
            <div className="step-num">2</div>
            <div className="step-content">
              <h4>
                {tTxt(
                  `Open ${selectedBrowser.toUpperCase()} Extension Manager`,
                  `Ouvrez la page de gestion des extensions de ${selectedBrowser}`,
                  `Open ${selectedBrowser.toUpperCase()} Extensiebeheer`
                )}
              </h4>
              <p>
                {tTxt(
                  'Copy the following address and paste it into the URL bar of a new browser tab:',
                  'Copiez l’adresse suivante et collez-la dans la barre d’adresse d’un nouvel onglet :',
                  'Kopieer het volgende adres en plak het in de adresbalk van een nieuw tabblad:'
                )}
              </p>
              <CopyBox>
                <code>{internalUrl}</code>
                <button
                  type="button"
                  className="copy-btn"
                  onClick={() => handleCopy(internalUrl)}
                  title="Copy to clipboard"
                >
                  {copiedUrl === internalUrl ? <Check size={16} color="#10b981" /> : <Copy size={16} />}
                  <span>{copiedUrl === internalUrl ? 'Copied!' : 'Copy URL'}</span>
                </button>
              </CopyBox>
            </div>
          </StepItem>

          {isChromium ? (
            <>
              <StepItem>
                <div className="step-num">3</div>
                <div className="step-content">
                  <h4>
                    {tTxt(
                      'Enable "Developer Mode"',
                      'Activez le "Mode développeur"',
                      'Schakel "Ontwikkelaarsmodus" in'
                    )}
                  </h4>
                  <p>
                    {tTxt(
                      'In the top-right corner of the Extensions page, toggle the "Developer mode" switch to ON.',
                      'Dans le coin supérieur droit de la page des extensions, activez le bouton bascule "Mode développeur".',
                      'Schakel in de rechterbovenhoek van de pagina Extensies de schakelaar "Ontwikkelaarsmodus" in.'
                    )}
                  </p>
                </div>
              </StepItem>

              <StepItem>
                <div className="step-num">4</div>
                <div className="step-content">
                  <h4>
                    {tTxt(
                      'Click "Load unpacked" & Select Extracted Folder',
                      'Chargez le dossier décompressé',
                      'Klik op "Uitgepakte extensie laden" en selecteer de map'
                    )}
                  </h4>
                  <p>
                    {tTxt(
                      'Click the "Load unpacked" button in the top left, and select the folder you extracted in Step 1.',
                      'Cliquez sur le bouton "Charger l\'extension non empaquetée" en haut à gauche, puis sélectionnez le dossier extrait à l\'étape 1.',
                      'Klik linksboven op de knop "Uitgepakte extensie laden" en kies de map die u in stap 1 heeft uitgepakt.'
                    )}
                  </p>
                </div>
              </StepItem>
            </>
          ) : (
            <>
              <StepItem>
                <div className="step-num">3</div>
                <div className="step-content">
                  <h4>
                    {tTxt(
                      'Click "Load Temporary Add-on..."',
                      'Chargez le module temporaire',
                      'Klik op "Tijdelijke add-on laden..."'
                    )}
                  </h4>
                  <p>
                    {tTxt(
                      'In the "This Firefox" section, click the "Load Temporary Add-on..." button.',
                      'Dans la section "Ce Firefox" (This Firefox), cliquez sur le bouton "Charger un module temporaire...".',
                      'Klik in het gedeelte "Deze Firefox" op de knop "Tijdelijke add-on laden...".'
                    )}
                  </p>
                </div>
              </StepItem>

              <StepItem>
                <div className="step-num">4</div>
                <div className="step-content">
                  <h4>
                    {tTxt(
                      'Select manifest.json inside Extracted Folder',
                      'Sélectionnez manifest.json',
                      'Selecteer manifest.json in de uitgepakte map'
                    )}
                  </h4>
                  <p>
                    {tTxt(
                      'Navigate into your extracted Firefox extension directory and select the manifest.json file.',
                      'Dans la boîte de dialogue de sélection de fichier, naviguez dans le dossier extrait et choisissez le fichier manifest.json.',
                      'Navigeer naar uw uitgepakte Firefox-extensiemap en kies het bestand manifest.json.'
                    )}
                  </p>
                </div>
              </StepItem>
            </>
          )}

          <StepItem>
            <div className="step-num">5</div>
            <div className="step-content">
              <h4>
                {tTxt(
                  'Ready to Analyse! Open Any Job Page',
                  'Prêt ! Rendez-vous sur vos offres préférées',
                  'Klaar voor analyse! Open een vacaturepagina'
                )}
              </h4>
              <p>
                {tTxt(
                  'Open any job posting on LinkedIn, Indeed, Glassdoor, or Welcome to the Jungle. The floating "Analyse with Compust" button will appear automatically on the bottom-right to run real-time resume match and visa analysis, with explicit options to track as Interested or Applied in your Applications Kanban board.',
                  'Naviguez sur une offre d’emploi sur LinkedIn, Indeed, Glassdoor ou Welcome to the Jungle. Le bouton flottant "Analyse with Compust" apparaîtra automatiquement en bas à droite pour analyser la correspondance avec votre CV en temps réel, avant de choisir explicitement de suivre votre candidature.',
                  'Open een vacature op LinkedIn, Indeed, Glassdoor of Welcome to the Jungle. De zwevende knop "Analyse with Compust" verschijnt automatisch rechtsonder voor realtime cv-matching en visumanalyse.'
                )}
              </p>
            </div>
          </StepItem>
        </StepsList>
      </InstructionsCard>

      {/* Supported Platforms Grid */}
      <PlatformsGrid>
        <PlatformCard>
          <div className="platform-title">LinkedIn Jobs</div>
          <p>Full support for direct job URLs (/jobs/view/...) and split-pane search pages with live currentJobId sync.</p>
        </PlatformCard>
        <PlatformCard>
          <div className="platform-title">Indeed</div>
          <p>Full support for /viewjob and /jobs search layouts with comprehensive salary, company, and JD extraction.</p>
        </PlatformCard>
        <PlatformCard>
          <div className="platform-title">Glassdoor</div>
          <p>Full support for job listings and expand-description triggers for robust complete job text extraction.</p>
        </PlatformCard>
        <PlatformCard>
          <div className="platform-title">Welcome to the Jungle</div>
          <p>Full support for multi-language French & European tech listings with deep section parsing.</p>
        </PlatformCard>
      </PlatformsGrid>
    </Container>
  );
};

// --- STYLED COMPONENTS ---

const Container = styled.div`
  max-width: 1000px;
  margin: 0 auto;
  padding: 32px 20px 80px 20px;
  color: #f1f5f9;
`;

const HeaderSection = styled.div`
  text-align: center;
  margin-bottom: 32px;

  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(99, 102, 241, 0.12);
    color: #818cf8;
    border: 1px solid rgba(99, 102, 241, 0.25);
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 12px;
  }

  h1 {
    font-size: 2.2rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #f8fafc;
    margin-bottom: 10px;
  }

  .subtitle {
    font-size: 1.05rem;
    color: #94a3b8;
    max-width: 680px;
    margin: 0 auto 20px auto;
    line-height: 1.5;
  }
`;

const StatusBanner = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;

  &.detected {
    background: rgba(16, 185, 129, 0.12);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.25);
  }

  &.neutral {
    background: rgba(148, 163, 184, 0.08);
    color: #cbd5e1;
    border: 1px solid rgba(148, 163, 184, 0.18);
  }
`;

const BrowserTabs = styled.div`
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
`;

const TabButton = styled.button<{ active: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: 12px;
  font-size: 0.92rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid ${(props) => (props.active ? '#6366f1' : 'rgba(255, 255, 255, 0.08)')};
  background: ${(props) => (props.active ? 'rgba(99, 102, 241, 0.18)' : 'rgba(30, 41, 59, 0.6)')};
  color: ${(props) => (props.active ? '#ffffff' : '#94a3b8')};

  &:hover {
    background: rgba(99, 102, 241, 0.12);
    color: #f8fafc;
  }

  .current-pill {
    font-size: 0.7rem;
    background: #6366f1;
    color: white;
    padding: 2px 6px;
    border-radius: 6px;
    text-transform: uppercase;
    font-weight: 700;
  }
`;

const InstructionsCard = styled.div`
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(12px);

  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 24px;
    padding-bottom: 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    margin-bottom: 28px;
    flex-wrap: wrap;
  }

  .browser-info h2 {
    font-size: 1.35rem;
    font-weight: 600;
    color: #f8fafc;
    margin-bottom: 6px;
  }

  .security-notice {
    font-size: 0.88rem;
    color: #94a3b8;
    max-width: 580px;
    line-height: 1.45;
  }

  .download-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    color: #ffffff;
    padding: 12px 22px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.95rem;
    text-decoration: none;
    transition: all 0.2s ease;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);

    &:hover {
      background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
      transform: translateY(-1px);
      box-shadow: 0 6px 18px rgba(99, 102, 241, 0.45);
    }
  }
`;

const StepsList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 24px;
`;

const StepItem = styled.div`
  display: flex;
  gap: 18px;
  align-items: flex-start;

  .step-num {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: rgba(99, 102, 241, 0.15);
    color: #818cf8;
    border: 1px solid rgba(99, 102, 241, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.95rem;
    flex-shrink: 0;
  }

  .step-content {
    flex: 1;

    h4 {
      font-size: 1.05rem;
      font-weight: 600;
      color: #f1f5f9;
      margin-bottom: 4px;
    }

    p {
      font-size: 0.9rem;
      color: #94a3b8;
      line-height: 1.5;
    }
  }
`;

const CopyBox = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 8px 12px;
  margin-top: 8px;
  max-width: 480px;

  code {
    font-family: 'Fira Code', monospace;
    font-size: 0.88rem;
    color: #38bdf8;
  }

  .copy-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.08);
    border: none;
    color: #f1f5f9;
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      background: rgba(255, 255, 255, 0.15);
    }
  }
`;

const PlatformsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-top: 32px;
`;

const PlatformCard = styled.div`
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 18px;

  .platform-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: #f8fafc;
    margin-bottom: 6px;
  }

  p {
    font-size: 0.82rem;
    color: #94a3b8;
    line-height: 1.4;
  }
`;
