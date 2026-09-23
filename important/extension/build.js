import { build } from 'vite';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const target = process.argv[2] || 'chrome';
const isFirefox = target === 'firefox';
const outDir = resolve(__dirname, isFirefox ? 'dist/firefox' : 'dist/chrome');

console.log(`Building Compust Capture Extension for [${target}] -> ${outDir}`);

async function runBuild() {
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

  // 3. Build Content Scripts as self-contained IIFE (no external ES imports)
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
  const manifestSrc = isFirefox
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

  // 6. Create downloadable zip archive
  try {
    const AdmZip = (await import('adm-zip')).default;
    const zip = new AdmZip();
    zip.addLocalFolder(outDir);
    const distDir = resolve(__dirname, 'dist');
    const zipFile = resolve(distDir, `compust-capture-${target}.zip`);
    zip.writeZip(zipFile);
    console.log(`Created downloadable archive: ${zipFile}`);
  } catch (err) {
    console.warn(`Warning: Could not create zip archive: ${err.message}`);
  }

  console.log(`Build for [${target}] complete!`);
}

runBuild().catch((err) => {
  console.error('Build failed:', err);
  process.exit(1);
});
