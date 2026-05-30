"""
fetch_v3.py
Uses il-supermarket-scarper — the official maintained Python package
for Israeli supermarket price data.
"""
import json, os, gzip, re, subprocess, sys, xml.etree.ElementTree as ET
from datetime import datetime
from collections import defaultdict
from pathlib import Path

OUTPUT = "prices.json"
DUMPS  = "dumps"

def install():
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q", "-U",
        "il-supermarket-scarper"
    ])

def fetch():
    from il_supermarket_scarper import ScarpingTask
    from il_supermarket_scarper.scrappers_factory import ScraperFactory

    os.makedirs(DUMPS, exist_ok=True)

    # Use all available scrapers, limit to 1 file per chain (fastest)
    task = ScarpingTask(
        dump_folder_name=DUMPS,
        files_types=["PriceFull"],
        limit=1,
    )
    task.start()

def parse_xml(path):
    try:
        content = Path(path).read_bytes()
        if content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)
        root = ET.fromstring(content)
    except Exception as e:
        print(f"    parse error {path}: {e}")
        return {}
    prices = {}
    for item in root.findall(".//Item") or root.findall(".//item"):
        def g(t):
            e = item.find(t) or item.find(t.lower())
            return (e.text or "").strip() if e is not None else ""
        name  = g("ItemName")  or g("itemname")
        price = g("ItemPrice") or g("itemprice")
        if name and price:
            try: prices[name] = round(float(price), 2)
            except: pass
    return prices

def build_json():
    chain_data = defaultdict(dict)
    dump_path  = Path(DUMPS)

    if not dump_path.exists():
        print("No dumps folder found")
        return

    for xml_file in dump_path.rglob("*.xml"):
        chain_name = xml_file.parent.name
        prices = parse_xml(xml_file)
        chain_data[chain_name].update(prices)
        print(f"  {chain_name}: {len(prices)} products from {xml_file.name[:40]}")

    for gz_file in dump_path.rglob("*.gz"):
        chain_name = gz_file.parent.name
        prices = parse_xml(gz_file)
        chain_data[chain_name].update(prices)
        print(f"  {chain_name}: {len(prices)} products from {gz_file.name[:40]}")

    counter = defaultdict(dict)
    for cname, items in chain_data.items():
        for name, price in items.items():
            clean = re.sub(r"\s+", " ", name.strip())[:80]
            counter[clean][cname] = price

    products = {k: v for k, v in counter.items() if len(v) >= 2}
    products = dict(sorted(products.items(), key=lambda x: len(x[1]), reverse=True))

    out = {
        "updated_at":     datetime.now().isoformat(),
        "chains":         sorted(chain_data.keys()),
        "total_products": len(products),
        "products":       products,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved {OUTPUT}")
    print(f"  Chains: {len(chain_data)} — {', '.join(sorted(chain_data.keys()))}")
    print(f"  Products (2+ chains): {len(products):,}")

def main():
    print("=== סל חכם — שליפת מחירים v3 ===\n")
    print("Installing il-supermarket-scarper...")
    install()
    print("Fetching prices (this may take 5-10 min)...")
    fetch()
    print("\nBuilding prices.json...")
    build_json()

if __name__ == "__main__":
    main()
