import json, os, gzip, re, subprocess, sys, xml.etree.ElementTree as ET
from datetime import datetime
from collections import defaultdict
from pathlib import Path

OUTPUT = "prices.json"
DUMPS  = "dumps"

# Install
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-U", "il-supermarket-scraper"])

# Set dump folder via env var (how the package reads it)
os.environ["DUMP_LOCATION"] = DUMPS
os.makedirs(DUMPS, exist_ok=True)

# Run scraper
from il_supermarket_scarper import ScarpingTask
scraper = ScarpingTask()
scraper.start()

# Parse XML files
def parse_xml(path):
    try:
        content = Path(path).read_bytes()
        if content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)
        root = ET.fromstring(content)
    except:
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

chain_data = defaultdict(dict)
for f in list(Path(DUMPS).rglob("*.xml")) + list(Path(DUMPS).rglob("*.gz")):
    chain_name = f.parent.name or "unknown"
    prices = parse_xml(f)
    if prices:
        chain_data[chain_name].update(prices)
        print(f"  {chain_name}: {len(prices)} products")

counter = defaultdict(dict)
for cname, items in chain_data.items():
    for name, price in items.items():
        counter[re.sub(r"\s+", " ", name.strip())[:80]][cname] = price

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
print(f"  Chains: {len(chain_data)}: {', '.join(sorted(chain_data.keys()))}")
print(f"  Products: {len(products):,}")
