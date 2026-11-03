// IndexNow ping after every production deploy.
//
// Bing and DuckDuckGo (same index) read IndexNow: instead of waiting for the
// next crawl, they are told which URLs exist the moment the deploy is live.
// Google ignores IndexNow, so this changes nothing there. Bing's index is also
// what feeds ChatGPT Search and Copilot, which is the part that matters here —
// the product site already receives visits referred by ChatGPT.
//
// Runs on onSuccess, not in the build command: scripts/indexnow.mjs checks
// each URL answers 200 before submitting, and during the build the new
// article is not deployed yet — it would be the one URL skipped every time.
//
// The key is public by design: IndexNow verifies ownership by fetching
// https://<host>/<key>.txt, which is public/<key>.txt. Rotating it means
// renaming that file and changing KEY below.
//
// The URL list is the live sitemap, so it is always exactly what the sitemap
// advertises. Errors are logged, never thrown: a failed ping must not fail a
// deploy that already succeeded.

const HOST = 'blog.accessdevops.com'
const KEY = '3bc0fd29ef9f041964f1652be6f42a7d'

async function sitemapUrls(url, depth = 0) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url} answered ${res.status}`)
  const locs = [...(await res.text()).matchAll(/<loc>\s*([^<\s]+)\s*<\/loc>/g)].map(m => m[1])
  // @nuxtjs/sitemap may answer with a sitemap index pointing at child sitemaps.
  if (depth === 0 && locs.every(l => l.endsWith('.xml'))) {
    return (await Promise.all(locs.map(l => sitemapUrls(l, 1)))).flat()
  }
  return locs.filter(l => !l.endsWith('.xml'))
}

export const onSuccess = async () => {
  if (process.env.CONTEXT !== 'production') {
    console.log(`[indexnow] skipped: context is ${process.env.CONTEXT}`)
    return
  }
  try {
    const urlList = [...new Set(await sitemapUrls(`https://${HOST}/sitemap.xml`))]
    const res = await fetch('https://api.indexnow.org/indexnow', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify({ host: HOST, key: KEY, keyLocation: `https://${HOST}/${KEY}.txt`, urlList }),
    })
    console.log(`[indexnow] ${urlList.length} URLs submitted, answer ${res.status}`)
  } catch (err) {
    console.log(`[indexnow] not submitted: ${err.message}`)
  }
}
