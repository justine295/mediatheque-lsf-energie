#!/usr/bin/env python3
"""
Construit la version consultation (lecture seule) de la Médiathèque pour Cloudflare Pages.

Entrées :
  db-snapshot/contents/*.json      export ArtifactData de "contents"
  db-snapshot/meta/config.json     export ArtifactData de meta/config (formats)
  db-snapshot/meta/ga4.json        export ArtifactData de meta/ga4 (état de la synchro)
  consultation/img/<id>.<ext>      images et PDF de la médiathèque (Artifact read)
  mediatheque-lsf.html             l'application

Usage :
  python3 export-consultation.py --todo   -> consultation-assets-todo.json (ids à télécharger)
  python3 export-consultation.py          -> consultation/index.html, data.json, _headers
"""
import datetime as dt
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "db-snapshot")
OUT = os.path.join(HERE, "consultation")
IMG = os.path.join(OUT, "img")


def read(path, default=None):
    if not os.path.exists(path):
        return default
    raw = json.load(open(path))
    return raw.get("data", raw) if isinstance(raw, dict) and "data" in raw and "id" in raw else raw


def contents():
    out = []
    for f in sorted(glob.glob(os.path.join(SNAP, "contents", "*.json"))):
        d = read(f)
        d = dict(d)
        d["id"] = os.path.basename(f)[:-5]
        out.append(d)
    return out


def needed_ids(items):
    ids = set()
    for c in items:
        for k in ("thumbId", "fileId"):
            if c.get(k):
                ids.add(c[k])
        u = c.get("url") or ""
        if u.startswith("/_blob/"):
            ids.add(u[7:39])
    return ids


def local_assets():
    os.makedirs(IMG, exist_ok=True)
    return {os.path.splitext(f)[0]: f for f in os.listdir(IMG) if not f.startswith(".")}


def main():
    items = contents()
    need = needed_ids(items)
    have = local_assets()
    if "--todo" in sys.argv:
        todo = sorted(need - set(have))
        json.dump(todo, open(os.path.join(HERE, "consultation-assets-todo.json"), "w"), indent=1)
        print(f"{len(todo)} fichier(s) à télécharger sur {len(need)}")
        return

    # Nettoyage : images qui ne servent plus.
    for i, f in list(have.items()):
        if i not in need:
            os.remove(os.path.join(IMG, f))
            del have[i]

    data = {
        "exportedAt": dt.datetime.now().astimezone().isoformat(),
        "contents": items,
        "config": read(os.path.join(SNAP, "meta", "config.json"), {}) or {},
        "ga4": read(os.path.join(SNAP, "meta", "ga4.json")),
        "assets": {i: have[i] for i in need if i in have},
    }
    json.dump(data, open(os.path.join(OUT, "data.json"), "w"), ensure_ascii=False)

    page = open(os.path.join(HERE, "mediatheque-lsf.html"), encoding="utf-8").read()
    html = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<meta name="robots" content="noindex, nofollow">\n'
            '<style>[hidden]{display:none!important}body{margin:0}img{max-width:100%}</style>\n'
            '</head>\n<body>\n' + page + '\n</body>\n</html>\n')
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)
    open(os.path.join(OUT, "_headers"), "w").write(
        "/*\n  X-Robots-Tag: noindex, nofollow\n  Referrer-Policy: same-origin\n"
        "/data.json\n  Cache-Control: no-store\n")
    missing = sorted(need - set(have))
    print(f"Export : {len(items)} contenus, {len(data['assets'])} fichiers"
          + (f" · {len(missing)} manquant(s)" if missing else ""))


if __name__ == "__main__":
    main()
