# Main Street Exits website

Fast static site for mainstreetexits.net. No framework, no web fonts, no build dependencies beyond Python 3.

- `content/pages/*.html` - site pages (one file per page)
- `content/blog/*.html` - blog posts
- `static/` - CSS (inlined into every page at build time), favicon, Open Graph image
- `build.py` - builds everything into `docs/`, which GitHub Pages serves
- Settings (phone, email, booking calendar URL, buyer form id, HighLevel valuation form id, canonical domain) live in the CONFIG block at the top of `build.py`.

## Build

```
python3 build.py
```

Then commit and push, including the `docs/` folder. GitHub Pages publishes from `main` / `docs`.

Preview locally: `cd docs && python3 -m http.server 8088` then open http://localhost:8088/

## Add a blog post

1. Create `content/blog/YYYY-MM-DD-your-post-slug.html`. The URL becomes `/blog/your-post-slug/`.
2. Start the file with front matter, then a line with only `---`, then the post body in HTML:

```
title: Page title for Google (about 60 characters) | Main Street Exits
h1: The headline shown on the page
description: One or two sentences for Google and social previews (about 155 characters).
date: 2026-11-02
---
<p>First paragraph...</p>
<h2>A section</h2>
<p>Link to another page like this: <a href="{{root}}business-valuation/">free valuation</a>.</p>
```

3. Run `python3 build.py`. The post is added to the blog index, the home page "From the blog" list, the sitemap, and gets BlogPosting schema and the standard call-to-action box automatically.

Optional front matter: `slug:` (override the URL), `updated:` (YYYY-MM-DD, used for dateModified and the sitemap).

Writing rules: plain language, no em dashes, no invented stats, testimonials or deal counts. Any market number needs a linked source (IBBA Market Pulse, BizBuySell Insight Report). Never quote a fixed fee; say fees are typically 5-10% of the sale price and depend on the size and price of the business.

## Placeholders available in content

Buyer deal-alert form: `BUYER_FORM_ID` / `BUYER_FORM_HEIGHT` in build.py (embedded on /buyers/).

`{{root}}` relative link to site root, `{{booking}}` booking calendar (falls back to the Contact page), `{{valuation_url}}`, `{{form}}` embedded HighLevel valuation form, `{{buyer_cta}}`, `{{email}}`, `{{phone}}`, `{{tel}}`.

## IndexNow

The key file `static/<key>.txt` (key also in `.indexnow-key`) lets you notify Bing and other IndexNow engines of new URLs:

```
curl -s -H "Content-Type: application/json" https://api.indexnow.org/indexnow -d '{"host":"mainstreetexits.net","key":"KEY","keyLocation":"https://mainstreetexits.net/KEY.txt","urlList":["https://mainstreetexits.net/blog/new-post/"]}'
```

Google no longer accepts sitemap pings. Submit the sitemap in Search Console instead.

## Chat widget

The HighLevel chat widget (`CHAT_WIDGET_ID` in build.py) is added to every page. It loads after the first scroll, tap, key press or mouse move, or about 4 seconds after page load, so it does not slow the page or shift layout.

## FAQ schema

Any `<details class="faq"><summary>Question</summary><div>Answer</div></details>` block on a page is automatically added to FAQPage structured data.

## Going live on mainstreetexits.net

1. Custom domain is set (`CUSTOM_DOMAIN` in build.py writes `docs/CNAME` on every build, so rebuilds never drop it). HTTPS is enforced in Settings > Pages.
2. DNS for the apex: A records to 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153 (optional AAAA: 2606:50c0:8000::153, 2606:50c0:8001::153, 2606:50c0:8002::153, 2606:50c0:8003::153).
3. DNS for www: CNAME `www` -> `growthorgrowth-cyber.github.io`.
4. Leave `valuation.mainstreetexits.net` pointed at HighLevel.
