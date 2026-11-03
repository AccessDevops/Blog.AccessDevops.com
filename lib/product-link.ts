/**
 * Toute adresse du site produit construite depuis le blog passe par ici.
 *
 * Le classificateur du site produit (`useDownloadTracking.ts`,
 * `classifyTrafficSource`) lit `utm_source` avant le référent et renvoie sa
 * valeur telle quelle. Un lien taggé `utm_source=blog` arrive donc sur
 * `website_visited` avec `source: "blog"`, sans qu'aucune liste d'hôtes ait à
 * être tenue à jour des deux côtés.
 *
 * `utm_campaign` porte le slug de l'article d'origine : c'est ce qui permet de
 * savoir quel article amène des téléchargements, pas seulement que « le blog »
 * en amène.
 *
 * Les liens écrits à la main dans le Markdown ne passent pas par cette
 * fonction et arrivent donc sans utm. Ils restent attribués grâce à la règle
 * de référent `blog.accessdevops.com` côté site produit — le tag n'ajoute que
 * la granularité par article.
 */
export const PRODUCT_SITE = 'https://s3explorer.accessdevops.com';
export const PRODUCT_HOST = 's3explorer.accessdevops.com';

export function productUrl(path = '/', campaign = 'blog'): string {
  const url = new URL(path, PRODUCT_SITE);
  url.searchParams.set('utm_source', 'blog');
  url.searchParams.set('utm_medium', 'referral');
  url.searchParams.set('utm_campaign', campaign);
  return url.toString();
}
