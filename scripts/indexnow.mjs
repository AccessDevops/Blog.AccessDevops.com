#!/usr/bin/env node
/**
 * Soumission IndexNow — Bing, Yandex, Naver, Seznam, Yep.
 *
 * IndexNow ne sert à RIEN pour Google : Google l'ignore et continue de passer
 * par son sitemap dans la Search Console. L'intérêt réel est ailleurs —
 * l'index de Bing alimente ChatGPT Search et Copilot. Un article absent de Bing
 * est un article que les assistants IA citent mal, ou pas du tout.
 *
 * Règles de conduite :
 *   · on ne soumet que des URL qui répondent 200 (une URL morte fait perdre de
 *     la confiance au point de terminer) ;
 *   · on ne soumet que ce qui a changé quand on peut le savoir ;
 *   · l'échec n'échoue jamais le build : un référencement qui casse une mise en
 *     ligne est un mauvais référencement.
 *
 * Usage :
 *   node scripts/indexnow.mjs --dry-run      # montre sans envoyer
 *   node scripts/indexnow.mjs                # changements depuis le dernier commit
 *   node scripts/indexnow.mjs --all          # tout le sitemap
 *   node scripts/indexnow.mjs --all --no-live-check
 */
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { join } from 'node:path';

const HOST = 'blog.accessdevops.com';
const ORIGIN = `https://${HOST}`;
const ENDPOINT = 'https://api.indexnow.org/indexnow';
const DIST = 'dist';
const args = process.argv.slice(2);
const ALL = args.includes('--all');
const DRY = args.includes('--dry-run');
const LIVE_CHECK = !args.includes('--no-live-check');

/** La clé vit dans public/<clé>.txt : le fichier doit être servi à la racine. */
function readKey() {
  const dir = 'public';
  const candidates = readdirSync(dir).filter(f => /^[a-f0-9]{8,128}\.txt$/i.test(f));
  if (candidates.length !== 1) {
    throw new Error(
      `attendu exactement un fichier de clé dans public/ (format <hex>.txt), trouvé ${candidates.length}`,
    );
  }
  const file = candidates[0];
  const key = readFileSync(join(dir, file), 'utf8').trim();
  return { key, keyFile: file };
}

function sitemapUrls() {
  const candidates = ['sitemap_index.xml', 'sitemap.xml'].map(f => join(DIST, f));
  const path = candidates.find(p => existsSync(p));
  if (!path) throw new Error(`aucun sitemap dans ${DIST}/ — lancer « npm run generate » d'abord`);
  const xml = readFileSync(path, 'utf8');
  // un sitemap index pointe vers d'autres sitemaps : on les suit d'un niveau
  if (path.endsWith('sitemap_index.xml')) {
    const children = [...xml.matchAll(/<loc>([^<]+\.xml[^<]*)<\/loc>/g)].map(m => m[1]);
    const out = [];
    for (const child of children) {
      const local = child.replace(ORIGIN, '').replace(/^\//, '');
      const p = join(DIST, local);
      if (existsSync(p)) out.push(...[...readFileSync(p, 'utf8').matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1]));
    }
    return out;
  }
  return [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1]);
}

/** URL touchées par le dernier commit, déduites des fichiers de contenu. */
function changedUrls(all) {
  try {
    const changed = execSync('git diff --name-only HEAD^ HEAD', { encoding: 'utf8' })
      .split('\n').filter(Boolean);
    const slugs = changed
      .filter(f => f.startsWith('content/') && f.endsWith('.md'))
      .map(f => f.replace(/^content\//, '').replace(/\.md$/, '').replace(/\/index$/, ''));
    if (!slugs.length) return { urls: [], reason: 'aucun contenu modifié dans le dernier commit' };
    const urls = all.filter(u => slugs.some(s => u.includes(`/${s}`) || u.endsWith(s)));
    return { urls, reason: `${changed.length} fichier(s) modifiés, ${slugs.length} article(s)` };
  } catch {
    return { urls: all, reason: 'git indisponible (clone superficiel) — repli sur tout le sitemap' };
  }
}

async function isLive(url) {
  try {
    const r = await fetch(url, { method: 'HEAD', redirect: 'follow' });
    return r.status === 200;
  } catch {
    return false;
  }
}

async function main() {
  const { key, keyFile } = readKey();
  const all = sitemapUrls();
  if (!all.length) throw new Error('sitemap vide');

  let urls = all;
  let why = `tout le sitemap (${all.length})`;
  if (!ALL) {
    const c = changedUrls(all);
    urls = c.urls;
    why = c.reason;
  }

  if (LIVE_CHECK && urls.length) {
    const alive = [];
    for (const u of urls) if (await isLive(u)) alive.push(u);
    const dead = urls.length - alive.length;
    urls = alive;
    if (dead) why += ` · ${dead} URL non servie(s) ignorée(s)`;
  }

  console.log(`IndexNow · hôte ${HOST} · clé ${keyFile}`);
  console.log(`  sélection : ${why}`);
  console.log(`  à soumettre : ${urls.length}`);
  urls.forEach(u => console.log(`    ${u}`));

  if (!urls.length) { console.log('  rien à faire.'); return; }

  const body = {
    host: HOST,
    key,
    keyLocation: `${ORIGIN}/${keyFile}`,
    urlList: urls,
  };

  if (DRY) {
    console.log('\n--dry-run : corps envoyé\n' + JSON.stringify(body, null, 2));
    return;
  }

  const res = await fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  // 200 = accepté, 202 = accepté, clé en cours de validation
  console.log(`\n  réponse ${res.status} ${res.statusText}${text ? ` — ${text.slice(0, 200)}` : ''}`);
  if (![200, 202].includes(res.status)) {
    console.log('  ⚠ refus : vérifier que le fichier de clé est bien servi à la racine du site.');
    process.exitCode = 0; // jamais bloquant
  }
}

main().catch(err => {
  console.error('IndexNow · échec non bloquant :', err.message);
  process.exitCode = 0;
});
