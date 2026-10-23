"""Build directory listings from the Comedy Database 'Listings' tab (exported as CSV).

    python3 sync_listings.py <csv-file-or-url>   (run from the Directory repo root)

Rewrites the dir-data block in index.html from the sheet. Rows with active = N are
left out. On a bad read or bad rows, nothing is changed.

SPLIT COLUMNS (Oct 23, 2026). The sheet can hold the old all-in-one columns
(where, url, note) or the split ones below. Split columns win when filled; a row
with them all blank still publishes from the old columns, so nothing breaks
while rows are being converted.
  WHERE  venue_name, venue_id (id of the venue's own Listings row), address, neighborhood
  WHEN   schedule ("1st Saturdays"), start_time ("7:00 PM"), signup_time, next (YYYY-MM-DD)
  MONEY  price_text
  WHO    host
  LINKS  website, tickets_url, facebook, performer_link (ig stays as it was)
"""
import csv, io, json, pathlib, re, sys, urllib.request

ROOT = pathlib.Path.cwd()
PAGE = ROOT / "index.html"
TYPES = {"venue", "show", "openmic", "classes", "podcast", "festival", "performer", "resource"}
GENRES = {"clown", "burlesque", "standup", "improv", "sketch", "variety"}
TEXT = ["name", "area", "where", "url", "note", "ig", "img", "alt", "next"]
SPLIT_WHERE = ["venue_name", "venue_id", "address", "neighborhood", "schedule", "start_time"]


def g(row, k):
    return (row.get(k) or "").strip()


def compose(row, by_id):
    """Turn the split columns into the fields the page shows. Returns a dict of overrides."""
    venue = by_id.get(g(row, "venue_id"), {})
    vname = g(row, "venue_name") or g(venue, "name")
    addr = g(row, "address") or g(venue, "address")
    hood = g(row, "neighborhood") or g(venue, "neighborhood")
    out = {}
    if any(g(row, k) for k in SPLIT_WHERE):
        when = " ".join(x for x in (g(row, "schedule"), g(row, "start_time")) if x)
        place = ", ".join(x for x in (vname, addr) if x)
        out["where"] = " · ".join(x for x in (when, place, hood) if x)
    site = g(row, "website")
    tickets = g(row, "tickets_url")
    if site or tickets:
        out["url"] = site or tickets
    details = []
    if g(row, "host"):
        details.append("Hosted by " + g(row, "host"))
    if g(row, "signup_time"):
        details.append("Sign-up " + g(row, "signup_time"))
    if g(row, "price_text"):
        details.append(g(row, "price_text"))
    if details:
        out["details"] = " · ".join(details)
    links = []
    vsite = g(venue, "website") or g(venue, "url")
    if vname and vsite and vsite != out.get("url"):
        links.append({"label": vname, "href": vsite})
    if tickets and tickets != out.get("url"):
        links.append({"label": "Tickets", "href": tickets})
    if g(row, "facebook"):
        links.append({"label": "Facebook", "href": g(row, "facebook")})
    if g(row, "performer_link"):
        links.append({"label": "Performer", "href": g(row, "performer_link")})
    if links:
        out["links"] = links
    return out


def fetch(source):
    if source.startswith("http"):
        with urllib.request.urlopen(source, timeout=30) as r:
            return r.read().decode("utf-8")
    return pathlib.Path(source).read_text(encoding="utf-8")


def parse(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    by_id = {g(r, "id"): r for r in rows if g(r, "id")}
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
        vid = g(row, "venue_id")
        if vid and vid not in by_id:
            raise ValueError(f"row {n} ({iid}): venue_id '{vid}' is not an id in the Listings tab")
        item.update(compose(row, by_id))
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
