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
  ],
};
useHead({
  link: [{ rel: 'canonical', href: url }],
  script: [{ type: 'application/ld+json', innerHTML: JSON.stringify(jsonld) }],
});
</script>
<template>
  <article v-if="post">
    <header class="mb-10">
      <div class="font-mono text-[13px] uppercase tracking-wider text-muted-foreground">{{ post.date }} · {{ post.author }}</div>
      <h1 class="mt-3 font-serif text-4xl font-bold tracking-tight">{{ post.title }}</h1>
    </header>
    <ContentRenderer :value="post" class="prose prose-stone max-w-none dark:prose-invert prose-headings:font-serif prose-headings:tracking-tight prose-a:text-primary" />
    <footer class="mt-14 flex flex-wrap justify-between gap-4 border-t border-border pt-6 text-sm text-muted-foreground">
      <span>Tags: {{ (post.tags || []).join(', ') || 'none' }}</span>
      <NuxtLink to="/" class="text-primary hover:underline">← All articles</NuxtLink>
    </footer>
  </article>
</template>
