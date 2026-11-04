#!/usr/bin/env python3
"""Static site builder for Main Street Exits.

Usage:  python3 build.py
Output: docs/  (served by GitHub Pages from main branch /docs)

Content lives in content/pages/*.html and content/blog/*.html.
Each file starts with a front matter block ("key: value" lines) ended by a line "---".
"""
import html, json, os, re, shutil, datetime

# ---------------------------------------------------------------------------
# CONFIG: the only place you should need to edit settings
# ---------------------------------------------------------------------------
SITE_URL = "https://mainstreetexits.net"          # canonical domain (no trailing slash)
CUSTOM_DOMAIN = "mainstreetexits.net"             # written to docs/CNAME on every build (GitHub Pages custom domain)
BRAND = "Main Street Exits"
# Florida compliance (FAC 61J2-10.025 / 10.026): Main Street Exits is a TEAM name, never a
# brokerage. The brokerage's licensed name must appear with it, in equal or larger type.
BROKERAGE = "Infinity Business Brokers"
BROKERAGE_LEGAL = "IBB Business Brokers LLC d/b/a Infinity Business Brokers"
BROKERAGE_LICENSE = "CQ1045706"
BROKERAGE_URL = "https://www.infinitybusinessbrokers.com/"
AGENT_NAME = "Eric Camehl"
AGENT_TITLE = "Licensed Real Estate Broker Associate"
AGENT_LICENSE = "BK3294556"
BROKER_LINE = f"{AGENT_NAME}, {AGENT_TITLE} ({AGENT_LICENSE}), {BROKERAGE}"
TEAM_LINE = f"{BRAND}, a team at {BROKERAGE}"
DISCLOSURE = (f"{BRAND} is a team of {BROKERAGE_LEGAL}, a licensed Florida real estate brokerage "
              f"(License {BROKERAGE_LICENSE}). {AGENT_NAME}, {AGENT_TITLE} ({AGENT_LICENSE}). "
              f"All brokerage services are provided through {BROKERAGE}.")
# TCPA / Florida FTSA notice shown under every form or calendar that collects a phone number.
CONSENT_NOTE = (f"By submitting, you agree that {BRAND} at {BROKERAGE} may contact you by phone, email and text "
                "message at the number and email you provide about your inquiry. Texts are sent only if you check a "
                "consent box, and marketing texts only if you check the marketing box. Calls and texts may be sent "
                "using automated technology. Consent is not a condition of any purchase or service. Message frequency "
                "varies. Message and data rates may apply. Reply STOP to opt out at any time, or HELP for help.")
EMAIL = "eric@mainstreetexits.net"
PHONE_DISPLAY = "(877) 450-8756"
PHONE_TEL = "+18774508756"
VALUATION_URL = "https://valuation.mainstreetexits.net/"
VALUATION_FORM_ID = "oZxKhFmfiqPgMGftSxwq"         # HighLevel Form 12
FORM_EMBED_HOST = "https://api.leadconnectorhq.com/widget/form/"
FORM_EMBED_SCRIPT = "https://link.msgsndr.com/js/form_embed.js"
# Exit Strategy Call calendar (HighLevel booking widget). Embedded on /book/;
# every "Book a confidential call" button points to /book/.
BOOKING_URL = "https://api.leadconnectorhq.com/widget/bookings/exit-strategy-call"
# HighLevel buyer deal-alert form id. Leave "" until supplied; the Buyers page
# falls back to an email link.
BUYER_FORM_ID = "rJQzQTYBqOylScYpOLng"   # MSE Buyer Deal Alerts
BUYER_FORM_HEIGHT = 1600
# HighLevel chat widget. Injected after first interaction or ~4s idle so it does
# not affect load speed or layout. Set CHAT_WIDGET_ID = "" to remove it.
CHAT_WIDGET_ID = "6adce84e912bacec15741935"
CHAT_LOADER = "https://widgets.leadconnectorhq.com/loader.js"
CHAT_RESOURCES = "https://widgets.leadconnectorhq.com/chat-widget/loader.js"
# ---------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "docs")
NAV = [("sell-my-business/", "Sell"), ("exit-planning/", "Exit Planning"),
       ("business-valuation/", "Valuation"), ("how-we-protect-you/", "How We Protect You"),
       ("buyers/", "Buyers"), ("blog/", "Blog"), ("about/", "About"), ("contact/", "Contact")]


def read_doc(path):
    raw = open(path, encoding="utf-8").read()
    head, body = raw.split("\n---\n", 1)
    meta = {}
    for line in head.strip().splitlines():
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
    return meta, body


def booking_href(root):
    return root + "book/" if BOOKING_URL else root + "contact/#book"


def booking_embed(height=900):
    """HighLevel calendar embed with LeadConnector form_embed.js (auto-resizes the iframe).
    Container has a fixed minimum height so the page does not jump while it loads."""
    if not BOOKING_URL:
        return f'<p>Call {TEAM_LINE}, at <a href="tel:{PHONE_TEL}">{PHONE_DISPLAY}</a> or email <a href="mailto:{EMAIL}">{EMAIL}</a> to set a time.</p>'
    return (f'<div class="formbox" style="min-height:{height}px"><iframe src="{BOOKING_URL}" '
            f'style="width:100%;height:{height}px;border:none;overflow:hidden" scrolling="no" '
            f'id="exit-strategy-call_booking" title="Book a confidential Exit Strategy Call"></iframe></div>'
            f'<script src="{FORM_EMBED_SCRIPT}" defer></script>'
            f'{consent_html()}'
            f'<p class="small">Trouble with the calendar? Call {TEAM_LINE}, at <a href="tel:{PHONE_TEL}">{PHONE_DISPLAY}</a> or email '
            f'<a href="mailto:{EMAIL}">{EMAIL}</a>.</p>')


def consent_html():
    return (f'<p class="small consent">{CONSENT_NOTE} See our <a href="{SITE_URL}/privacy-policy/">Privacy Policy</a> '
            f'and <a href="{SITE_URL}/terms/#sms">SMS Terms</a>.</p>')


def lazy_form(fid, title, height, box_id, anchor):
    """HighLevel form embed (api.leadconnectorhq.com). The iframe is injected when the visitor
    scrolls near it, keeping third-party cookies/JS off the initial load; the box has a fixed
    height so the page never shifts."""
    src = FORM_EMBED_HOST + fid
    iframe = (f'<iframe src="{src}" id="inline-{fid}" title="{title}" '
              f'style="width:100%;height:{height}px;border:none;border-radius:6px" '
              f'data-height="{height}" data-layout-iframe-id="inline-{fid}" data-form-id="{fid}"></iframe>')
    js = ("<script>(function(){var b=document.getElementById('" + box_id + "');function go(){if(b.dataset.on)return;"
          "b.dataset.on=1;b.innerHTML=b.dataset.html;}"
          "if('IntersectionObserver'in window){new IntersectionObserver(function(e,o){if(e[0].isIntersecting){go();o.disconnect();}},"
          "{rootMargin:'300px'}).observe(b);}else{go();}"
          "document.querySelectorAll('a[href=\"#" + anchor + "\"]').forEach(function(a){a.addEventListener('click',go);});})();</script>")
    return (f'<div class="formbox" id="{box_id}" style="height:{height + 14}px" data-html="{html.escape(iframe)}">'
            f'<noscript>{iframe}</noscript><p class="small" style="padding:12px">Loading the secure form. '
            f'If it does not appear, <a href="{src}">open it here</a>.</p></div>{js}')


def form_embed(height=1400):
    return (lazy_form(VALUATION_FORM_ID, "Free confidential business valuation form", height, "vform", "valuation-form")
            + consent_html()
            + f'<p class="small">Prefer not to use the form? Contact {TEAM_LINE}: email <a href="mailto:{EMAIL}">{EMAIL}</a> or call '
            f'<a href="tel:{PHONE_TEL}">{PHONE_DISPLAY}</a>.</p>')


def buyer_cta(height=BUYER_FORM_HEIGHT):
    if BUYER_FORM_ID:
        return (lazy_form(BUYER_FORM_ID, "Buyer deal alerts signup", height, "bform", "deal-alerts")
                + consent_html()
                + f'<p class="small">Questions first? Contact {TEAM_LINE}: email <a href="mailto:{EMAIL}">{EMAIL}</a> or call '
                f'<a href="tel:{PHONE_TEL}">{PHONE_DISPLAY}</a>.</p>')
    subj = "Buyer%20deal%20alerts"
    body = ("Name%3A%0APhone%3A%0AIndustries%20I%20want%3A%0AStates%20or%20regions%3A%0A"
            "Price%20range%3A%0ACash%20available%20to%20invest%3A%0AUsing%20SBA%20financing%3F%3A")
    return (f'<p><a class="btn" href="mailto:{EMAIL}?subject={subj}&amp;body={body}">Email me to get deal alerts</a></p>'
            f'<p class="small">Tell me the industries, locations, price range and cash you have to invest. '
            f'You will hear from me directly at <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>')


def faq_schema(body):
    items = re.findall(r'<details class="faq"><summary>(.*?)</summary>(.*?)</details>', body, re.S)
    if not items:
        return None
    def clean(s):
        return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": clean(q),
                            "acceptedAnswer": {"@type": "Answer", "text": clean(a)}} for q, a in items]}


def org_schema():
    """Brokerage is the business entity. Main Street Exits is a team (sub-organization) of it."""
    brokerage = {"@type": "RealEstateAgent", "@id": SITE_URL + "/#brokerage", "name": BROKERAGE,
                 "legalName": "IBB Business Brokers LLC", "url": BROKERAGE_URL,
                 "address": {"@type": "PostalAddress", "addressLocality": "Lakewood Ranch", "addressRegion": "FL",
                             "addressCountry": "US"},
                 "hasCredential": {"@type": "EducationalOccupationalCredential", "credentialCategory": "license",
                                   "name": f"Florida real estate brokerage license {BROKERAGE_LICENSE}",
                                   "recognizedBy": {"@type": "GovernmentOrganization",
                                                    "name": "Florida Department of Business and Professional Regulation"}}}
    team = {"@type": "Organization", "@id": SITE_URL + "/#team", "name": f"{BRAND} at {BROKERAGE}",
            "alternateName": BRAND, "url": SITE_URL + "/", "email": EMAIL, "telephone": PHONE_TEL,
            "image": SITE_URL + "/og.png", "logo": SITE_URL + "/favicon-512.png",
            "description": f"{BRAND} is a team of {BROKERAGE_LEGAL}, a licensed Florida real estate brokerage "
                           f"(License {BROKERAGE_LICENSE}). All brokerage services are provided through {BROKERAGE}.",
            "parentOrganization": {"@id": SITE_URL + "/#brokerage"}}
    person = {"@type": "Person", "@id": SITE_URL + "/#eric", "name": AGENT_NAME, "jobTitle": AGENT_TITLE,
              "url": SITE_URL + "/about/", "worksFor": {"@id": SITE_URL + "/#brokerage"},
              "memberOf": {"@id": SITE_URL + "/#team"},
              "hasCredential": {"@type": "EducationalOccupationalCredential", "credentialCategory": "license",
                                "name": f"Florida real estate broker associate license {AGENT_LICENSE}"}}
    return {"@context": "https://schema.org", "@graph": [brokerage, team, person]}


def brand_title(t):
    """Every page title carries the brokerage name next to the team name."""
    t = t.replace("| Main Street Exits", f"| {BRAND} at {BROKERAGE}")
    if BROKERAGE not in t:
        t = f"{t} | {BRAND} at {BROKERAGE}"
    return t


def add_brokerage_notes(body):
    """Put the brokerage name right after every paragraph of CTA buttons (phone, email, booking)."""
    note = f'<p class="small brk">{TEAM_LINE}. {AGENT_NAME}, {AGENT_TITLE}.</p>'
    return re.sub(r'(<p>(?:(?!</p>).)*class="btn(?:(?!</p>).)*</p>)', lambda m: m.group(1) + note, body, flags=re.S)


def chat_snippet():
    if not CHAT_WIDGET_ID:
        return ""
    return ("<script>(function(){var done=false,ev=['scroll','pointerdown','keydown','touchstart','mousemove'];"
            "function load(){if(done)return;done=true;ev.forEach(function(e){removeEventListener(e,load,{passive:true});});"
            "var s=document.createElement('script');s.src='" + CHAT_LOADER + "';"
            "s.setAttribute('data-resources-url','" + CHAT_RESOURCES + "');"
            "s.setAttribute('data-widget-id','" + CHAT_WIDGET_ID + "');s.async=true;document.body.appendChild(s);}"
            "ev.forEach(function(e){addEventListener(e,load,{passive:true,once:true});});"
            "function idle(){setTimeout(load,4000);}"
            "if(document.readyState==='complete'){idle();}else{addEventListener('load',idle);}})();</script>")


def render(meta, body, url_path, depth, extra_schema=None):
    root = "../" * depth if depth else "./"
    body = (body.replace("{{root}}", root).replace("{{booking}}", booking_href(root))
                .replace("{{valuation_url}}", VALUATION_URL).replace("{{form}}", form_embed())
                .replace("{{buyer_cta}}", buyer_cta()).replace("{{booking_embed}}", booking_embed()).replace("{{email}}", EMAIL)
                .replace("{{phone}}", PHONE_DISPLAY).replace("{{tel}}", PHONE_TEL))
    body = add_brokerage_notes(body)
    canonical = SITE_URL + "/" + url_path
    schemas = [org_schema()]
    fs = faq_schema(body)
    if fs:
        schemas.append(fs)
    if extra_schema:
        schemas.append(extra_schema)
    ld = "".join(f'<script type="application/ld+json">{json.dumps(s, separators=(",", ":"))}</script>' for s in schemas)
    title = html.escape(brand_title(meta["title"]))
    desc = html.escape(meta["description"])
    nav = "".join(f'<a href="{root}{p}"{" aria-current=\"page\"" if url_path.startswith(p) else ""}>{n}</a>' for p, n in NAV)
    css = open(os.path.join(ROOT, "static", "site.css"), encoding="utf-8").read()
    noindex = '<meta name="robots" content="noindex">' if meta.get("noindex") else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{desc}">{noindex}
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="{meta.get('ogtype','website')}"><meta property="og:site_name" content="{BRAND} at {BROKERAGE}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}"><meta property="og:image" content="{SITE_URL}/{meta.get('image','og.png')}?v=20261104">
<meta property="og:image:alt" content="{html.escape(meta.get('image_alt','Main Street Exits, a team at Infinity Business Brokers: value it, prepare it, sell it, confidentially'))}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{root}favicon.svg" type="image/svg+xml"><link rel="icon" href="{root}favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="{root}apple-touch-icon.png"><meta name="theme-color" content="#14324f">
<style>{css}</style>{ld}</head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="wrap bar"><a class="brand" href="{root}" aria-label="{BRAND}, a team at {BROKERAGE}"><span class="logo">Main Street <span>Exits</span></span><span class="sep" aria-hidden="true">|</span><span class="bkr"><span class="bkr-pre">Team at</span> {BROKERAGE}</span></a>
<span class="tel-wrap"><a class="tel" href="tel:{PHONE_TEL}">{PHONE_DISPLAY}</a><span class="tel-bk">{BROKERAGE}</span></span></div>
<nav class="wrap nav" aria-label="Main">{nav}</nav></header>
<main id="main">{body}</main>
<footer class="foot"><div class="wrap">
<p><strong>{BRAND}</strong> | <strong>a team at {BROKERAGE}</strong><br>{BROKER_LINE}<br>
<a href="mailto:{EMAIL}">{EMAIL}</a> | <a href="tel:{PHONE_TEL}">{PHONE_DISPLAY}</a> | {BROKERAGE}</p>
<p class="links"><a href="{root}faq/">FAQ</a> <a href="{root}blog/">Blog</a> <a href="{root}privacy-policy/">Privacy Policy</a> <a href="{root}terms/">Terms of Use</a> <a href="{VALUATION_URL}">Free Valuation</a></p>
<p class="disclosure">{DISCLOSURE}</p>
<p class="small">Results not guaranteed. Valuations are estimates based on current market data and do not guarantee a sale price or timeline. Submitting a form or contacting us does not establish a brokerage relationship. A brokerage relationship exists only under a signed written agreement with {BROKERAGE}. Florida license information can be verified at <a href="https://www.myfloridalicense.com/">myfloridalicense.com</a>. &copy; {datetime.date.today().year} {BRAND} | {BROKERAGE_LEGAL}.</p>
</div></footer>{chat_snippet()}</body></html>"""


def write(url_path, page):
    d = os.path.join(OUT, url_path)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    for f in os.listdir(os.path.join(ROOT, "static")):
        src = os.path.join(ROOT, "static", f)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(OUT, f))
        elif f != "site.css":
            shutil.copy(src, OUT)
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    if CUSTOM_DOMAIN:
        open(os.path.join(OUT, "CNAME"), "w").write(CUSTOM_DOMAIN + "\n")
    urls = []

    # Blog posts
    posts = []
    bdir = os.path.join(ROOT, "content", "blog")
    for f in sorted(os.listdir(bdir)):
        if not f.endswith(".html"):
            continue
        meta, body = read_doc(os.path.join(bdir, f))
        slug = meta.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", f[:-5])
        meta["slug"] = slug
        meta["words"] = str(len(re.sub(r"<[^>]+>", " ", body).split()))
        posts.append((meta, body))
    posts.sort(key=lambda p: (p[0]["date"], p[0]["title"]), reverse=True)
    for meta, body in posts:
        url = f"blog/{meta['slug']}/"
        d = datetime.date.fromisoformat(meta["date"])
        art = (f'<article class="wrap post"><p class="crumb"><a href="{{{{root}}}}blog/">Blog</a></p>'
               f'<h1>{meta["h1"]}</h1><p class="meta">By {AGENT_NAME}, {AGENT_TITLE}, {BROKERAGE} | <time datetime="{meta["date"]}">{d.strftime("%B %-d, %Y")}</time></p>'
               f'{body}<aside class="cta"><h2>Want a straight answer on your business?</h2>'
               f'<p>Get a free, confidential valuation or talk it through on a private call.</p>'
               f'<p><a class="btn" href="{{{{valuation_url}}}}">Get my free valuation</a> '
               f'<a class="btn alt" href="{{{{booking}}}}">Book a confidential call</a></p></aside></article>')
        schema = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": meta["h1"],
                  "description": meta["description"], "datePublished": meta["date"],
                  "dateModified": meta.get("updated", meta["date"]),
                  "author": {"@type": "Person", "name": AGENT_NAME, "jobTitle": AGENT_TITLE, "worksFor": {"@type": "RealEstateAgent", "name": BROKERAGE}},
                  "publisher": {"@type": "RealEstateAgent", "name": BROKERAGE, "legalName": "IBB Business Brokers LLC", "url": BROKERAGE_URL},
                  "mainEntityOfPage": SITE_URL + "/" + url, "image": SITE_URL + "/" + meta.get("image", "og.png"),
                  "url": SITE_URL + "/" + url}
        schema["author"]["url"] = SITE_URL + "/about/"
        if meta.get("keywords"):
            schema["keywords"] = meta["keywords"]
        if meta.get("words"):
            schema["wordCount"] = int(meta["words"])
        meta["ogtype"] = "article"
        write(url, render(meta, art, url, 2, schema))
        urls.append((url, meta.get("updated", meta["date"])))

    cards = "".join(f'<li class="card"><h2><a href="{{{{root}}}}blog/{m["slug"]}/">{m["h1"]}</a></h2>'
                    f'<p class="meta">{datetime.date.fromisoformat(m["date"]).strftime("%B %-d, %Y")}</p><p>{m["description"]}</p></li>'
                    for m, _ in posts)
    latest = "".join(f'<li><a href="{{{{root}}}}blog/{m["slug"]}/">{m["h1"]}</a></li>' for m, _ in posts[:3])

    # Pages
    pdir = os.path.join(ROOT, "content", "pages")
    today = datetime.date.today().isoformat()
    for f in sorted(os.listdir(pdir)):
        if not f.endswith(".html"):
            continue
        meta, body = read_doc(os.path.join(pdir, f))
        body = body.replace("{{blog_cards}}", cards).replace("{{latest_posts}}", latest)
        slug = meta["slug"]
        if slug == "404":
            page = render(meta, body, "404.html", 0)
            # 404 can be served from any depth: resolve links against the site root
            page = page.replace('<meta charset="utf-8">', '<meta charset="utf-8"><script>document.write(\'<base href="\'+(location.hostname.endsWith("github.io")?"/mainstreetexits/":"/")+\'">\')</script>', 1)
            page = re.sub(r'<link rel="canonical"[^>]*>', '', page)
            open(os.path.join(OUT, "404.html"), "w", encoding="utf-8").write(page)
            continue
        url = "" if slug == "home" else slug + "/"
        depth = 0 if slug == "home" else 1
        if url:
            write(url, render(meta, body, url, depth))
        else:
            open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(render(meta, body, "", 0))
        urls.append((url, today))

    sm = "".join(f"<url><loc>{SITE_URL}/{u}</loc><lastmod>{d}</lastmod></url>" for u, d in sorted(urls))
    open(os.path.join(OUT, "sitemap.xml"), "w").write(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")
    print(f"Built {len(urls)} pages + 404 into docs/")


if __name__ == "__main__":
    main()
