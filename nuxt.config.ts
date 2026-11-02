export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  modules: ['@nuxt/content', '@nuxtjs/sitemap', '@nuxtjs/tailwindcss'],
  site: { url: 'https://blog.accessdevops.com', name: 'AccessDevOps Blog' },
  css: ['~/assets/css/fonts.css', '~/assets/css/tailwind.css'],
  app: {
    head: {
      htmlAttrs: { lang: 'en', 'data-theme': 'light' },
      script: [
        {
          tagPosition: 'head',
          innerHTML:
            "try{if(localStorage.getItem('theme')==='dark')document.documentElement.dataset.theme='dark'}catch(e){}",
        },
      ],
      meta: [
        { name: 'theme-color', content: '#ffffff' },
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
        { rel: 'preload', as: 'font', type: 'font/woff2', href: '/fonts/Inter-400-latin.woff2', crossorigin: 'anonymous' },
        { rel: 'preload', as: 'font', type: 'font/woff2', href: '/fonts/Inter-600-latin.woff2', crossorigin: 'anonymous' },
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
        // Google exige un carré d'au moins 48 px : sans lui, il n'affiche
        // aucune icône dans les résultats, même si un SVG est présent.
        { rel: 'icon', type: 'image/png', sizes: '192x192', href: '/icon-192.png' },
        { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/favicon-32.png' },
        { rel: 'icon', sizes: 'any', href: '/favicon.ico' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' },
        { rel: 'manifest', href: '/site.webmanifest' },
        { rel: 'alternate', type: 'application/rss+xml', title: 'AccessDevOps Blog RSS', href: '/rss.xml' },
      ],
    },
  },
  content: {
    // variantes high-contrast : la palette github standard tombe à 3,2:1
    // sur certains tokens (gris des commentaires), sous le seuil AA.
    highlight: {
      theme: { default: 'github-light-high-contrast', dark: 'github-dark-high-contrast' },
    },
  },
  // Shiki ne charge que les grammaires déclarées : sans cette liste, python,
  // xml et bash tombent en texte brut et les blocs paraissent monochromes.
  mdc: {
    highlight: {
      langs: [
        'bash', 'shell', 'python', 'json', 'jsonc', 'xml', 'html', 'yaml',
        'javascript', 'typescript', 'tsx', 'sql', 'ini', 'toml', 'diff',
        'http', 'dockerfile', 'nginx', 'go', 'rust',
      ],
    },
  },
  nitro: {
    preset: 'netlify-static',
    prerender: { routes: ['/rss.xml'], autoSubfolderIndex: false },
  },
});
