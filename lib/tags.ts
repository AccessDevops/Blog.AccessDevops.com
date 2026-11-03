/**
 * Les tags du frontmatter, et ce qu'on en fait côté référencement.
 *
 * Une page de tag n'a d'intérêt que si elle rassemble. Avec un seul article,
 * elle duplique l'article sans rien ajouter : c'est exactement la page mince
 * que Google classe « crawled, currently not indexed », et sur un domaine
 * jeune chaque URL faible coûte du budget d'exploration. D'où le seuil.
 *
 * Les pages sous le seuil existent quand même — les tags sont affichés sous
 * chaque article et doivent mener quelque part — mais elles portent
 * `noindex, follow` et restent hors du sitemap. Elles transmettent, elles ne
 * se présentent pas.
 */
export const MIN_POSTS_FOR_INDEX = 2;

/** `cost-optimisation` → `Cost optimisation`. Les sigles restent en capitales. */
const ACRONYMS = new Set(['s3', 'iam', 'sts', 'aws', 'api', 'cli', 'dr']);

export function tagLabel(tag: string): string {
  return tag
    .split('-')
    .map((w, i) => (ACRONYMS.has(w) ? w.toUpperCase() : i === 0 ? w[0]!.toUpperCase() + w.slice(1) : w))
    .join(' ');
}

/**
 * Sans barre finale, comme `/blog/<slug>`. Le site est généré avec
 * `autoSubfolderIndex: false` : une barre finale produirait un répertoire et
 * un canonical que le sitemap écrirait sans barre — deux URL pour une page.
 */
export function tagPath(tag: string): string {
  return `/tags/${tag}`;
}

export interface TaggedPost { _path?: string; title?: string; description?: string; date?: string; tags?: string[] }

export function countTags(posts: TaggedPost[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const p of posts) for (const t of p.tags ?? []) counts.set(t, (counts.get(t) ?? 0) + 1);
  return counts;
}

/** Les tags assez fournis pour mériter une page indexable, du plus gros au plus petit. */
export function indexableTags(posts: TaggedPost[]): { tag: string; count: number }[] {
  return [...countTags(posts).entries()]
    .filter(([, n]) => n >= MIN_POSTS_FOR_INDEX)
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
}
