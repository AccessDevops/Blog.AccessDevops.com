import posthog from 'posthog-js';
import { PRODUCT_HOST } from '~/lib/product-link';

/**
 * PostHog pour le blog, dans le même projet que le site produit et
 * l'application desktop (145681). Même projet volontairement : la question à
 * laquelle ce blog doit répondre est « un lecteur devient-il un visiteur du
 * site, puis une installation ? ». Trois projets séparés rendraient cet
 * entonnoir impossible à écrire en une requête.
 *
 * ── Quota (offre gratuite : 1 M d'événements par mois) ────────────────────
 * Octobre 2026, le mois le plus chargé à ce jour, a produit 29 449 événements
 * tous produits confondus, soit 2,9 % du quota. Le blog ajoute au plus trois
 * événements par lecteur et par article. Les postes coûteux sont désactivés
 * explicitement ci-dessous plutôt que laissés aux valeurs par défaut :
 *
 *   · autocapture        → un article est du texte ; capturer chaque clic sur
 *                          un paragraphe produirait dix fois le volume des
 *                          pages vues pour aucune information exploitable.
 *                          Les seuls clics qui comptent (vers le site
 *                          produit) sont capturés nommément plus bas.
 *   · session recording  → facturé sur un compteur distinct et bien plus bas
 *                          que celui des événements ; c'est le premier poste
 *                          qui fait sauter une offre gratuite.
 *   · web vitals         → quatre événements par page vue, pour une mesure de
 *                          performance que Search Console donne déjà.
 *   · $pageleave         → doublerait le volume des pages vues. La profondeur
 *                          de lecture est mesurée par `blog_read_complete`,
 *                          qui vaut un seul événement par article lu.
 *
 * Reste donc : $pageview, blog_article_viewed, blog_read_complete,
 * blog_product_click. Soit ~4 événements pour un lecteur qui lit un article
 * en entier et clique vers le site.
 */
export default defineNuxtPlugin((nuxtApp) => {
  const { posthogKey, posthogHost, posthogUiHost } = useRuntimeConfig().public as {
    posthogKey: string; posthogHost: string; posthogUiHost: string;
  };

  if (!posthogKey) {
    // Le même piège que sur le site produit : sans clé au moment du build, la
    // page fonctionne et la mesure est muette. Le dire une fois.
    console.warn(
      '[analytics] NUXT_PUBLIC_POSTHOG_KEY absente au build — aucune mesure ne sera enregistrée.',
    );
    return;
  }

  const client = posthog.init(posthogKey, {
    api_host: posthogHost,
    ui_host: posthogUiHost,
    persistence: 'localStorage+cookie',
    // Le site produit est sur s3explorer.accessdevops.com, le blog sur
    // blog.accessdevops.com. Un cookie posé sur `.accessdevops.com` suit le
    // lecteur d'un sous-domaine à l'autre, ce que localStorage ne fait pas :
    // c'est ce qui permet de voir un même distinct_id lire un article puis
    // télécharger. C'est déjà la valeur par défaut de posthog-js ; on l'écrit
    // parce que tout l'intérêt de la mesure en dépend.
    cross_subdomain_cookie: true,
    autocapture: false,
    capture_pageview: false, // capturé à la main ci-dessous
    capture_pageleave: false,
    capture_performance: false,
    disable_session_recording: true,
    defaults: '2025-05-24',
  })!;

  /**
   * Pages vues à la main plutôt que par posthog-js.
   *
   * Le blog est prérendu puis hydraté en SPA : la capture automatique a
   * changé de mécanisme entre les versions de posthog-js (`true`, puis
   * `'history_change'`). Appeler `capture` sur le hook de Nuxt donne le même
   * résultat sans dépendre de la version installée.
   */
  const capturePageview = () => {
    client.capture('$pageview', { $current_url: window.location.href });
  };
  nuxtApp.hook('app:mounted', capturePageview);
  nuxtApp.hook('page:finish', () => {
    // `app:mounted` a déjà compté la première page ; ce hook ne doit compter
    // que les navigations qui suivent.
    if (!(window as any).__blogFirstPageDone) {
      (window as any).__blogFirstPageDone = true;
      return;
    }
    capturePageview();
  });

  /**
   * Tout clic vers le site produit, d'où qu'il parte.
   *
   * Écouteur délégué sur le document plutôt qu'un `@click` par lien : les
   * liens les plus nombreux sont écrits dans le Markdown des articles et ne
   * passent par aucun composant Vue. En phase de capture, pour s'exécuter
   * même si un gestionnaire intermédiaire arrête la propagation. Rien n'est
   * annulé ni retardé : la navigation part normalement, et posthog-js vide sa
   * file via sendBeacon au déchargement.
   */
  if (import.meta.client) {
    document.addEventListener('click', (e) => {
      const target = e.target as HTMLElement | null;
      const anchor = target?.closest?.('a[href]') as HTMLAnchorElement | null;
      if (!anchor) return;
      let host = '';
      try { host = new URL(anchor.href, window.location.href).hostname; } catch { return; }
      if (host !== PRODUCT_HOST) return;

      client.capture('blog_product_click', {
        // Chemin seul : l'URL complète ferait exploser la cardinalité avec les
        // utm, alors que la question est « vers quelle page du site ? ».
        target_path: new URL(anchor.href, window.location.href).pathname,
        from_path: window.location.pathname,
        // Où se trouvait le lien. `in_article` est le seul qui prouve que
        // l'article lui-même convertit, par opposition au bandeau de navigation.
        placement: anchor.closest('article .prose') ? 'in_article'
          : anchor.closest('aside') ? 'guide_card'
            : anchor.closest('header') ? 'nav'
              : anchor.closest('footer') ? 'footer'
                : 'other',
        anchor_text: (anchor.textContent || '').trim().slice(0, 80),
      });
    }, { capture: true });
  }

  return { provide: { posthog: client } };
});
