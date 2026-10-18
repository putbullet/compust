; ==============================================================================
; Compust — Modern Windows Installer Script (Inno Setup 6)
; Single-file, self-healing, non-admin per-user installer
; Multi-language: English, French, Dutch
; ==============================================================================

#ifndef AppVersion
  #define AppVersion "1.0.3"
#endif

#ifndef StagingDir
  #define StagingDir "..\release\staging"
#endif

#ifndef OutputDir
  #define OutputDir "..\release"
#endif

[Setup]
AppId={{C08A91F2-927A-4D71-B8AE-362E6941865F}}
AppName=Compust
AppVersion={#AppVersion}
AppVerName=Compust v{#AppVersion}
AppPublisher=Compust Community
AppPublisherURL=https://github.com/putbullet/compust
AppSupportURL=https://github.com/putbullet/compust/issues
AppUpdatesURL=https://github.com/putbullet/compust/releases
DefaultDirName={localappdata}\Programs\Compust
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=Compust-Setup-v{#AppVersion}
OutputDir={#OutputDir}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\launcher\compust.ico
UninstallDisplayIcon={app}\launcher\compust.ico
CloseApplications=force
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "nl"; MessagesFile: "compiler:Languages\Dutch.isl"

[CustomMessages]
en.WelcomeTitle=Welcome to Compust
en.WelcomeSub=The private, local-first career intelligence, resume tailoring, and interview platform.
en.CompustCore=Compust Core Platform (FastAPI engine, pre-built React SPA, local database)
en.VoicePack=Voice & Interview Pack (Local speech-to-text & neural audio preview)
en.AdditionalIcons=Shortcuts and Startup:
en.CreateDesktopIcon=Create a Desktop shortcut
en.CreateStartMenu=Create Start Menu shortcuts
en.RunAtStartup=Start Compust automatically when Windows starts
en.OllamaPageTitle=AI Engine Setup (Ollama)
en.OllamaPageSubTitle=Private on-device AI for resume tailoring and mock interview simulation
en.OllamaIntro=Compust uses Ollama to run local language models (default: qwen3.5:0.8b) 100% privately without API keys or cloud fees.
en.OllamaAlreadyInstalled=Ollama is already installed and detected on your computer.
en.OllamaOptInstall=(Recommended) Download and install Ollama for me automatically
en.OllamaOptManual=Show manual setup instructions (ollama pull qwen3.5:0.8b)
en.OllamaOptSkip=Skip for now (core features work immediately; AI features can be enabled anytime)
en.UninstallKeepData=Do you want to KEEP your personal data (database, saved resumes, and logs)?%n%nClick 'Yes' to preserve your data in case you reinstall later.%nClick 'No' to permanently delete your data.
en.LaunchCompust=Launch Compust now
en.ViewQuickStart=Open Quick-Start Guide in browser
en.CheckAndRepair=Compust – Check & Repair

fr.WelcomeTitle=Bienvenue sur Compust
fr.WelcomeSub=Plateforme locale et confidentielle d'intelligence de carriere, CV et preparation d'entretiens.
fr.CompustCore=Plateforme centrale Compust (FastAPI, React SPA, base de donnees locale)
fr.VoicePack=Module vocal & entretiens (Reconnaissance vocale locale & synthese vocale)
fr.AdditionalIcons=Raccourcis et demarrage :
fr.CreateDesktopIcon=Creer un raccourci sur le Bureau
fr.CreateStartMenu=Creer des raccourcis dans le Menu Demarrer
fr.RunAtStartup=Demarrer Compust automatiquement au lancement de Windows
fr.OllamaPageTitle=Configuration du moteur IA (Ollama)
fr.OllamaPageSubTitle=IA locale privee pour l'adaptation de CV et simulation d'entretiens
fr.OllamaIntro=Compust utilise Ollama pour executer des modeles IA legers (defaut : qwen3.5:0.8b) de maniere 100%% privee, sans cle API.
fr.OllamaAlreadyInstalled=Ollama est deja installe et operationnel sur votre ordinateur.
fr.OllamaOptInstall=(Recommande) Telecharger et installer Ollama automatiquement
fr.OllamaOptManual=Afficher les instructions manuelles (ollama pull qwen3.5:0.8b)
fr.OllamaOptSkip=Ignorer pour le moment (les fonctions cles fonctionnent hors ligne)
fr.UninstallKeepData=Souhaitez-vous CONSERVER vos donnees personnelles (base de donnees, CV, historiques) ?%n%nCliquez sur 'Oui' pour conserver vos donnees.%nCliquez sur 'Non' pour tout supprimer.
fr.LaunchCompust=Lancer Compust maintenant
fr.ViewQuickStart=Ouvrir le guide de demarrage rapide
fr.CheckAndRepair=Compust – Verifier & Reparer

nl.WelcomeTitle=Welkom bij Compust
nl.WelcomeSub=Het lokale carriere-intelligentie, cv-optimalisatie en interviewplatform.
nl.CompustCore=Compust kernplatform (FastAPI, React SPA, lokale database)
nl.VoicePack=Spraak- & interviewpakket (Lokale spraakherkenning & synthese)
nl.AdditionalIcons=Snelkoppelingen en opstarten:
nl.CreateDesktopIcon=Maak een snelkoppeling op het bureaublad
nl.CreateStartMenu=Maak snelkoppelingen in het Startmenu
nl.RunAtStartup=Start Compust automatisch wanneer Windows start
nl.OllamaPageTitle=AI-engine configuratie (Ollama)
nl.OllamaPageSubTitle=Prive lokale AI voor cv-aanpassing en interviews
nl.OllamaIntro=Compust gebruikt Ollama voor lokale AI-modellen (standaard: qwen3.5:0.8b) 100%% prive zonder API-sleutels.
nl.OllamaAlreadyInstalled=Ollama is al geinstalleerd op uw computer.
nl.OllamaOptInstall=(Aanbevolen) Download en installeer Ollama automatisch
nl.OllamaOptManual=Toon handmatige instructies (ollama pull qwen3.5:0.8b)
nl.OllamaOptSkip=Nu overslaan (basisfuncties werken altijd)
nl.UninstallKeepData=Wilt u uw persoonlijke gegevens BEWAREN (database, cv's en logbestanden)?%n%nKlik op 'Ja' om gegevens te behouden.%nKlik op 'Nee' om alles te verwijderen.
nl.LaunchCompust=Start Compust nu
nl.ViewQuickStart=Open de beknopte handleiding
nl.CheckAndRepair=Compust – Controleren & Repareren

[Components]
Name: "core"; Description: "{cm:CompustCore}"; Types: full compact custom; Flags: fixed
Name: "voice"; Description: "{cm:VoicePack}"; Types: full

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startmenu"; Description: "{cm:CreateStartMenu}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startup"; Description: "{cm:RunAtStartup}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#StagingDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\Compust"; Filename: "{app}\Compust.exe"; IconFilename: "{app}\launcher\compust.ico"; Tasks: desktopicon
Name: "{userprograms}\Compust\Compust"; Filename: "{app}\Compust.exe"; IconFilename: "{app}\launcher\compust.ico"; Tasks: startmenu
Name: "{userprograms}\Compust\{cm:CheckAndRepair}"; Filename: "{app}\Compust.exe"; Parameters: "--repair"; IconFilename: "{app}\launcher\compust.ico"; Tasks: startmenu
Name: "{userprograms}\Compust\Uninstall Compust"; Filename: "{uninstallexe}"; Tasks: startmenu
Name: "{userstartup}\Compust"; Filename: "{app}\Compust.exe"; Tasks: startup

[Run]
Filename: "{app}\Compust.exe"; Description: "{cm:LaunchCompust}"; Flags: nowait postinstall skipifsilent
Filename: "https://github.com/putbullet/compust#quick-start"; Description: "{cm:ViewQuickStart}"; Flags: shellexec postinstall skipifsilent unchecked

[Code]
var
  OllamaPage: TWizardPage;
  OllamaInstalled: Boolean;
  OptInstallOllama: TRadioButton;
  OptManualOllama: TRadioButton;
  OptSkipOllama: TRadioButton;
  OllamaStatusLabel: TLabel;

function IsOllamaRunningOrInstalled(): Boolean;
var
  OllamaExePath: String;
begin
  OllamaExePath := ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe');
  if FileExists(OllamaExePath) then
  begin
    Result := True;
    Exit;
  end;
  Result := False;
end;

procedure InitializeWizard();
var
  IntroLabel: TLabel;
begin
  OllamaInstalled := IsOllamaRunningOrInstalled();

  // Create Custom Ollama Setup Wizard Page
  OllamaPage := CreateCustomPage(
    wpSelectTasks,
    CustomMessage('OllamaPageTitle'),
    CustomMessage('OllamaPageSubTitle')
  );

  IntroLabel := TLabel.Create(OllamaPage);
  IntroLabel.Parent := OllamaPage.Surface;
  IntroLabel.Left := 0;
  IntroLabel.Top := 10;
  IntroLabel.Width := OllamaPage.SurfaceWidth;
  IntroLabel.WordWrap := True;
  IntroLabel.Caption := CustomMessage('OllamaIntro');

  OllamaStatusLabel := TLabel.Create(OllamaPage);
  OllamaStatusLabel.Parent := OllamaPage.Surface;
  OllamaStatusLabel.Left := 0;
  OllamaStatusLabel.Top := 70;
  OllamaStatusLabel.Width := OllamaPage.SurfaceWidth;
  OllamaStatusLabel.Font.Style := [fsBold];

  if OllamaInstalled then
  begin
    OllamaStatusLabel.Font.Color := clGreen;
    OllamaStatusLabel.Caption := CustomMessage('OllamaAlreadyInstalled');
  end
  else
  begin
    OllamaStatusLabel.Font.Color := clWindowText;
    OllamaStatusLabel.Caption := 'Ollama is not yet detected on this system.';

    OptInstallOllama := TRadioButton.Create(OllamaPage);
    OptInstallOllama.Parent := OllamaPage.Surface;
    OptInstallOllama.Left := 10;
    OptInstallOllama.Top := 105;
    OptInstallOllama.Width := OllamaPage.SurfaceWidth - 20;
    OptInstallOllama.Caption := CustomMessage('OllamaOptInstall');
    OptInstallOllama.Checked := True;

    OptManualOllama := TRadioButton.Create(OllamaPage);
    OptManualOllama.Parent := OllamaPage.Surface;
    OptManualOllama.Left := 10;
    OptManualOllama.Top := 140;
    OptManualOllama.Width := OllamaPage.SurfaceWidth - 20;
    OptManualOllama.Caption := CustomMessage('OllamaOptManual');

    OptSkipOllama := TRadioButton.Create(OllamaPage);
    OptSkipOllama.Parent := OllamaPage.Surface;
    OptSkipOllama.Left := 10;
    OptSkipOllama.Top := 175;
    OptSkipOllama.Width := OllamaPage.SurfaceWidth - 20;
    OptSkipOllama.Caption := CustomMessage('OllamaOptSkip');
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  MarkerPath: String;
  InstallerUrl, TmpInstaller: String;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Write install completion marker for idempotency & self-healing verification
    MarkerPath := ExpandConstant('{app}\.install_complete');
    SaveStringToFile(MarkerPath, 'version=' + ExpandConstant('{#AppVersion}') + #13#10 + 'status=installed' + #13#10, False);

    // If user opted to install Ollama automatically (interactive wizard only)
    if (not WizardSilent()) and (not OllamaInstalled) and (OptInstallOllama <> nil) and (OptInstallOllama.Checked) then
    begin
      InstallerUrl := 'https://ollama.com/download/OllamaSetup.exe';
      TmpInstaller := ExpandConstant('{tmp}\OllamaSetup.exe');
      
      // Use PowerShell to securely download and run official Ollama installer
      Exec('powershell.exe', '-NoProfile -Command "try { Invoke-WebRequest -Uri ''' + InstallerUrl + ''' -OutFile ''' + TmpInstaller + ''' -UseBasicParsing; Start-Process ''' + TmpInstaller + ''' -ArgumentList ''/silent'' -Wait } catch {}"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
  KeepData: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\Compust');
    if DirExists(DataDir) and (not UninstallSilent()) then
    begin
      KeepData := MsgBox(CustomMessage('UninstallKeepData'), mbConfirmation, MB_YESNO or MB_DEFBUTTON1);
      if KeepData = IDNO then
      begin
        DelTree(DataDir, True, True, True);
      end;
    end;
  end;
end;
