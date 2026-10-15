# Atlanta Comedy Directory

Live at https://directory.dynamiceldorado.com/ (GitHub Pages).

Listings live in the `dir-data` JSON inside `index.html`. After changing them, run:

    python3 build.py

That rebuilds the static copy of every listing (so search engines and AI tools can read it), the SEO tags, `robots.txt` and `sitemap.xml`. Commit everything it changes.
