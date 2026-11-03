/**
 * Les deux événements propres au blog, et le classement de la source.
 *
 * Le vocabulaire du classement est volontairement identique à celui de
 * `useDownloadTracking.ts` sur le site produit (`bing`, `google`,
 * `duckduckgo`, `ai_assistant`, `social`, `referral`, `direct`). Sans cela,
 * comparer l'acquisition du blog et celle du site demanderait de traduire
 * deux nomenclatures à chaque requête.
 */

const SEARCH_ENGINES: [string, (h: string) => boolean][] = [
  ['google', h => h.includes('google.')],
  ['bing', h => h.includes('bing.')],
  ['duckduckgo', h => h.includes('duckduckgo.')],
  ['yandex', h => h.includes('yandex.')],
  ['brave', h => h.includes('search.brave.')],
  ['ecosia', h => h.includes('ecosia.')],
  ['startpage', h => h.includes('startpage.')],
  ['baidu', h => h.includes('baidu.')],
];

// Les assistants testés avant les moteurs : gemini.google.com doit compter
// comme assistant, pas comme Google.
const AI_ASSISTANTS = [
  'chatgpt.com', 'chat.openai.com', 'openai.com', 'perplexity.ai',
  'claude.ai', 'gemini.google.com', 'copilot.microsoft.com', 'phind.com',
];

function classifyHost(host: string): string | null {
  if (AI_ASSISTANTS.some(s => host === s || host.endsWith(`.${s}`))) return 'ai_assistant';
  for (const [name, match] of SEARCH_ENGINES) if (match(host)) return name;
  return null;
}

export function classifyBlogSource(): string {
  if (typeof window === 'undefined') return 'unknown';
  const params = new URLSearchParams(window.location.search);

  const utm = params.get('utm_source');
  if (utm) {
    const lower = utm.toLowerCase();
    return classifyHost(lower) ?? lower.slice(0, 32);
  }

  const ref = (document.referrer || '').toLowerCase();
  if (!ref) return 'direct';
  try {
    const host = new URL(ref).hostname;
    if (host === 'blog.accessdevops.com') return 'internal';
    // Le site produit renvoyant vers le blog est une circulation interne au
    // même éditeur, pas une acquisition : la compter comme `referral` ferait
    // croire à un apport extérieur.
    if (host.endsWith('accessdevops.com')) return 'own_network';
    const engine = classifyHost(host);
    if (engine) return engine;
    if (['news.ycombinator.com', 'reddit.com', 'x.com', 'twitter.com', 'linkedin.com', 'lobste.rs', 't.co'].some(s => host.endsWith(s))) return 'social';
    return 'referral';
  } catch {
    return 'direct';
  }
}

export function useBlogTracking() {
  const { $posthog } = useNuxtApp() as unknown as { $posthog?: { capture: (e: string, p?: Record<string, unknown>) => void } };

  function trackArticleViewed(props: { slug: string; title: string; tags?: string[]; guide?: string }) {
    $posthog?.capture('blog_article_viewed', {
      ...props,
      tags: props.tags ?? [],
      source: classifyBlogSource(),
    });
  }

  /**
   * Un seul événement par article lu, émis quand la fin du corps de l'article
   * entre dans la fenêtre. Mesure la lecture, pas le défilement : c'est la
   * différence entre « 40 visiteurs » et « 6 lecteurs », et c'est le seul
   * chiffre qui dit si écrire un article par jour sert à quelque chose.
   *
   * Renvoie une fonction d'arrêt, à appeler au démontage, sinon l'observateur
   * d'un article survit à la navigation vers le suivant.
   */
  function trackReadComplete(el: HTMLElement | null, slug: string): () => void {
    if (!el || typeof IntersectionObserver === 'undefined') return () => {};
    let fired = false;
    const observer = new IntersectionObserver((entries) => {
      if (fired || !entries.some(e => e.isIntersecting)) return;
      fired = true;
      $posthog?.capture('blog_read_complete', { slug });
      observer.disconnect();
      // Pas de rootMargin négatif : la sentinelle est un élément sans
      // hauteur propre, et réduire la racine par le bas peut l'exclure
      // exactement au moment où le lecteur atteint la fin. Vérifié en
      // navigateur : avec -10 %, l'événement ne partait jamais.
    });
    observer.observe(el);
    return () => observer.disconnect();
  }

  return { trackArticleViewed, trackReadComplete };
}
