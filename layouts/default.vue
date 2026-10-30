<template>
  <div class="flex min-h-screen flex-col">
    <header class="border-b border-border">
      <div class="mx-auto flex w-full max-w-prose items-baseline justify-between gap-4 px-6 py-6">
        <NuxtLink to="/" class="font-serif text-xl font-bold tracking-tight">AccessDevOps <span class="font-normal text-muted-foreground">· Blog</span></NuxtLink>
        <nav class="flex gap-6 text-[15px] text-muted-foreground">
          <NuxtLink to="/" class="hover:text-foreground">Articles</NuxtLink>
          <a href="https://s3explorer.accessdevops.com" class="hover:text-foreground">S3 Explorer</a>
          <a href="https://github.com/AccessDevOps" class="hover:text-foreground">GitHub</a>
        </nav>
      </div>
    </header>
    <main class="mx-auto w-full max-w-prose flex-1 px-6 py-20"><slot /></main>
    <footer class="border-t border-border">
      <div class="mx-auto flex w-full max-w-prose flex-wrap justify-between gap-4 px-6 py-7 text-sm text-muted-foreground">
        <span>© {{ new Date().getFullYear() }} AccessDevOps</span>
        <span>Cloud · DevOps · S3</span>
      </div>
    </footer>
  </div>
</template>
