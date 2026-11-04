import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const websiteDir = path.resolve(__dirname, '..');
const rootDir = path.resolve(websiteDir, '..');
const publicDir = path.resolve(websiteDir, 'public');

const filesToSync = ['setup.sh', 'setup.ps1'];

if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

let syncedCount = 0;
for (const file of filesToSync) {
  const sourcePath = path.resolve(rootDir, file);
  const targetPath = path.resolve(publicDir, file);

  if (fs.existsSync(sourcePath)) {
    fs.copyFileSync(sourcePath, targetPath);
    console.log(`[sync-installers] Successfully synced ${file} -> website/public/${file}`);
    syncedCount++;
  } else {
    console.warn(`[sync-installers] Note: Source file ${sourcePath} not found; skipping.`);
  }
}

if (syncedCount > 0) {
  console.log(`[sync-installers] Total ${syncedCount} installer file(s) synchronized for build.`);
}

