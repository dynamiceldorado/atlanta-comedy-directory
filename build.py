#!/usr/bin/env python3
"""Pre-render the Atlanta Comedy Directory so search engines and AI tools can read it.

Run after any change to the dir-data JSON in index.html:
    python3 build.py

It is idempotent. It rewrites three things in index.html, between marker comments:
  1. SEO tags in <head>: title, description, canonical, Open Graph and a JSON-LD ItemList.
  2. A static copy of every listing inside <div id="dir-root">. The page script
     replaces it with the interactive version on load, so visitors see no change.
  3. robots.txt and sitemap.xml next to index.html.
"""
import html, json, re, pathlib, datetime

ROOT = pathlib.Path(__file__).parent
PAGE = ROOT / "index.html"
SITE = "https://directory.dynamiceldorado.com/"
FORM = "https://docs.google.com/forms/d/e/1FAIpQLSdmeltLBWwirmeO_R6KCv9PdUNMEizfonqVJX2pDmcGjky0cQ/viewform"
GUIDE = "https://guide.dynamiceldorado.com/"

GENRES = {"clown": ("Clown", "--clown"), "burlesque": ("Burlesque", "--burlesque"),
          "standup": ("Stand-up", "--standup"), "improv": ("Improv", "--improv"),
          "sketch": ("Sketch", "--sketch"), "variety": ("Variety & theater", "--other")}
TYPES = [("venue", "Theaters & clubs"), ("show", "Shows & troupes"), ("openmic", "Open mics & jams"),
         ("classes", "Classes & schools"), ("podcast", "Podcasts"), ("festival", "Festivals"),
         ("performer", "Performers"), ("resource", "Calendars & resources")]
DESC = ("Atlanta's comedy scene in one place: theaters and clubs, improv troupes, open mics, "
        "comedy classes, podcasts and festivals, inside and outside the Perimeter.")

e = lambda s: html.escape(s or "", quote=True)


def ig_href(v):
    return v if v.startswith("http") else "https://www.instagram.com/" + v.lstrip("@")


def card(it):
    name = e(it["name"])
    title = f'<a href="{e(it["url"])}" target="_blank" rel="noopener">{name}</a>' if it.get("url") else name
    g0 = (it.get("genres") or [None])[0]
    out = [f'<article class="card{" g-" + g0 if g0 else ""}"><h3>{title}</h3>']
    # Genre/area line comes right under the name, matching the interactive card
    tags = []
    if it.get("area"):
        full = "Outside the Perimeter (I-285)" if it["area"] == "OTP" else "Inside the Perimeter (I-285)"
        tags.append(f'<abbr class="area{" otp" if it["area"] == "OTP" else ""}" title="{full}">{e(it["area"])}</abbr>')
    for g in it.get("genres") or []:
        label, var = GENRES.get(g, (g, "--other"))
        tags.append(f'<span class="tag"><span class="sq" aria-hidden="true" style="background:var({var})"></span>{e(label)}</span>')
    if tags:
        out.append(f'<div class="tags">{"".join(tags)}</div>')
    if it.get("where"):
        out.append(f'<div class="where">{e(it["where"])}</div>')
    if it.get("ig"):
        v = it["ig"]
        label = "Instagram" if v.startswith("http") else "@" + v.lstrip("@")
        out.append(f'<div class="where"><a href="{e(ig_href(v))}" target="_blank" rel="noopener">{e(label)}</a></div>')
    if it.get("note"):
        # Full text in the static copy (for search engines); the page script clamps it to 2 lines
        out.append(f'<p class="note">{e(it["note"])}</p>')
    out.append('</article>')
    return "".join(out)


NAV = ('<nav class="topnav" aria-label="Dynamic El Dorado sites"><div class="wrap">'
       '<a class="home" href="https://dynamiceldorado.com/">Dynamic El Dorado</a>'
       '<a href="https://directory.dynamiceldorado.com/" aria-current="page">Directory</a>'
       f'<a href="{GUIDE}">Live Comedy Guide</a></div></nav>')
FOOTNAV = ('<ul class="footnav">'
           '<li><a href="https://dynamiceldorado.com/">Dynamic El Dorado</a></li>'
           '<li><a href="https://directory.dynamiceldorado.com/">Directory</a></li>'
           f'<li><a href="{GUIDE}">Live Comedy Guide</a></li>'
           '<li><a href="https://squareup.com/customer-programs/enroll/tdb8t92f3zVq">Newsletter</a></li>'
           '<li><a href="https://www.instagram.com/dynamiceldorado/">Instagram</a></li></ul>')


def prerender(data):
    items = data["items"]
    parts = [NAV + '<header class="mast"><div class="wrap">'
             '<div class="mast-brand"><div class="presented">Presented by</div>'
             '<a href="https://dynamiceldorado.com/"><img src="logo.png" alt="Dynamic El Dorado" width="150" height="48"></a>'
             '<a class="btn gold" href="https://squareup.com/customer-programs/enroll/tdb8t92f3zVq">Get the newsletter</a></div>'
             '<h1>Atlanta Comedy <span>Directory</span></h1>'
             '<p class="lede">Where to see it, learn it and do it: the theaters, troupes, open mics, classes, '
             "podcasts and festivals that make up Atlanta's comedy scene, inside and outside the Perimeter.</p>"
             f'<div class="mast-meta"><span>{len(items)} listings</span><span>Last updated {e(data.get("updated") or "—")}</span></div>'
             '</div></header><main><div class="wrap"><div id="results">']
    for key, label in TYPES:
        group = sorted((i for i in items if i.get("type") == key), key=lambda i: i["name"].lower())
        if not group:
            continue
        parts.append(f'<section class="group"><div class="grid"><h2>{e(label)} <small>{len(group)}</small></h2>')
        parts.extend(card(i) for i in group)
        parts.append("</div></section>")
    parts.append('</div><section class="suggest"><h2>Suggest a listing</h2>'
                 '<p>Run a show, a mic, a troupe, a class or a podcast? Performing in Atlanta and want to be listed? '
                 f'<a href="{FORM}">Got a thing we should add here? Let us know about it!</a></p></section>'
                 '</div></main><footer><div class="wrap">' + FOOTNAV + '<p>Listings are checked against public sources and updated regularly. '
                 'Details change: confirm dates and prices with the venue before you go.</p>'
                 f'<p>What\'s on this weekend? See the <a href="{GUIDE}">Live Comedy Guide</a>.</p></div></footer>')
    return "".join(parts)


def seo_head(data):
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": "Atlanta Comedy Directory",
          "description": DESC, "url": SITE, "numberOfItems": len(data["items"]),
          "itemListElement": []}
    for n, it in enumerate(sorted(data["items"], key=lambda i: i["name"].lower()), 1):
        thing = {"@type": "Organization" if it.get("type") in ("venue", "classes", "show", "festival") else "Thing",
                 "name": it["name"]}
        if it.get("url"):
            thing["url"] = it["url"]
        if it.get("note"):
            thing["description"] = it["note"]
        ld["itemListElement"].append({"@type": "ListItem", "position": n, "item": thing})
    ld_json = json.dumps(ld, ensure_ascii=False).replace("<", "\\u003c")
    return ("<!--seo:start-->"
            "<title>Atlanta Comedy Directory: Theaters, Open Mics, Classes &amp; Troupes</title>"
            f'<meta name="description" content="{e(DESC)}">'
            f'<link rel="canonical" href="{SITE}">'
            '<meta property="og:type" content="website">'
            '<meta property="og:title" content="Atlanta Comedy Directory">'
            f'<meta property="og:description" content="{e(DESC)}">'
            f'<meta property="og:url" content="{SITE}">'
            '<meta property="og:site_name" content="Dynamic El Dorado">'
            '<meta name="twitter:card" content="summary">'
            f'<script type="application/ld+json">{ld_json}</script>'
            "<!--seo:end-->")


def main():
    src = PAGE.read_text(encoding="utf-8")
    data = json.loads(re.search(r'<script type="application/json" id="dir-data">(.*?)</script>', src, re.S).group(1))

    # 1. SEO tags in <head> (replace an earlier run, or insert before </head>)
    src = re.sub(r"<!--seo:start-->.*?<!--seo:end-->", "", src, flags=re.S)
    src = src.replace("</head>", seo_head(data) + "</head>", 1)
    if src.startswith("<!doctype html><html>"):
        src = src.replace("<html>", '<html lang="en">', 1)
    src = re.sub(r"<body>\s*<title>[^<]*</title>", "<body>", src, count=1)  # stray title from the editor copy

    # 2. Static listings inside dir-root
    src = re.sub(r'<div id="dir-root">.*?</div><!--/dir-root-->|<div id="dir-root"></div>',
                 lambda _: f'<div id="dir-root">{prerender(data)}</div><!--/dir-root-->', src, count=1, flags=re.S)
    PAGE.write_text(src, encoding="utf-8")

    # 3. robots.txt and sitemap.xml
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n", encoding="utf-8")
    lastmod = data.get("updated") or datetime.date.today().isoformat()
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{SITE}</loc><lastmod>{lastmod}</lastmod><changefreq>weekly</changefreq></url>\n"
        "</urlset>\n", encoding="utf-8")
    print(f"Pre-rendered {len(data['items'])} listings; updated {lastmod}")


if __name__ == "__main__":
    main()
