export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  modules: ['@nuxt/content', '@nuxtjs/sitemap', '@nuxtjs/tailwindcss'],
  site: { url: 'https://blog.accessdevops.com', name: 'AccessDevOps Blog' },
  css: ['~/assets/css/tailwind.css'],
  app: { head: { htmlAttrs: { lang: 'en' } } },
  content: { highlight: { theme: 'github-light' } },
});
