"""
fetch_all_chains.py
מושך מחירים מכל רשתות המזון בישראל ומייצר prices.json
מקור: חוק המזון (שקיפות מחירים) — כל הנתונים ציבוריים

הרצה: python fetch_all_chains.py
דרישות: pip install requests
"""

import os, re, gzip, json, time, requests, xml.etree.ElementTree as ET
from datetime import datetime
from collections import defaultdict

OUTPUT_FILE = "prices.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SalChaham/1.0; price-transparency)"}

# ---------------------------------------------------------------
# כל הרשתות + ה-provider שלהן
# ---------------------------------------------------------------
CERBERUS_CHAINS = [
    {"name": "רמי לוי",        "id": "7290058140886"},
    {"name": "אושר עד",        "id": "7290103152017"},
    {"name": "חצי חינם",       "id": "7290700100008"},
    {"name": "יוחנן דוד",      "id": "7290803800003"},
    {"name": "דור אלון",       "id": "7290492000005"},
    {"name": "סופר דוש",       "id": "7290873900009"},
    {"name": "כשת טעמים",      "id": "7290785400000"},
]

NIBIT_CHAINS = [
    {"name": "ויקטורי",        "id": "7290696200003"},
    {"name": "מחסני השוק",     "id": "7290661400001"},
    {"name": "מחסני להב",      "id": "7290058179503"},
]

PRIVATE_CHAINS = [
    {
        "name": "שופרסל",
        "id": "7290027600007",
        "url": "https://prices.shufersal.co.il/",
        "file_pattern": "PriceFull",
    },
    {
        "name": "מגה",
        "id": "7290055700007",
        "url": "https://publishprice.mega.co.il/",
        "file_pattern": "PriceFull",
    },
    {
        "name": "יינות ביתן",
        "id": "7290725900003",
        "url": "https://publishprice.ybitan.co.il/",
        "file_pattern": "PriceFull",
    },
    {
        "name": "עדן טבע מרקט",
        "id": "7290055755557",
        "url": "https://publishprice.eden.co.il/",
        "file_pattern": "PriceFull",
    },
    {
        "name": "קואופ",
        "id": "7290633800006",
        "url": "https://coopsprice.coop.co.il/",
        "file_pattern": "PriceFull",
    },
    {
        "name": "טיב טעם",
        "id": "7290873255550",
        "url": "https://publishprice.tivtaam.co.il/",
        "file_pattern": "PriceFull",
    },
]

# ---------------------------------------------------------------
# Cerberus provider (רמי לוי, אושר עד וכו')
# ---------------------------------------------------------------
def fetch_cerberus(chain):
    base = f"https://url.retail.publishedprices.co.il/{get_cerberus_slug(chain['id'])}/"
    try:
        r = requests.get(base, headers=HEADERS, timeout=15)
        urls = re.findall(r'href=["\']([^"\']*PriceFull[^"\']*)["\']', r.text, re.IGNORECASE)
        full_urls = []
        for u in urls:
            full_urls.append(u if u.startswith("http") else base.rstrip("/") + "/" + u.lstrip("/"))
        return full_urls[:2]
    except Exception as e:
        print(f"    cerberus index error: {e}")
        return []

CERBERUS_SLUGS = {
    "7290058140886": "ramilevy",
    "7290103152017": "osherad",
    "7290700100008": "hazihinam",
    "7290803800003": "yohananof",
    "7290492000005": "doralon",
    "7290873900009": "superdush",
    "7290785400000": "keshettaamim",
}
def get_cerberus_slug(chain_id):
    return CERBERUS_SLUGS.get(chain_id, chain_id)

# ---------------------------------------------------------------
# Nibit provider (ויקטורי, מחסני השוק)
# ---------------------------------------------------------------
def fetch_nibit(chain):
    base = f"https://matrixcatalog.co.il/NBCompetitionData.aspx"
    try:
        r = requests.get(base, headers=HEADERS, timeout=15,
                        params={"fileType": "gz", "chainId": chain["id"]})
        urls = re.findall(r'href=["\']([^"\']*PriceFull[^"\']*)["\']', r.text, re.IGNORECASE)
        full_urls = []
        for u in urls:
            full_urls.append(u if u.startswith("http") else "https://matrixcatalog.co.il/" + u.lstrip("/"))
        return full_urls[:2]
    except Exception as e:
        print(f"    nibit index error: {e}")
        return []

# ---------------------------------------------------------------
# Private provider (שופרסל, מגה וכו')
# ---------------------------------------------------------------
def fetch_private(chain):
    try:
        r = requests.get(chain["url"], headers=HEADERS, timeout=15)
        pattern = chain.get("file_pattern", "PriceFull")
        urls = re.findall(r'href=["\']([^"\']*' + pattern + r'[^"\']*)["\']', r.text, re.IGNORECASE)
        full_urls = []
        for u in urls:
            full_urls.append(u if u.startswith("http") else chain["url"].rstrip("/") + "/" + u.lstrip("/"))
        return full_urls[:2]
    except Exception as e:
        print(f"    private index error: {e}")
        return []

# ---------------------------------------------------------------
# פענוח XML
# ---------------------------------------------------------------
def parse_xml(content):
    try:
        if content[:2] == b"\x1f\x8b":
            content = gzip.decompress(content)
        root = ET.fromstring(content)
    except Exception as e:
        print(f"      parse error: {e}")
        return {}

    items = root.findall(".//Item") or root.findall(".//item")
    prices = {}
    for item in items:
        def g(tag):
            el = item.find(tag) or item.find(tag.lower())
            return (el.text or "").strip() if el is not None else ""
        name = g("ItemName") or g("itemname")
        price_str = g("ItemPrice") or g("itemprice")
        if not name or not price_str:
            continue
        try:
            prices[name] = round(float(price_str), 2)
        except ValueError:
            continue
    return prices

# ---------------------------------------------------------------
# שליפה כללית
# ---------------------------------------------------------------
def fetch_chain(chain, provider):
    print(f"\n  [{chain['name']}]")
    if provider == "cerberus":
        urls = fetch_cerberus(chain)
    elif provider == "nibit":
        urls = fetch_nibit(chain)
    else:
        urls = fetch_private(chain)

    if not urls:
        print(f"    אין קבצים")
        return {}

    all_prices = {}
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            p = parse_xml(r.content)
            all_prices.update(p)
            print(f"    ✓ {len(p)} מוצרים")
            time.sleep(0.4)
        except Exception as e:
            print(f"    ✗ {e}")

    return all_prices

# ---------------------------------------------------------------
# בניית JSON פלט
# ---------------------------------------------------------------
def build_output(chain_data):
    counter = defaultdict(dict)
    for chain_name, prices in chain_data.items():
        for item, price in prices.items():
            name = re.sub(r'\s+', ' ', item.strip())[:80]
            counter[name][chain_name] = price

    # רק מוצרים שמופיעים ב-3+ רשתות
    products = {k: v for k, v in counter.items() if len(v) >= 3}

    # מיון לפי כמות רשתות
    products = dict(sorted(products.items(), key=lambda x: len(x[1]), reverse=True))

    chains = sorted(chain_data.keys())
    return {
        "updated_at": datetime.now().isoformat(),
        "chains": chains,
        "total_products": len(products),
        "products": products,
    }

# ---------------------------------------------------------------
# main
# ---------------------------------------------------------------
def main():
    print("=== סל חכם — שליפת כל הרשתות ===\n")
    chain_data = {}

    print("── Cerberus (רמי לוי, אושר עד, חצי חינם...) ──")
    for chain in CERBERUS_CHAINS:
        p = fetch_chain(chain, "cerberus")
        if p:
            chain_data[chain["name"]] = p

    print("\n── Nibit (ויקטורי, מחסני השוק...) ──")
    for chain in NIBIT_CHAINS:
        p = fetch_chain(chain, "nibit")
        if p:
            chain_data[chain["name"]] = p

    print("\n── Private (שופרסל, מגה, יינות ביתן...) ──")
    for chain in PRIVATE_CHAINS:
        p = fetch_chain(chain, "private")
        if p:
            chain_data[chain["name"]] = p

    print(f"\n\nבונה {OUTPUT_FILE}...")
    output = build_output(chain_data)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ {OUTPUT_FILE} נשמר בהצלחה!")
    print(f"  רשתות שנשלפו: {len(chain_data)}")
    print(f"  מוצרים משותפים (3+ רשתות): {output['total_products']:,}")
    print(f"  רשתות: {', '.join(output['chains'])}")
    print(f"\nעכשיו תעלה את prices.json ל-GitHub לצד index.html")

if __name__ == "__main__":
    main()
