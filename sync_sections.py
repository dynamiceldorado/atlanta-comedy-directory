"""Pull section titles/order from the Comedy Database sheet into sections.json.

Source: the Sections columns (section_key, display_order, title, active) of the
sheet, published to the web as CSV. Usage:
    python3 sync_sections.py <csv-url-or-local-file>
    (or set SECTIONS_CSV_URL and run with no arguments)

If the sheet can't be read or has bad rows, the existing sections.json is kept
and the script exits non-zero so the scheduled run fails visibly.
"""
import csv, io, json, os, pathlib, sys, urllib.request

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "sections.json"
KNOWN_KEYS = {"venue", "show", "openmic", "classes", "podcast", "festival", "performer", "resource"}


def fetch(source):
    if source.startswith("http"):
        with urllib.request.urlopen(source, timeout=30) as r:
            return r.read().decode("utf-8")
    return pathlib.Path(source).read_text(encoding="utf-8")


def parse(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    sections, seen = [], set()
    for n, row in enumerate(rows, 2):  # row 1 is the header
        key = (row.get("section_key") or "").strip()
        if not key:
            continue  # blank rows below the table are fine
        if key not in KNOWN_KEYS:
            raise ValueError(f"row {n}: unknown section_key '{key}'")
        if key in seen:
            raise ValueError(f"row {n}: duplicate section_key '{key}'")
        seen.add(key)
        try:
            order = int((row.get("display_order") or "").strip())
        except ValueError:
            raise ValueError(f"row {n}: display_order must be a whole number")
        title = (row.get("title") or "").strip()
        if not title:
            raise ValueError(f"row {n}: title is empty")
        active = (row.get("active") or "Y").strip().upper() != "N"
        sections.append({"key": key, "order": order, "title": title, "active": active})
    if not any(s["active"] for s in sections):
        raise ValueError("no active sections")
    return sorted(sections, key=lambda s: s["order"])


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SECTIONS_CSV_URL", "")
    if not source:
        sys.exit("No source: pass a CSV URL/path or set SECTIONS_CSV_URL.")
    try:
        sections = parse(fetch(source))
    except Exception as exc:
        sys.exit(f"Sections sync failed; sections.json left as-is. {exc}")
    OUT.write_text(json.dumps(sections, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(sections)} sections to {OUT.name}")


if __name__ == "__main__":
    main()
