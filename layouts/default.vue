<template>
  <div class="flex min-h-screen flex-col">
    <header class="sticky top-0 z-10 border-b border-border bg-background/85 backdrop-blur-md">
      <div class="mx-auto flex w-full max-w-[780px] items-center justify-between gap-6 px-6 py-4">
        <NuxtLink to="/" class="flex items-center gap-2 text-[15px] font-semibold tracking-tight">
          <span aria-hidden="true" class="inline-block h-[9px] w-[9px] rounded-[2px] bg-primary"></span>
          AccessDevOps<span class="font-normal text-muted-foreground">/blog</span>
        </NuxtLink>
        <nav class="flex items-center gap-5 text-sm text-muted-foreground">
          <NuxtLink to="/" class="hover:text-foreground">Articles</NuxtLink>
          <a href="https://s3explorer.accessdevops.com" class="hover:text-foreground">S3 Explorer</a>
          <a href="https://github.com/AccessDevOps" class="hover:text-foreground">GitHub</a>
        </nav>
      </div>
    </header>
    <main class="mx-auto w-full max-w-[780px] flex-1 px-6 py-16"><slot /></main>
    <footer class="border-t border-border">
      <div class="mx-auto flex w-full max-w-[780px] flex-wrap items-center justify-between gap-3 px-6 py-6">
        <span class="label">© {{ new Date().getFullYear() }} AccessDevOps</span>
        <span class="label">Cloud · DevOps · S3</span>
      </div>
    </footer>
  </div>
</template>
