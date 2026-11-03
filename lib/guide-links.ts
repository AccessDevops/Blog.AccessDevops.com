/**
 * Le pont entre un article et la page du site produit qui correspond à son
 * sujet. Un article explique un problème ; la page guide aide à choisir
 * l'outil qui le règle. Le lien doit tomber au bon endroit, pas sur l'accueil :
 * un lecteur qui vient de lire une heure sur les URL présignées ne cherche pas
 * une page d'accueil, il cherche un client qui signe correctement.
 *
 * Règles de référencement respectées ici :
 *   · lien <a href> réel dans le HTML généré, jamais monté en JavaScript ;
 *   · ancre descriptive, jamais « cliquez ici » ;
 *   · un seul lien contextuel par article — pas de bloc de liens sitewide,
 *     qui ressemble à un échange de liens et se dévalue ;
 *   · propriété du même éditeur, donc pas de rel="nofollow" : c'est un lien
 *     éditorial, pas un lien vendu.
 */

export interface ProductGuide {
  slug: string;
  title: string;
  /** Le problème de l'article, et ce que le guide en fait. */
  blurb: string;
}

const PRODUCT_SITE = 'https://s3explorer.accessdevops.com';

export const GUIDES: Record<string, ProductGuide> = {
  'share-s3-file-presigned-url': {
    slug: 'share-s3-file-presigned-url',
    title: 'Sharing an S3 file with a presigned link',
    blurb:
      'Signing a URL by hand is where most of the friction lives: expiry, content type, and which key signed it.',
  },
  's3-error-codes': {
    slug: 's3-error-codes',
    title: 'SignatureDoesNotMatch and other S3 errors',
    blurb:
      'Most of the errors described above come from four settings. This page walks through each one against AWS, R2, MinIO and Ceph.',
  },
  's3-storage-pricing-comparison': {
    slug: 's3-storage-pricing-comparison',
    title: 'S3 pricing across AWS, R2, B2 and Wasabi',
    blurb:
      'Storage, egress and request prices side by side, with the egress line most comparisons leave out.',
  },
  'incomplete-multipart-uploads': {
    slug: 'incomplete-multipart-uploads',
    title: 'Finding and deleting incomplete multipart uploads',
    blurb:
      'Interrupted uploads keep their parts, and they are billed as storage until someone removes them.',
  },
  's3-compatible-storage-desktop-client': {
    slug: 's3-compatible-storage-desktop-client',
    title: 'One desktop client for every S3-compatible provider',
    blurb:
      'If you work across AWS, R2, B2, MinIO or Garage, the comparison that matters is how many endpoints one window can hold.',
  },
  's3-browser-linux': {
    slug: 's3-browser-linux',
    title: 'S3 browsers for Linux and Ubuntu',
    blurb: 'What actually runs on Linux, and what each option gives up.',
  },
};

export function guideFor(slug: string | undefined): (ProductGuide & { url: string }) | null {
  if (!slug) return null;
  const g = GUIDES[slug];
  if (!g) return null;
  return { ...g, url: `${PRODUCT_SITE}/guides/${g.slug}/` };
}
