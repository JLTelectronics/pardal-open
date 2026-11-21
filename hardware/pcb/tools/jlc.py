import json, sys, urllib.request

URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"

def search(keyword, n=8, instock=True):
    body = json.dumps({"keyword": keyword, "currentPage": 1, "pageSize": 30}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    out = []
    for it in (d.get("data") or {}).get("componentPageInfo", {}).get("list", []) or []:
        pr = sorted(it.get("componentPrices") or [], key=lambda p: p["startNumber"])
        p10 = next((p["productPrice"] for p in pr if p["startNumber"] <= 10 <= (p["endNumber"] if p["endNumber"] > 0 else 1e9)),
                   pr[0]["productPrice"] if pr else None)
        if instock and not it.get("stockCount"):
            continue
        out.append({"lcsc": it["componentCode"], "mpn": it["componentModelEn"], "brand": it["componentBrandEn"],
                    "pkg": it.get("componentSpecificationEn"), "type": "basic" if it["componentLibraryType"] == "base" else
                    ("pref" if it.get("preferredComponentFlag") else "ext"),
                    "stock": it["stockCount"], "p10": p10, "desc": (it.get("describe") or "")[:90]})
    out.sort(key=lambda r: ({"basic": 0, "pref": 1, "ext": 2}[r["type"]], r["p10"] or 99))
    return out[:n]

if __name__ == "__main__":
    for kw in sys.argv[1:]:
        print(f"== {kw}")
        for r in search(kw):
            print(f"  {r['lcsc']:>10} {r['type']:5} ${r['p10']:<7} st {r['stock']:<7} {r['mpn'][:28]:28} {str(r['pkg'])[:18]:18} {r['desc'][:60]}")
