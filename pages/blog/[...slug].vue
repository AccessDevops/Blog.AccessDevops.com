<script setup lang="ts">
const route = useRoute();
const { data: post } = await useAsyncData(`post-${route.path}`, () => queryContent(route.path).findOne());
if (!post.value) throw createError({ statusCode: 404, statusMessage: 'Post not found' });
useSeoMeta({ title: `${post.value.title} — AccessDevOps Blog`, description: post.value.description, ogType: 'article' });
const jsonld = {
  '@context': 'https://schema.org', '@type': 'BlogPosting',
  headline: post.value.title, description: post.value.description, datePublished: post.value.date,
  author: { '@type': 'Person', name: post.value.author || 'Clement Baranger', url: 'https://cbarange.com' },
  publisher: { '@type': 'Organization', name: 'AccessDevOps', url: 'https://accessdevops.com' },
};
useHead({ script: [{ type: 'application/ld+json', innerHTML: JSON.stringify(jsonld) }] });
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
