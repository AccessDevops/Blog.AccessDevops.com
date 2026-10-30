<script setup lang="ts">
defineProps<{ error: any }>();
useSeoMeta({
  title: 'Page not found — AccessDevOps Blog',
  description: 'This page does not exist. Browse the AccessDevOps Blog for guides on S3, cloud and DevOps.',
  robots: 'noindex, follow',
});
</script>
<template>
  <div class="mx-auto max-w-[780px] px-6 py-24">
    <p class="label">Error {{ error?.statusCode || 404 }}</p>
    <h1 class="display mt-4">Page not found.</h1>
    <p class="lede mt-4 max-w-[52ch]">That URL doesn't exist — it may have moved, or the link may be broken.</p>
    <a href="/" class="link mt-8 inline-block text-[15px]">← Back to all articles</a>
  </div>
</template>
