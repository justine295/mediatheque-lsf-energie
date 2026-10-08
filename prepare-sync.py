#!/usr/bin/env python3
"""
Prépare la synchro quotidienne des vignettes et des publicités Meta.

Entrées :
  db-snapshot/contents/*.json   export ArtifactData de la collection "contents"
                                ({"id","data","version"} ou le document seul)
  pubs-meta/ads.json            sortie de meta-ads.py
  meta-pages.json               pages Facebook suivies (cible, landing)
Sorties :
  vignettes-todo.json           pages à capturer (pour capture-vignettes.py)
  sync-plan.json                {"vignettes": [...], "ads_new": [...], "ads_update": [...]}
"""
import collections
import datetime as dt
import glob
import json
import os
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = dt.date.today()
REFRESH_DAYS = 7


def load_contents():
    docs = {}
    for f in glob.glob(os.path.join(HERE, "db-snapshot", "contents", "*.json")):
        raw = json.load(open(f))
        doc_id = raw.get("id") or os.path.basename(f)[:-5]
        data = raw.get("data", raw)
        docs[doc_id] = {"data": data, "version": raw.get("version")}
    return docs


def theme(text):
    first = unicodedata.normalize("NFKC", text).strip().split("\n")[0]
    first = "".join(ch for ch in first if ch.isalnum() or ch in " '’:+-,.?!€%").strip(" -:")
    return (first[:55].rsplit(" ", 1)[0] + "…") if len(first) > 55 else first


def main():
    docs = load_contents()
    plan = {"vignettes": [], "ads_new": [], "ads_update": []}

    # 1. Vignettes : pages web sans vignette, ou capture automatique de plus de 7 jours.
    #    Une vignette choisie à la main (thumbId sans thumbAuto) n'est jamais remplacée.
    url_count = collections.Counter(d["data"].get("url") for d in docs.values())
    for doc_id, d in docs.items():
        x = d["data"]
        url = x.get("url") or ""
        if not url.startswith("http") or "facebook.com/ads/library" in url:
            continue
        if url_count[url] > 1 and not x.get("thumbId"):
            continue  # plusieurs fiches sur la même page : la capture ne les distinguerait pas
        thumb, auto = x.get("thumbId"), x.get("thumbAuto")
        stale = auto and (TODAY - dt.date.fromisoformat(auto[:10])).days >= REFRESH_DAYS
        if not thumb or stale:
            plan["vignettes"].append({"id": doc_id, "url": url, "version": d["version"],
                                      "old_thumb_to_delete": thumb if auto else None})
    json.dump([{"id": v["id"], "url": v["url"]} for v in plan["vignettes"]],
              open(os.path.join(HERE, "vignettes-todo.json"), "w"), indent=1)

    # 2. Publicités Meta : une fiche par visuel (page + empreinte de l'image).
    ads_path = os.path.join(HERE, "pubs-meta", "ads.json")
    if os.path.exists(ads_path):
        pages = {p["slug"]: p for p in json.load(open(os.path.join(HERE, "meta-pages.json")))}
        groups = collections.OrderedDict()
        for a in json.load(open(ads_path)):
            groups.setdefault((a["slug"], a["hash"]), []).append(a)
        for (slug, h), ads in groups.items():
            pg = pages.get(slug)
            if not pg:
                continue
            doc_id = f"ad-{slug}-{h}"
            active = any(a["status"] == "Actif" for a in ads)
            dates = " ; ".join(sorted({a["dates"] for a in ads if a["dates"]}))
            ad_ids = sorted({a["id"] for a in ads})
            text = unicodedata.normalize("NFKC", ads[0]["text"])
            desc = (f"Publicité sponsorisée Facebook/Instagram, page « {pg['name']} ». "
                    + ("En diffusion. " if active else "Diffusion terminée. ")
                    + f"Dates : {dates}. {len(ad_ids)} publicité{'s' if len(ad_ids) > 1 else ''} (ID {', '.join(ad_ids)}).\n\nTexte : {text[:600]}")
            if doc_id in docs:
                cur = docs[doc_id]["data"]
                tags = [t for t in cur.get("tags", []) if t != "en diffusion"] + (["en diffusion"] if active else [])
                merged_ids = sorted(set(cur.get("adIds") or []) | set(ad_ids))
                if tags != cur.get("tags") or merged_ids != sorted(cur.get("adIds") or []):
                    plan["ads_update"].append({"doc_id": doc_id, "version": docs[doc_id]["version"],
                                               "data": {"tags": tags, "adIds": merged_ids, "description": desc,
                                                        "updatedAt": dt.datetime.now().astimezone().isoformat()}})
            else:
                plan["ads_new"].append({"doc_id": doc_id, "file": ads[0]["file"], "data": {
                    "title": f"Pub Meta · {theme(text)}", "audience": pg["audience"], "also": [],
                    "category": "visuel", "status": "publie",
                    "url": f"https://www.facebook.com/ads/library/?id={ad_ids[0]}",
                    "description": desc, "owner": "", "due": "",
                    "tags": ["meta ads", pg["name"]] + (["en diffusion"] if active else []),
                    "links": [pg["landing"]] if pg.get("landing") else [], "metrics": [], "source": "Meta",
                    "thumbId": "<ID DE L'IMAGE ENVOYÉE>", "thumbAuto": None,
                    "adIds": ad_ids, "adPage": pg["pageId"], "exemple": False,
                    "createdAt": dt.datetime.now().astimezone().isoformat(),
                    "updatedAt": dt.datetime.now().astimezone().isoformat()}})

    json.dump(plan, open(os.path.join(HERE, "sync-plan.json"), "w"), ensure_ascii=False, indent=1)
    print(f"Vignettes à capturer : {len(plan['vignettes'])} · nouvelles pubs : {len(plan['ads_new'])} · pubs à mettre à jour : {len(plan['ads_update'])}")


if __name__ == "__main__":
    main()
