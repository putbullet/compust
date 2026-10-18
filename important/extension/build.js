import { build } from 'vite';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const target = process.argv[2] || 'all';
const isFirefox = target === 'firefox';
const isChrome = target === 'chrome';
const isAll = target === 'all';

const pkg = JSON.parse(fs.readFileSync(resolve(__dirname, 'package.json'), 'utf-8'));
const version = pkg.version || '1.0.1';

// Helper to add files to AdmZip ensuring forward slashes on every platform
function addFolderToZipForwardSlashes(zip, folderPath, prefix = '') {
  const items = fs.readdirSync(folderPath, { withFileTypes: true });
  for (const item of items) {
    const fullPath = resolve(folderPath, item.name);
    const entryPath = prefix ? `${prefix}/${item.name}` : item.name;
    if (item.isDirectory()) {
      addFolderToZipForwardSlashes(zip, fullPath, entryPath);
    } else {
      const data = fs.readFileSync(fullPath);
      zip.addFile(entryPath, data);
    }
  }
}

async function buildTarget(currentTarget) {
  const isFx = currentTarget === 'firefox';
  const outDir = resolve(__dirname, isFx ? 'dist/firefox' : 'dist/chrome');
  console.log(`\nBuilding Compust Capture Extension for [${currentTarget}] -> ${outDir}`);

  // 1. Build Popup and Options HTML pages
  await build({
    configFile: false,
    root: __dirname,
    build: {
      outDir,
      emptyOutDir: true,
      rollupOptions: {
        input: {
          popup: resolve(__dirname, 'src/popup/index.html'),
          options: resolve(__dirname, 'src/options/index.html'),
        },
      },
    },
  });

  // 2. Build Background Script as self-contained IIFE
  await build({
    configFile: false,
    root: __dirname,
    build: {
      outDir,
      emptyOutDir: false,
      lib: {
        entry: resolve(__dirname, 'src/background/index.ts'),
        formats: ['iife'],
        name: 'CompustBackground',
        fileName: () => 'src/background/index.js',
      },
    },
  });

  // 3. Build Content Scripts as self-contained IIFE
  const contentScripts = ['linkedin', 'indeed', 'glassdoor', 'welcomeToTheJungle', 'generic'];
  for (const site of contentScripts) {
    await build({
      configFile: false,
      root: __dirname,
      build: {
        outDir,
        emptyOutDir: false,
        lib: {
          entry: resolve(__dirname, `src/content/${site}.ts`),
          formats: ['iife'],
          name: `Compust${site.charAt(0).toUpperCase() + site.slice(1)}`,
          fileName: () => `src/content/${site}.js`,
        },
      },
    });
  }

  // 4. Copy manifest
  const manifestSrc = isFx
    ? resolve(__dirname, 'manifest.firefox.json')
    : resolve(__dirname, 'manifest.chrome.json');
  fs.copyFileSync(manifestSrc, resolve(outDir, 'manifest.json'));
  console.log(`Copied ${manifestSrc} -> ${resolve(outDir, 'manifest.json')}`);

  // 5. Copy icons
  const iconsSrc = resolve(__dirname, 'src/assets/icons');
  const iconsDest = resolve(outDir, 'assets/icons');
  if (fs.existsSync(iconsSrc)) {
    fs.mkdirSync(iconsDest, { recursive: true });
    for (const icon of fs.readdirSync(iconsSrc)) {
      fs.copyFileSync(resolve(iconsSrc, icon), resolve(iconsDest, icon));
    }
    console.log(`Copied icons to ${iconsDest}`);
  }

  // 6. Create downloadable zip archive with forward-slash paths
  try {
    const AdmZip = (await import('adm-zip')).default;
    const zip = new AdmZip();
    addFolderToZipForwardSlashes(zip, outDir);

    const distDir = resolve(__dirname, 'dist');
    const zipFile = resolve(distDir, `compust-capture-${currentTarget}.zip`);
    const versionedZip = resolve(distDir, `compust-capture-${currentTarget}-v${version}.zip`);
    zip.writeZip(zipFile);
    zip.writeZip(versionedZip);
    console.log(`Created downloadable archive: ${zipFile}`);
    console.log(`Created versioned archive:    ${versionedZip}`);

    // Also mirror to root release folder
    const releaseDir = resolve(__dirname, '../release');
    if (fs.existsSync(releaseDir)) {
      fs.copyFileSync(zipFile, resolve(releaseDir, `compust-capture-${currentTarget}.zip`));
      fs.copyFileSync(versionedZip, resolve(releaseDir, `compust-capture-${currentTarget}-v${version}.zip`));
      if (isFx) {
        const amoDir = resolve(releaseDir, 'firefox-amo');
        if (fs.existsSync(amoDir)) {
          fs.copyFileSync(zipFile, resolve(amoDir, `compust-capture-firefox.zip`));
          fs.copyFileSync(versionedZip, resolve(amoDir, `compust-capture-firefox-v${version}.zip`));
        }
      }
    }

    // Verify forward-slash paths in zip
    const entries = zip.getEntries();
    const hasBackslash = entries.some((e) => e.entryName.includes('\\'));
    if (hasBackslash) {
      console.error(`ERROR: Zip for [${currentTarget}] contains backslash paths!`);
      process.exit(1);
    } else {
      console.log(`Verified ${entries.length} entries in [${currentTarget}] archive all use forward slashes.`);
    }
  } catch (err) {
    console.warn(`Warning: Could not create zip archive: ${err.message}`);
  }

  console.log(`Build for [${currentTarget}] complete!`);
}

async function packageAmoSource() {
  console.log(`\nPackaging AMO Source Archive for Firefox...`);
  const AdmZip = (await import('adm-zip')).default;
  const zip = new AdmZip();

  // Folders to include: src, tests
  addFolderToZipForwardSlashes(zip, resolve(__dirname, 'src'), 'src');
  addFolderToZipForwardSlashes(zip, resolve(__dirname, 'tests'), 'tests');

  // Root files to include
  const rootFiles = [
    'package.json',
    'package-lock.json',
    'manifest.firefox.json',
    'manifest.chrome.json',
    'build.js',
    'tsconfig.json',
  ];
  for (const f of rootFiles) {
    const p = resolve(__dirname, f);
    if (fs.existsSync(p)) {
      zip.addFile(f, fs.readFileSync(p));
    }
  }

  // Include BUILD.md from release/firefox-amo if available
  const buildMdPath = resolve(__dirname, '../release/firefox-amo/BUILD.md');
  if (fs.existsSync(buildMdPath)) {
    zip.addFile('BUILD.md', fs.readFileSync(buildMdPath));
  }

  const distDir = resolve(__dirname, 'dist');
  const sourceZip = resolve(distDir, `compust-capture-firefox-v${version}-source.zip`);
  zip.writeZip(sourceZip);
  console.log(`Created AMO source archive: ${sourceZip}`);

  const releaseDir = resolve(__dirname, '../release');
  if (fs.existsSync(releaseDir)) {
    fs.copyFileSync(sourceZip, resolve(releaseDir, `compust-capture-firefox-v${version}-source.zip`));
    const amoDir = resolve(releaseDir, 'firefox-amo');
    if (fs.existsSync(amoDir)) {
      fs.copyFileSync(sourceZip, resolve(amoDir, `compust-capture-firefox-v${version}-source.zip`));
    }
  }

  const entries = zip.getEntries();
  const hasBackslash = entries.some((e) => e.entryName.includes('\\'));
  if (hasBackslash) {
    console.error(`ERROR: AMO source zip contains backslash paths!`);
    process.exit(1);
  } else {
    console.log(`Verified ${entries.length} entries in AMO source archive all use forward slashes.`);
    console.log(`Listing sample:`, entries.slice(0, 10).map((e) => e.entryName).join(', '));
  }
}

async function run() {
  if (isChrome || isAll) {
    await buildTarget('chrome');
  }
  if (isFirefox || isAll) {
    await buildTarget('firefox');
    await packageAmoSource();
  }
}

run().catch((err) => {
  console.error('Build failed:', err);
  process.exit(1);
});
