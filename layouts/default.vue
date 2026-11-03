<script setup lang="ts">
import { productUrl } from '~/lib/product-link';

// Deux campagnes distinctes : un clic depuis la navigation n'a pas la même
// valeur qu'un clic depuis le pied de page d'un article lu en entier.
const productNav = productUrl('/', 'blog_nav');
const productFooter = productUrl('/', 'blog_footer');
</script>
<template>
  <div class="flex min-h-screen flex-col">
    <header class="sticky top-0 z-10 border-b border-border bg-background/90 backdrop-blur-md">
      <div class="mx-auto flex w-full max-w-[780px] items-center justify-between gap-6 px-6 py-4">
        <NuxtLink to="/" class="flex items-center gap-2 text-[15px] font-semibold tracking-tight">
          <span aria-hidden="true" class="inline-block h-[9px] w-[9px] rounded-[2px] bg-primary"></span>
          AccessDevOps<span class="font-normal text-muted-foreground">/blog</span>
        </NuxtLink>
        <nav class="flex items-center gap-4 text-sm">
          <NuxtLink to="/" class="text-muted-foreground hover:text-foreground" active-class="text-foreground font-medium" exact-active-class="text-foreground font-medium">Articles</NuxtLink>
          <a :href="productNav" class="text-muted-foreground hover:text-foreground">S3 Explorer</a>
          <a href="https://github.com/AccessDevOps" class="hidden text-muted-foreground hover:text-foreground sm:inline">GitHub</a>
          <ThemeToggle class="ml-1" />
        </nav>
      </div>
    </header>
    <main class="mx-auto w-full max-w-[780px] flex-1 px-6 py-14"><slot /></main>
    <footer class="border-t border-border">
      <div class="mx-auto flex w-full max-w-[780px] flex-col gap-4 px-6 py-8 sm:flex-row sm:items-center sm:justify-between">
        <nav class="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted-foreground">
          <NuxtLink to="/tags" class="hover:text-foreground">Topics</NuxtLink>
          <a href="/rss.xml" class="hover:text-foreground">RSS</a>
          <a href="https://github.com/AccessDevOps" class="hover:text-foreground">GitHub</a>
          <a :href="productFooter" class="hover:text-foreground">S3 Explorer</a>
          <a href="https://accessdevops.com" class="hover:text-foreground">accessdevops.com</a>
        </nav>
        <span class="label">© {{ new Date().getFullYear() }} AccessDevOps</span>
      </div>
    </footer>
  </div>
</template>
