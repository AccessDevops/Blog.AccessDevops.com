<script setup lang="ts">
import { MIN_POSTS_FOR_INDEX, tagLabel, tagPath, indexableTags } from '~/lib/tags';

const route = useRoute();
const SITE = 'https://blog.accessdevops.com';
const tag = computed(() => String(route.params.tag));

const { data: posts } = await useAsyncData(`tag-${tag.value}`, () =>
  queryContent('/blog')
    .where({ tags: { $contains: tag.value } })
    .only(['title', 'description', '_path', 'date', 'tags'])
    .sort({ date: -1 })
    .find(),
);
const { data: allPosts } = await useAsyncData('tag-all', () =>
  queryContent('/blog').only(['tags']).find(),
);

if (!posts.value?.length) throw createError({ statusCode: 404, statusMessage: 'Tag not found' });

const label = computed(() => tagLabel(tag.value));
const url = computed(() => `${SITE}${tagPath(tag.value)}`);
// Sous le seuil, la page existe mais ne se présente pas aux moteurs. `follow`
// et non `none` : les liens vers les articles doivent continuer de compter.
const thin = computed(() => (posts.value?.length ?? 0) < MIN_POSTS_FOR_INDEX);
const siblings = computed(() => indexableTags((allPosts.value ?? []) as any[]).filter(t => t.tag !== tag.value));

useSeoMeta({
  title: `${label.value} — AccessDevOps Blog`,
  description: `Every article on ${label.value}: ${posts.value!.slice(0, 3).map(p => p.title).join(' · ')}.`,
  robots: thin.value ? 'noindex, follow' : undefined,
  ogTitle: `${label.value} — AccessDevOps Blog`,
  ogUrl: url.value,
  ogType: 'website',
  ogImage: `${SITE}/og-image.png`,
  twitterCard: 'summary_large_image',
  twitterImage: `${SITE}/og-image.png`,
});

const jsonld = computed(() => ({
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'CollectionPage',
      name: `${label.value} — AccessDevOps Blog`,
      url: url.value,
      inLanguage: 'en',
      // Les articles de la page, dans l'ordre où ils sont rendus : c'est ce
      // qui permet à un moteur de comprendre la page comme un index plutôt
      // que comme un article de plus.
      mainEntity: {
        '@type': 'ItemList',
        itemListElement: posts.value!.map((p, i) => ({
          '@type': 'ListItem', position: i + 1, url: `${SITE}${p._path}`, name: p.title,
        })),
      },
    },
    {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: `${SITE}/` },
        { '@type': 'ListItem', position: 2, name: 'Topics', item: `${SITE}/tags` },
        { '@type': 'ListItem', position: 3, name: label.value, item: url.value },
      ],
    },
  ],
}));

useHead(() => ({
  link: [{ rel: 'canonical', href: url.value }],
  script: [{ type: 'application/ld+json', innerHTML: JSON.stringify(jsonld.value) }],
}));

const fmt = (d: string) => new Date(d).toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' });
</script>

<template>
  <section>
    <nav class="label" aria-label="Breadcrumb">
      <NuxtLink to="/" class="hover:text-foreground">Articles</NuxtLink>
      <span aria-hidden="true" class="mx-2 opacity-40">/</span>
      <NuxtLink to="/tags" class="hover:text-foreground">Topics</NuxtLink>
    </nav>
    <h1 class="display mt-4">{{ label }}</h1>
    <p class="lede mt-4 max-w-[58ch]">
      {{ posts!.length }} article{{ posts!.length > 1 ? 's' : '' }} on {{ label }}.
    </p>

    <ul class="mt-12">
      <li v-for="post in posts" :key="post._path">
        <NuxtLink :to="post._path" class="entry group grid grid-cols-[minmax(0,1fr)_auto] items-start gap-5">
          <div class="min-w-0">
            <div class="label flex flex-wrap items-center gap-x-3 gap-y-1">
              <time>{{ fmt(post.date) }}</time>
            </div>
            <h2 class="mt-2.5 text-[1.3rem] font-semibold leading-snug tracking-[-0.022em] decoration-1 underline-offset-[3px] group-hover:text-primary group-hover:underline">
              {{ post.title }}
            </h2>
            <p class="mt-2 max-w-[68ch] text-[15px] leading-relaxed text-muted-foreground">{{ post.description }}</p>
          </div>
          <span aria-hidden="true" class="mt-8 select-none text-lg text-muted-foreground transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-primary">→</span>
        </NuxtLink>
      </li>
    </ul>

    <section v-if="siblings.length" class="mt-2 border-t border-border pt-8">
      <h2 class="label">Other topics</h2>
      <ul class="mt-3 flex flex-wrap gap-2">
        <li v-for="s in siblings" :key="s.tag">
          <NuxtLink :to="tagPath(s.tag)" class="inline-block rounded-md border border-border px-2.5 py-1 text-sm text-muted-foreground hover:border-primary hover:text-foreground">
            {{ tagLabel(s.tag) }} <span class="opacity-50">{{ s.count }}</span>
          </NuxtLink>
        </li>
      </ul>
    </section>
  </section>
</template>
