"""
fetch_v4.py - Israeli supermarket prices using il-supermarket-scraper 1.0.x
"""
import json, os, gzip, re, subprocess, sys, xml.etree.ElementTree as ET
from datetime import datetime
from collections import defaultdict
from pathlib import Path

OUTPUT = "prices.json"
DUMPS  = "dumps"

def install():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-U", "il-supermarket-scraper"])

def fetch():
    from il_supermarket_scarper.scrappers_factory import ScraperFactory
    from il_supermarket_scarper.main_scarper import MainScraper

    os.makedirs(DUMPS, exist_ok=True)
    scrapers = ScraperFactory.all_scrapers()
    for scraper_class in scrapers[:8]:  # first 8 chains
        try:
            scraper = scraper_class(folder_name=DUMPS)
            scraper.scrape(files_types=["PriceFull"], limit=1)
            print(f"  ✓ {scraper_class.__name__}")
        except Exception as e:
            print(f"  ✗ {scraper_class.__name__}: {e}")

def parse_xml(path):
    try:
        content = Path(path).read_bytes()
        if content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)
        root = ET.fromstring(content)
    except Exception as e:
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
        print("No dumps folder"); return

    for f in list(dump_path.rglob("*.xml")) + list(dump_path.rglob("*.gz")):
        chain_name = f.parent.name or "unknown"
        prices = parse_xml(f)
        if prices:
            chain_data[chain_name].update(prices)
            print(f"  {chain_name}: {len(prices)} products")

    counter = defaultdict(dict)
    for cname, items in chain_data.items():
        for name, price in items.items():
            clean = re.sub(r"\s+", " ", name.strip())[:80]
            counter[clean][cname] = price

    products = {k: v for k, v in counter.items() if len(v) >= 2}
    products = dict(sorted(products.items(), key=lambda x: len(x[1]), reverse=True))

    out = {
        "updated_at": datetime.now().isoformat(),
        "chains": sorted(chain_data.keys()),
        "total_products": len(products),
        "products": products,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved {OUTPUT}")
    print(f"  Chains: {len(chain_data)} — {', '.join(sorted(chain_data.keys()))}")
    print(f"  Products (2+ chains): {len(products):,}")

def main():
    print("=== סל חכם v4 ===\n")
    print("Installing...")
    install()
    print("Fetching prices...")
    fetch()
    print("\nBuilding prices.json...")
    build_json()

if __name__ == "__main__":
    main()
