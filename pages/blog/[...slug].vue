<script setup lang="ts">
const route = useRoute();
const SITE = 'https://blog.accessdevops.com';
const { data: post } = await useAsyncData(`post-${route.path}`, () => queryContent(route.path).findOne());
if (!post.value) throw createError({ statusCode: 404, statusMessage: 'Post not found' });
const author = post.value.author || 'Clement Baranger';
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
    <footer class="mt-16 flex flex-wrap items-center justify-between gap-4 border-t border-border pt-6">
      <span class="label">{{ (post.tags || []).join(' · ') || 'untagged' }}</span>
      <NuxtLink to="/" class="link text-sm">← All articles</NuxtLink>
    </footer>
  </article>
</template>
