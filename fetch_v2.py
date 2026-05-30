"""
fetch_v2.py - uses direct XML file URLs from Israeli price transparency law
"""
import gzip, json, re, ssl, time, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime
from collections import defaultdict

OUTPUT = "prices.json"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
}

# Direct index URLs for each chain
CHAINS = [
    {"name": "שופרסל",    "url": "https://prices.shufersal.co.il/"},
    {"name": "רמי לוי",   "url": "https://url.retail.publishedprices.co.il/ramilevy/"},
    {"name": "מגה",       "url": "https://publishprice.mega.co.il/"},
    {"name": "ויקטורי",   "url": "https://publishprice.victory.co.il/"},
    {"name": "יינות ביתן","url": "https://publishprice.ybitan.co.il/"},
    {"name": "אושר עד",   "url": "https://url.retail.publishedprices.co.il/osherad/"},
    {"name": "חצי חינם",  "url": "https://url.retail.publishedprices.co.il/hazihinam/"},
    {"name": "יוחנן דוד", "url": "https://url.retail.publishedprices.co.il/yohananof/"},
    {"name": "דור אלון",  "url": "https://url.retail.publishedprices.co.il/doralon/"},
]

def fetch_url(url, timeout=20):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()

def get_file_urls(chain):
    try:
        html = fetch_url(chain["url"]).decode("utf-8", errors="ignore")
        urls = re.findall(r'href=["\']([^"\']*PriceFull[^"\']*)["\']', html, re.IGNORECASE)
        base = chain["url"].rstrip("/")
        full = []
        for u in urls:
            full.append(u if u.startswith("http") else base + "/" + u.lstrip("/"))
        print(f"  found {len(full)} files")
        return full[:2]
    except Exception as e:
        print(f"  error: {e}")
        return []

def parse_xml(content):
    try:
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
        name = g("ItemName") or g("itemname")
        price = g("ItemPrice") or g("itemprice")
        if name and price:
            try: prices[name] = round(float(price), 2)
            except: pass
    return prices

def main():
    print("=== סל חכם — שליפת מחירים ===\n")
    chain_data = {}
    for chain in CHAINS:
        print(f"\n[{chain['name']}]")
        urls = get_file_urls(chain)
        prices = {}
        for url in urls:
            try:
                data = fetch_url(url, timeout=30)
                p = parse_xml(data)
                prices.update(p)
                print(f"  ✓ {len(p)} products from {url.split('/')[-1][:40]}")
                time.sleep(0.3)
            except Exception as e:
                print(f"  ✗ {e}")
        if prices:
            chain_data[chain["name"]] = prices

    counter = defaultdict(dict)
    for cname, items in chain_data.items():
        for name, price in items.items():
            counter[re.sub(r'\s+', ' ', name.strip())[:80]][cname] = price

    products = {k: v for k, v in counter.items() if len(v) >= 2}
    products = dict(sorted(products.items(), key=lambda x: len(x[1]), reverse=True))

    out = {
        "updated_at": datetime.now().isoformat(),
        "chains": sorted(chain_data.keys()),
        "total_products": len(products),
        "products": products
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved {OUTPUT}")
    print(f"  Chains fetched: {len(chain_data)} — {', '.join(chain_data.keys())}")
    print(f"  Products (2+ chains): {len(products):,}")
    print(f"\nNow upload prices.json to GitHub next to index.html")

if __name__ == "__main__":
    main()
