<script setup lang="ts">
const { data: posts } = await useAsyncData('posts', () => queryContent('blog').sort({ date: -1 }).find());
const SITE = 'https://blog.accessdevops.com';
useSeoMeta({
  title: 'AccessDevOps Blog — S3, Cloud & DevOps Guides',
  description: 'Field notes on cloud infrastructure, DevOps and S3-compatible object storage — practical guides for engineers.',
  ogTitle: 'AccessDevOps Blog — S3, Cloud & DevOps Guides',
  ogDescription: 'Practical guides for engineers running object storage at scale.',
  ogImage: `${SITE}/og-image.png`,
  ogUrl: `${SITE}/`,
  ogType: 'website',
  twitterCard: 'summary_large_image',
  twitterImage: `${SITE}/og-image.png`,
});
const siteLd = {
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  name: 'AccessDevOps Blog',
  url: `${SITE}/`,
  inLanguage: 'en',
  publisher: {
    '@type': 'Organization',
    name: 'AccessDevOps',
    url: 'https://accessdevops.com',
    sameAs: ['https://cbarange.com', 'https://s3explorer.accessdevops.com'],
  },
};
useHead({
  link: [
    { rel: 'canonical', href: `${SITE}/` },
    { rel: 'alternate', type: 'application/rss+xml', title: 'AccessDevOps Blog RSS', href: `${SITE}/rss.xml` },
  ],
  script: [{ type: 'application/ld+json', innerHTML: JSON.stringify(siteLd) }],
});
const fmt = (d: string) => new Date(d).toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' });
</script>
<template>
  <section>
    <h1 class="mb-3 font-serif text-4xl font-bold tracking-tight">Notes on cloud, DevOps and object storage.</h1>
    <p class="mb-14 max-w-[58ch] text-lg text-muted-foreground">Field notes on infrastructure, automation and S3 — the trade-offs, the gotchas, and the small wins that save hours. Written by the team behind AccessDevOps and S3 Explorer.</p>
    <ul class="border-t border-border">
      <li v-for="post in posts" :key="post._path" class="border-b border-border">
        <NuxtLink :to="post._path" class="group block py-8">
          <div class="font-mono text-[13px] uppercase tracking-wider text-muted-foreground">{{ fmt(post.date) }}<span v-if="post.tags?.length"> · {{ post.tags.join(' · ') }}</span></div>
          <h2 class="mt-2 font-serif text-2xl font-bold group-hover:text-primary">{{ post.title }}</h2>
          <p class="mt-2 text-muted-foreground">{{ post.description }}</p>
        </NuxtLink>
      </li>
    </ul>
  </section>
</template>
