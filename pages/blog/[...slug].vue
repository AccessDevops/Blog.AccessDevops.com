<script setup lang="ts">
import { guideFor } from '~/lib/guide-links';

const route = useRoute();
const { trackArticleViewed, trackReadComplete } = useBlogTracking();
const SITE = 'https://blog.accessdevops.com';
const { data: post } = await useAsyncData(`post-${route.path}`, () => queryContent(route.path).findOne());
const { data: allPosts } = await useAsyncData('blog-index', () =>
  queryContent('/blog').only(['title', 'description', '_path', 'tags']).find(),
);

// Le pont vers la page guide du site produit, quand l'article en a une.
const slug = computed(() => (post.value?._path ?? '').replace('/blog/', ''));
const guide = computed(() => guideFor(post.value?.guide as string | undefined, slug.value));

/**
 * Trois articles à lire ensuite. Ordre de priorité : le choix éditorial écrit
 * dans le frontmatter, puis les tags partagés. Un lien interne qui ne correspond
 * à rien coûte plus qu'il ne rapporte — il dilue le sujet de la page.
 */
const related = computed(() => {
  const list = (allPosts.value ?? []) as any[];
  const self = post.value!._path;
  const explicit = (post.value!.related ?? []) as string[];
  if (explicit.length) {
    return explicit
      .map(slug => list.find(x => x._path === `/blog/${slug}` || x._path === slug))
      .filter(Boolean)
      .slice(0, 3);
  }
  const mine = new Set<string>((post.value!.tags ?? []) as string[]);
  return list
    .filter(x => x._path !== self)
    .map(x => ({ x, score: ((x.tags ?? []) as string[]).filter(t => mine.has(t)).length }))
    .filter(v => v.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 2)
    .map(v => v.x);
});

if (!post.value) throw createError({ statusCode: 404, statusMessage: 'Post not found' });
const author = post.value.author || 'Clement Baranger';

// Sentinelle de fin d'article : son entrée dans la fenêtre vaut « lu ».
const endMarker = ref<HTMLElement | null>(null);
let stopReadObserver: (() => void) | null = null;
onMounted(() => {
  trackArticleViewed({
    slug: slug.value,
    title: post.value!.title,
    tags: (post.value!.tags ?? []) as string[],
    guide: post.value!.guide as string | undefined,
  });
  stopReadObserver = trackReadComplete(endMarker.value, slug.value);
});
// Sans cela, l'observateur d'un article continue de surveiller après la
// navigation vers le suivant et attribue sa lecture au mauvais slug.
onBeforeUnmount(() => stopReadObserver?.());
const url = `${SITE}${post.value._path}`;
useSeoMeta({
  title: `${post.value.title} — AccessDevOps Blog`,
  description: post.value.description,
  ogType: 'article',
  ogTitle: post.value.title,
  ogDescription: post.value.description,
  ogImage: `${SITE}/og-image.png`,
  ogUrl: url,
  articlePublishedTime: post.value.date,
  articleAuthor: [author],
  twitterCard: 'summary_large_image',
  twitterImage: `${SITE}/og-image.png`,
  ogVideo: post.value.video ? `${SITE}${post.value.video}` : undefined,
  ogVideoType: post.value.video ? 'video/mp4' : undefined,
});
const jsonld = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'BlogPosting',
      headline: post.value.title,
      description: post.value.description,
      image: [`${SITE}/og-image.png`],
      datePublished: post.value.date,
      dateModified: post.value.updated || post.value.date,
      inLanguage: 'en',
      mainEntityOfPage: { '@type': 'WebPage', '@id': url },
      author: { '@type': 'Person', name: author, url: 'https://cbarange.com' },
      publisher: {
        '@type': 'Organization',
        name: 'AccessDevOps',
        url: 'https://accessdevops.com',
        logo: { '@type': 'ImageObject', url: `${SITE}/icon-512.png`, width: 512, height: 512 },
      },
    },
    {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: `${SITE}/` },
        { '@type': 'ListItem', position: 2, name: post.value.title, item: url },
      ],
    },
  ] as any[],
};
if (post.value.video) {
  jsonld['@graph'].push({
    '@type': 'VideoObject',
    name: post.value.title,
    description: post.value.description,
    thumbnailUrl: [`${SITE}${post.value.videoPoster || '/og-image.png'}`],
    uploadDate: post.value.date,
    duration: post.value.videoDuration || 'PT30S',
    contentUrl: `${SITE}${post.value.video}`,
    embedUrl: url,
    publisher: { '@type': 'Organization', name: 'AccessDevOps', url: 'https://accessdevops.com' },
  });
}
useHead({
  link: [{ rel: 'canonical', href: url }],
  script: [{ type: 'application/ld+json', innerHTML: JSON.stringify(jsonld) }],
});
</script>
<template>
  <article v-if="post">
    <header class="mb-10 border-b border-border pb-8">
      <div class="label flex flex-wrap items-center gap-x-3">
        <time>{{ post.date }}</time><span class="opacity-50">·</span><span>{{ post.author }}</span>
      </div>
      <h1 class="display mt-4">{{ post.title }}</h1>
      <p class="lede mt-4 max-w-[62ch]">{{ post.description }}</p>
    </header>
    <ContentRenderer :value="post" class="prose max-w-none" />
    <!-- Sentinelle de fin de lecture. 1 px de haut : un élément sans hauteur
         n'intersecte rien de façon fiable selon les moteurs. -->
    <div ref="endMarker" aria-hidden="true" class="h-px"></div>

    <aside v-if="guide" class="mt-14 rounded-lg border border-border p-5">
      <p class="text-sm leading-relaxed text-muted-foreground">{{ guide.blurb }}</p>
      <a :href="guide.url" class="link mt-3 inline-block text-sm">
        {{ guide.title }} →
      </a>
    </aside>

    <section v-if="related.length" class="mt-14">
      <h2 class="label">Keep reading</h2>
      <ul class="mt-3 divide-y divide-border border-y border-border">
        <li v-for="r in related" :key="r._path">
          <NuxtLink :to="r._path" class="group block py-4">
            <span class="font-medium underline-offset-4 group-hover:underline">{{ r.title }}</span>
            <span class="mt-1 block text-sm leading-relaxed text-muted-foreground">{{ r.description }}</span>
          </NuxtLink>
        </li>
      </ul>
    </section>

    <footer class="mt-16 flex flex-wrap items-center justify-between gap-4 border-t border-border pt-6">
      <span class="label">{{ (post.tags || []).join(' · ') || 'untagged' }}</span>
      <NuxtLink to="/" class="link text-sm">← All articles</NuxtLink>
    </footer>
  </article>
</template>
