<script setup lang="ts">
defineProps<{ error: any }>();
useSeoMeta({
  title: 'Page not found — AccessDevOps Blog',
  description: 'This page does not exist. Browse the AccessDevOps Blog for guides on S3, cloud and DevOps.',
  robots: 'noindex, follow',
});
</script>
<template>
  <div class="mx-auto max-w-3xl px-6 py-24">
    <p class="font-mono text-sm uppercase tracking-wider text-primary">{{ error?.statusCode || 404 }}</p>
    <h1 class="mt-4 font-serif text-4xl font-bold tracking-tight">Page not found.</h1>
    <p class="mt-4 max-w-[52ch] text-muted-foreground">
      That URL doesn't exist — it may have moved, or the link may be broken.
    </p>
    <a href="/" class="mt-8 inline-block font-medium text-primary hover:underline">← Back to all articles</a>
  </div>
</template>
