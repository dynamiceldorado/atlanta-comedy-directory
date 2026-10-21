"""Build directory listings from the Comedy Database 'Listings' tab (exported as CSV).

    python3 sync_listings.py <csv-file-or-url>   (run from the Directory repo root)

Rewrites the dir-data block in index.html from the sheet. Rows with active = N are
left out. On a bad read or bad rows, nothing is changed.
"""
import csv, io, json, pathlib, re, sys, urllib.request

ROOT = pathlib.Path.cwd()
PAGE = ROOT / "index.html"
TYPES = {"venue", "show", "openmic", "classes", "podcast", "festival", "performer", "resource"}
GENRES = {"clown", "burlesque", "standup", "improv", "sketch", "variety"}
TEXT = ["name", "area", "where", "url", "note", "ig", "img", "alt", "next"]


def fetch(source):
    if source.startswith("http"):
        with urllib.request.urlopen(source, timeout=30) as r:
            return r.read().decode("utf-8")
    return pathlib.Path(source).read_text(encoding="utf-8")


def parse(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    items, ids = [], set()
    for n, row in enumerate(rows, 2):
        if not (row.get("id") or "").strip():
            continue
        if (row.get("active") or "Y").strip().upper() == "N":
            continue
        iid = row["id"].strip()
        if iid in ids:
            raise ValueError(f"row {n}: duplicate id '{iid}'")
        ids.add(iid)
        typ = (row.get("type") or "").strip()
        if typ not in TYPES:
            raise ValueError(f"row {n} ({iid}): unknown type '{typ}'")
        genres = [g.strip() for g in (row.get("genres") or "").split("|") if g.strip()]
        bad = [g for g in genres if g not in GENRES]
        if bad:
            raise ValueError(f"row {n} ({iid}): unknown genre {bad}")
        if not (row.get("name") or "").strip():
            raise ValueError(f"row {n} ({iid}): name is empty")
        item = {"id": iid, "name": row["name"].strip(), "type": typ}
        for k in ("area", "where", "url", "note", "ig"):
            item[k] = (row.get(k) or "").strip()
        item["genres"] = genres
        for k in ("img", "alt", "next"):
            v = (row.get(k) or "").strip()
            if v:
                item[k] = v
        items.append(item)
    if not items:
        raise ValueError("no active listings found")
    return items


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: sync_listings.py <csv-file-or-url>")
    try:
        items = parse(fetch(sys.argv[1]))
    except Exception as exc:
        sys.exit(f"Listings sync failed; index.html left as-is. {exc}")
    src = PAGE.read_text(encoding="utf-8")
    m = re.search(r'(<script type="application/json" id="dir-data">)(.*?)(</script>)', src, re.S)
    data = json.loads(m.group(2))
    data["items"] = items
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    PAGE.write_text(src[:m.start(2)] + blob + src[m.end(2):], encoding="utf-8")
    print(f"Wrote {len(items)} listings to index.html")


if __name__ == "__main__":
    main()
