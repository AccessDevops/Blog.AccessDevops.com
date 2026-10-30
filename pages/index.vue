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
</script>
<template>
  <section>
    <h1 class="display max-w-[22ch]">Field notes on S3, cloud and DevOps.</h1>
    <p class="lede mt-5 max-w-[58ch]">
      The trade-offs, the gotchas and the numbers behind object storage — written by the team that builds
      S3 Explorer. No vendor spin, no 10× claims.
    </p>

    <ul class="mt-14">
      <li v-for="post in posts" :key="post._path">
        <NuxtLink :to="post._path" class="entry">
          <div class="label flex flex-wrap items-center gap-x-3 gap-y-1">
            <time>{{ fmt(post.date) }}</time>
            <template v-if="post.tags?.length"><span class="opacity-60">·</span><span>{{ post.tags.join(' · ') }}</span></template>
          </div>
          <h2 class="mt-2.5 text-[1.35rem] font-semibold leading-snug tracking-[-0.022em]">{{ post.title }}</h2>
          <p class="mt-2 max-w-[68ch] text-[15px] leading-relaxed text-muted-foreground">{{ post.description }}</p>
        </NuxtLink>
      </li>
    </ul>
  </section>
</template>
