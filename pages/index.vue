<script setup lang="ts">
import { productUrl } from '~/lib/product-link';
import { tagLabel, tagPath } from '~/lib/tags';
const { data: posts } = await useAsyncData('posts', () => queryContent('blog').sort({ date: -1 }).find());
const SITE = 'https://blog.accessdevops.com';
const productHome = productUrl('/', 'blog_home');
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
    logo: { '@type': 'ImageObject', url: `${SITE}/icon-512.png`, width: 512, height: 512 },
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
const words = (n: any): number => {
  if (!n) return 0;
  if (typeof n === 'string') return n.trim().split(/\s+/).filter(Boolean).length;
  if (Array.isArray(n)) return n.reduce((a: number, x: any) => a + words(x), 0);
  if (n.value) return words(n.value);
  if (n.children) return words(n.children);
  return 0;
};
const readTime = (post: any) => Math.max(1, Math.round(words(post.body) / 220));
</script>
<template>
  <section>
    <h1 class="display max-w-[22ch]">Field notes on S3, cloud and DevOps.</h1>
    <p class="lede mt-5 max-w-[58ch]">
      Request costs, egress cliffs, replication bills — measured, sourced and reproducible.
      Written by the team behind S3 Explorer.
    </p>

    <p class="mt-5 text-[15px]">
      <NuxtLink to="/tags" class="link">Browse by topic →</NuxtLink>
    </p>

    <ul class="mt-12">
      <li v-for="post in posts" :key="post._path">
        <NuxtLink :to="post._path" class="entry group grid grid-cols-[minmax(0,1fr)_auto] items-start gap-5">
          <div class="min-w-0">
            <div class="label flex flex-wrap items-center gap-x-3 gap-y-1">
              <time>{{ fmt(post.date) }}</time>
              <span aria-hidden="true" class="opacity-40">·</span>
              <span>{{ readTime(post) }} min read</span>
              <template v-if="post.tags?.length"><span aria-hidden="true" class="opacity-40">·</span><span>{{ post.tags.map(tagLabel).join(' · ') }}</span></template>
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

    <aside class="mt-2 flex flex-col gap-5 border-t border-border pt-8 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p class="text-[15px] font-semibold">S3 Explorer</p>
        <p class="mt-1 max-w-[46ch] text-sm leading-relaxed text-muted-foreground">
          The desktop S3 client these articles are tested with. Windows, macOS, Linux — with a per-request metrics view built in.
        </p>
      </div>
      <a :href="productHome" class="btn shrink-0">See S3 Explorer</a>
    </aside>
  </section>
</template>
