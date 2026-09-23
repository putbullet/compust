import { defineConfig } from 'vite';
import { resolve } from 'path';
import fs from 'fs';

export default defineConfig(({ mode }) => {
  const isFirefox = mode === 'firefox';
  const outDir = isFirefox ? 'dist/firefox' : 'dist/chrome';

  return {
    root: resolve(__dirname, '.'),
    build: {
      outDir,
      emptyOutDir: true,
      target: 'es2022',
      rollupOptions: {
        input: {
          background: resolve(__dirname, 'src/background/index.ts'),
          linkedin: resolve(__dirname, 'src/content/linkedin.ts'),
          indeed: resolve(__dirname, 'src/content/indeed.ts'),
          glassdoor: resolve(__dirname, 'src/content/glassdoor.ts'),
          welcomeToTheJungle: resolve(__dirname, 'src/content/welcomeToTheJungle.ts'),
          generic: resolve(__dirname, 'src/content/generic.ts'),
          popup: resolve(__dirname, 'src/popup/index.html'),
          options: resolve(__dirname, 'src/options/index.html'),
        },
        output: {
          entryFileNames: (chunkInfo) => {
            if (chunkInfo.name === 'background') {
              return 'src/background/index.js';
            }
            if (['linkedin', 'indeed', 'glassdoor', 'welcomeToTheJungle', 'generic'].includes(chunkInfo.name)) {
              return `src/content/${chunkInfo.name}.js`;
            }
            return 'assets/[name]-[hash].js';
          },
          chunkFileNames: 'assets/[name]-[hash].js',
          assetFileNames: (assetInfo) => {
            if (assetInfo.names && assetInfo.names.some(n => n.endsWith('.css'))) {
              return 'assets/[name][extname]';
            }
            return 'assets/[name]-[hash][extname]';
          },
        },
      },
    },
    plugins: [
      {
        name: 'copy-manifest-and-assets',
        closeBundle() {
          const manifestSource = isFirefox
            ? resolve(__dirname, 'manifest.firefox.json')
            : resolve(__dirname, 'manifest.chrome.json');
          const manifestTarget = resolve(__dirname, outDir, 'manifest.json');
          fs.copyFileSync(manifestSource, manifestTarget);

          // Copy icons to dist/<mode>/assets/icons/
          const iconsSrcDir = resolve(__dirname, 'src/assets/icons');
          const iconsDestDir = resolve(__dirname, outDir, 'assets/icons');
          if (fs.existsSync(iconsSrcDir)) {
            if (!fs.existsSync(iconsDestDir)) {
              fs.mkdirSync(iconsDestDir, { recursive: true });
            }
            const files = fs.readdirSync(iconsSrcDir);
            for (const file of files) {
              fs.copyFileSync(
                resolve(iconsSrcDir, file),
                resolve(iconsDestDir, file)
              );
            }
          }
        },
      },
    ],
  };
});
