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
  /** Chemin réel sur le site produit. Par défaut `/guides/<slug>/`. */
  path?: string;
}

import { productUrl } from './product-link';

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
  'cyberduck-alternative': {
    slug: 'cyberduck-alternative',
    title: 'Cyberduck as an S3 client, and where it stops',
    blurb:
      'Cyberduck speaks dozens of protocols; this page compares it with a client built for S3 alone, on macOS and Windows.',
  },
  'migrate-from-minio': {
    slug: 'migrate-from-minio',
    title: 'Migrating data off MinIO',
    blurb:
      'Moving out of an unmaintained MinIO: in place to Silo, or to Garage and RustFS through the S3 API with rclone.',
  },
  'minio-alternatives': {
    slug: 'minio-alternatives',
    title: 'MinIO is unmaintained — the alternatives',
    blurb:
      'What actually changed for the open-source edition, the security exposure that follows, and which servers replace it.',
  },
  's3-browser-alternative': {
    slug: 's3-browser-alternative',
    title: 'S3 Browser is now CS Browser',
    blurb:
      'Windows-only, free for two accounts: what CS Browser still does well, and where a dedicated S3 client earns its place.',
  },
  's3-in-2027-readiness': {
    slug: 's3-in-2027-readiness',
    title: 'S3 in 2027 and the EU Data Act deadline',
    blurb:
      'From 12 January 2027 the switching charges disappear, egress included — what it covers and what it does not.',
  },
  's3-viewer-preview-files': {
    slug: 's3-viewer-preview-files',
    title: 'Previewing S3 files without downloading them',
    blurb:
      'Why an S3 object does not open in a browser, what presigned URLs change, and how the console handles previews.',
  },
  'winscp-s3-alternative': {
    slug: 'winscp-s3-alternative',
    title: 'WinSCP against S3-compatible storage',
    blurb:
      'WinSCP does speak S3 on Windows; this page separates what it covers from what it leaves to a dedicated client.',
  },

  // Pages par fournisseur : c'est la page qui répond à « comment je me connecte
  // à X », donc celle qu'un article sur X doit ouvrir.
  'provider-aws': {
    slug: 'aws',
    path: '/providers/aws/',
    title: 'Connecting to Amazon S3',
    blurb: 'No endpoint to fill in, region-based routing and virtual-hosted addressing.',
  },
  'provider-backblaze': {
    slug: 'backblaze',
    path: '/providers/backblaze/',
    title: 'Connecting to Backblaze B2',
    blurb: 'Cluster-specific endpoints and keyID as the access key over the S3-compatible API.',
  },
  'provider-ceph': {
    slug: 'ceph',
    path: '/providers/ceph/',
    title: 'Connecting to Ceph RADOS Gateway',
    blurb: 'Port 7480 by default, credentials from radosgw-admin, both signature versions.',
  },
  'provider-clever-cloud': {
    slug: 'clever-cloud',
    path: '/providers/clever-cloud/',
    title: 'Connecting to Clever Cloud Cellar',
    blurb: 'One fixed endpoint, keys from the add-on dashboard, an empty region name.',
  },
  'provider-cloudflare': {
    slug: 'cloudflare',
    path: '/providers/cloudflare/',
    title: 'Connecting to Cloudflare R2',
    blurb: 'Account-scoped endpoint, path-style addressing required, no regions.',
  },
  'provider-dell-ecs': {
    slug: 'dell-ecs',
    path: '/providers/dell-ecs/',
    title: 'Connecting to Dell EMC ECS',
    blurb: 'Namespace-scoped object users, the 9020/9021 port pair, Content-MD5 quirks.',
  },
  'provider-digitalocean': {
    slug: 'digitalocean',
    path: '/providers/digitalocean/',
    title: 'Connecting to DigitalOcean Spaces',
    blurb: 'Region-based endpoints and virtual-hosted addressing only.',
  },
  'provider-france-nuage': {
    slug: 'france-nuage',
    path: '/providers/france-nuage/',
    title: 'Connecting to France Nuage',
    blurb: 'One fixed endpoint, path-style addressing, keys issued by the Ceph gateway.',
  },
  'provider-gcs': {
    slug: 'gcs',
    path: '/providers/gcs/',
    title: 'Connecting to Google Cloud Storage',
    blurb: 'The interoperability API: fixed endpoint and HMAC keys instead of service accounts.',
  },
  'provider-minio': {
    slug: 'minio',
    path: '/providers/minio/',
    title: 'Connecting to MinIO',
    blurb: 'Full URL with port, path-style addressing mandatory, region ignored.',
  },
  'provider-ovhcloud': {
    slug: 'ovhcloud',
    path: '/providers/ovhcloud/',
    title: 'Connecting to OVHcloud Object Storage',
    blurb: 'Datacenter-coded regions and S3 users created under Public Cloud.',
  },
  'provider-wasabi': {
    slug: 'wasabi',
    path: '/providers/wasabi/',
    title: 'Connecting to Wasabi',
    blurb: 'AWS-shaped regions and credentials, region-specific endpoints.',
  },
};

/** Toutes les pages profondes connues, pour les contrôles de publication. */
export function guidePaths(): string[] {
  return Object.values(GUIDES).map((g) => g.path ?? `/guides/${g.slug}/`);
}

/**
 * `campaign` porte le slug de l'article d'où part le lien, pas celui du guide
 * d'arrivée : la question est « quel article convertit », et deux articles
 * différents pointent vers le même guide.
 */
export function guideFor(
  slug: string | undefined,
  campaign = 'blog',
): (ProductGuide & { url: string }) | null {
  if (!slug) return null;
  const g = GUIDES[slug];
  if (!g) return null;
  return { ...g, url: productUrl(g.path ?? `/guides/${g.slug}/`, campaign) };
}
