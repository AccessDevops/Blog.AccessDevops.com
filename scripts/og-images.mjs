#!/usr/bin/env node
/**
 * Une image Open Graph par article, rendue depuis assets-src/og-article.html.
 *
 * Pourquoi un script séparé de assets-src/build_assets.py : celui-là produit
 * les icônes et l'image générique, dépend de Pillow et d'un chemin Chrome
 * codé en dur pour une autre machine. Celui-ci ne dépend que de Node et d'un
 * Chrome trouvé automatiquement, pour pouvoir tourner là où on publie.
 *
 * Le fichier public/og/<slug>.png n'est pas obligatoire : lib/og-manifest.json
 * dit lesquels existent, et un article absent du manifeste retombe sur
 * l'image générique. Un article publié sans avoir lancé ce script a donc une
 * image correcte, jamais une image cassée.
 *
 *   node scripts/og-images.mjs            # ne régénère que ce qui manque
 *   node scripts/og-images.mjs --force    # tout refaire
 *   node scripts/og-images.mjs --only=<slug>
 */
import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync, statSync, rmSync } from 'node:fs';
import { spawn, spawnSync } from 'node:child_process';
import { join, basename } from 'node:path';

const W = 1200, H = 630;
const CONTENT = 'content/blog';
const OUT_DIR = 'public/og';
const MANIFEST = 'lib/og-manifest.json';
const TPL = 'assets-src/og-article.html';
const args = process.argv.slice(2);
const FORCE = args.includes('--force');
const ONLY = (args.find(a => a.startsWith('--only=')) || '').split('=')[1];

function findChrome() {
  const home = process.env.HOME || '';
  const candidates = [
    process.env.CHROME_PATH,
    // Un Chrome « for testing » posé à côté de l'outil : le serveur qui publie
    // n'a pas de navigateur système, et en installer un via apt demande root
    // alors qu'un binaire téléchargé se suffit à lui-même.
    `${home}/.hermes/tools/chrome-headless-shell/chrome-headless-shell`,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  ].filter(Boolean);
  for (const c of candidates) if (existsSync(c)) return c;
  for (const bin of ['google-chrome', 'chromium', 'chrome-headless-shell']) {
    const which = spawnSync('which', [bin], { encoding: 'utf8' });
    if (which.status === 0) return which.stdout.trim();
  }
  return null;
}

/** Frontmatter minimal : on ne lit que title, date et tags. */
function frontmatter(text) {
  const m = /^---\n([\s\S]*?)\n---\n/.exec(text);
  if (!m) return {};
  const fm = {};
  for (const line of m[1].split('\n')) {
    const i = line.indexOf(':');
    if (i < 0) continue;
    const k = line.slice(0, i).trim();
    let v = line.slice(i + 1).trim().replace(/^["']|["']$/g, '');
    if (v.startsWith('[') && v.endsWith(']')) {
      fm[k] = v.slice(1, -1).split(',').map(x => x.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
    } else fm[k] = v;
  }
  fm.__body = text.slice(m[0].length);
  return fm;
}

const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/** Les dimensions sortent de l'en-tête PNG — pas de dépendance image. */
function pngSize(file) {
  const b = readFileSync(file);
  if (b.length < 24 || b.readUInt32BE(0) !== 0x89504e47) return null;
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

const chrome = findChrome();
if (!chrome) {
  console.log('[og] aucun Chrome trouvé — rien généré, les articles gardent l\'image générique');
  process.exitCode = 0;
} else {
  mkdirSync(OUT_DIR, { recursive: true });
  const tpl = readFileSync(TPL, 'utf8');
  const files = readdirSync(CONTENT).filter(f => f.endsWith('.md'));
  const manifest = existsSync(MANIFEST) ? JSON.parse(readFileSync(MANIFEST, 'utf8')) : {};
  const tmp = '.og-tmp';
  mkdirSync(tmp, { recursive: true });
  let made = 0, kept = 0, failed = 0;

  for (const f of files) {
    const slug = basename(f, '.md');
    if (ONLY && slug !== ONLY) continue;
    const out = join(OUT_DIR, `${slug}.png`);
    const src = join(CONTENT, f);
    if (!FORCE && existsSync(out) && statSync(out).mtimeMs > statSync(src).mtimeMs) { kept++; manifest[slug] = true; continue; }

    const fm = frontmatter(readFileSync(src, 'utf8'));
    const title = fm.title || slug;
    const tags = Array.isArray(fm.tags) ? fm.tags : [];
    const words = fm.__body.split(/\s+/).filter(Boolean).length;
    // replaceAll et non replace : le commentaire en tête du gabarit nomme les
    // marqueurs, et replace ne remplace que la première occurrence — c'était
    // celle du commentaire, les images sortaient avec « __TITLE__ » écrit
    // dessus.
    const html = tpl
      .replaceAll('__TITLE__', esc(title))
      .replaceAll('__KICKER__', esc(tags.slice(0, 3).join(' · ').toUpperCase() || 'ACCESSDEVOPS'))
      .replaceAll('__READ__', `${Math.max(1, Math.round(words / 220))} min read`)
      // Le seuil est en caractères, pas en mots : ce qui déborde est la
      // largeur du texte rendu, et un titre court en mots peut être long.
      .replaceAll('__SIZE__', title.length > 58 ? 'xlong' : title.length > 42 ? 'long' : '');
    const page = join(tmp, `${slug}.html`);
    writeFileSync(page, html);

    const r = spawnSync(chrome, [
      // --no-sandbox : le serveur de publication n'a pas d'espaces de noms
      // utilisateur, et Chrome refuse alors de démarrer (rc=null, aucune
      // capture). On ne rend ici que nos propres gabarits, depuis le disque.
      '--headless', '--disable-gpu', '--hide-scrollbars', '--no-first-run', '--no-sandbox',
      '--force-device-scale-factor=1', `--window-size=${W},${H}`,
      `--screenshot=${join(process.cwd(), out)}`,
      `--user-data-dir=${join(process.cwd(), tmp, 'profile')}`,
      // file:// plutôt qu'un serveur local : le gabarit ne charge que des
      // polices voisines, et Chrome les lit sans restriction depuis le disque.
      `file://${join(process.cwd(), page)}`,
    ], { timeout: 90_000, encoding: 'utf8' });

    const size = existsSync(out) ? pngSize(out) : null;
    if (r.status !== 0 || !size) { console.log(`[og] ${slug}: ÉCHEC (rc=${r.status})`); failed++; continue; }
    if (size.w !== W || size.h !== H) { console.log(`[og] ${slug}: taille ${size.w}x${size.h}, attendu ${W}x${H} — rejeté`); rmSync(out); failed++; continue; }
    manifest[slug] = true; made++;
    console.log(`[og] ${slug}: ${size.w}x${size.h}`);
  }

  // Un slug dont l'article a disparu ne doit pas rester dans le manifeste.
  const live = new Set(files.map(f => basename(f, '.md')));
  for (const k of Object.keys(manifest)) if (!live.has(k) || !existsSync(join(OUT_DIR, `${k}.png`))) delete manifest[k];
  writeFileSync(MANIFEST, JSON.stringify(manifest, Object.keys(manifest).sort(), 2) + '\n');
  rmSync(tmp, { recursive: true, force: true });
  console.log(`[og] ${made} générée(s), ${kept} à jour, ${failed} en échec — ${Object.keys(manifest).length} dans le manifeste`);
}
