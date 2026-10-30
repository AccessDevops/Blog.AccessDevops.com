import { serverQueryContent } from '#content/server'

const SITE = 'https://blog.accessdevops.com'

const esc = (s: any) =>
  String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

export default defineEventHandler(async (event) => {
  const docs = await serverQueryContent(event).sort({ date: -1 }).find()
  const posts = docs.filter((d: any) => d._path?.startsWith('/blog/'))
  const items = posts
    .map(
      (d: any) => `    <item>
      <title>${esc(d.title)}</title>
      <link>${SITE}${d._path}</link>
      <guid isPermaLink="true">${SITE}${d._path}</guid>
      <pubDate>${new Date(d.date).toUTCString()}</pubDate>
      <description>${esc(d.description)}</description>
    </item>`,
    )
    .join('\n')

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>AccessDevOps Blog</title>
    <link>${SITE}/</link>
    <atom:link href="${SITE}/rss.xml" rel="self" type="application/rss+xml" />
    <description>Field notes on S3, Cloud &amp; DevOps.</description>
    <language>en</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
${items}
  </channel>
</rss>`

  setHeader(event, 'Content-Type', 'application/rss+xml; charset=utf-8')
  return xml
})
