export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  modules: ['@nuxt/content', '@nuxtjs/sitemap', '@nuxtjs/tailwindcss'],
  site: { url: 'https://blog.accessdevops.com', name: 'AccessDevOps Blog' },
  css: ['~/assets/css/tailwind.css'],
  app: {
    head: {
      htmlAttrs: { lang: 'en' },
      meta: [
        { name: 'theme-color', content: '#0B0F0E' },
        { name: 'author', content: 'Clement Baranger' },
        { name: 'robots', content: 'index, follow, max-image-preview:large' },
        { property: 'og:site_name', content: 'AccessDevOps Blog' },
        { property: 'og:locale', content: 'en_US' },
        { property: 'og:image', content: 'https://blog.accessdevops.com/og-image.png' },
        { property: 'og:image:width', content: '1200' },
        { property: 'og:image:height', content: '630' },
        { property: 'og:image:alt', content: 'AccessDevOps Blog — Field notes on S3, Cloud & DevOps' },
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:site', content: '@cbarange' },
        { name: 'twitter:creator', content: '@cbarange' },
        { name: 'twitter:image', content: 'https://blog.accessdevops.com/og-image.png' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
        { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/favicon-32.png' },
        { rel: 'icon', sizes: 'any', href: '/favicon.ico' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' },
        { rel: 'manifest', href: '/site.webmanifest' },
        { rel: 'alternate', type: 'application/rss+xml', title: 'AccessDevOps Blog RSS', href: '/rss.xml' },
      ],
    },
  },
  content: { highlight: { theme: 'github-light' } },
  nitro: {
    preset: 'netlify-static',
    prerender: { routes: ['/rss.xml'], autoSubfolderIndex: false },
  },
});
