<script setup lang="ts">
import { tagLabel, tagPath, indexableTags, countTags } from '~/lib/tags';

const SITE = 'https://blog.accessdevops.com';
const { data: posts } = await useAsyncData('tags-index', () =>
  queryContent('/blog').only(['tags']).find(),
);

const indexable = computed(() => indexableTags((posts.value ?? []) as any[]));
// Les tags sous le seuil sont listés aussi : la page les relie, c'est son
// rôle de carrefour. Ce sont leurs propres pages qui portent le noindex.
const rest = computed(() => {
  const keep = new Set(indexable.value.map(t => t.tag));
  return [...countTags((posts.value ?? []) as any[]).entries()]
    .filter(([t]) => !keep.has(t))
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => a.tag.localeCompare(b.tag));
});

useSeoMeta({
  title: 'Topics — AccessDevOps Blog',
  description: 'Every subject covered on the AccessDevOps blog: S3 access control, presigned URLs, IAM, storage pricing and the tooling around them.',
  ogTitle: 'Topics — AccessDevOps Blog',
  ogUrl: `${SITE}/tags`,
  ogType: 'website',
  ogImage: `${SITE}/og-image.png`,
  twitterCard: 'summary_large_image',
  twitterImage: `${SITE}/og-image.png`,
});
useHead({ link: [{ rel: 'canonical', href: `${SITE}/tags` }] });
</script>

<template>
  <section>
    <nav class="label" aria-label="Breadcrumb">
      <NuxtLink to="/" class="hover:text-foreground">Articles</NuxtLink>
    </nav>
    <h1 class="display mt-4">Topics</h1>
    <p class="lede mt-4 max-w-[58ch]">Every subject the blog covers, by how much has been written about it.</p>

    <ul class="mt-12 divide-y divide-border border-y border-border">
      <li v-for="t in indexable" :key="t.tag">
        <NuxtLink :to="tagPath(t.tag)" class="group flex items-baseline justify-between gap-5 py-4">
          <span class="font-medium underline-offset-4 group-hover:underline group-hover:text-primary">{{ tagLabel(t.tag) }}</span>
          <span class="label shrink-0">{{ t.count }} articles</span>
        </NuxtLink>
      </li>
    </ul>

    <section v-if="rest.length" class="mt-10">
      <h2 class="label">Also mentioned</h2>
      <ul class="mt-3 flex flex-wrap gap-2">
        <li v-for="t in rest" :key="t.tag">
          <NuxtLink :to="tagPath(t.tag)" class="inline-block rounded-md border border-border px-2.5 py-1 text-sm text-muted-foreground hover:border-primary hover:text-foreground">
            {{ tagLabel(t.tag) }}
          </NuxtLink>
        </li>
      </ul>
    </section>
  </section>
</template>
