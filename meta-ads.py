#!/usr/bin/env python3
"""
Récupère les publicités d'une page Facebook dans la bibliothèque publicitaire Meta
(publique, sans connexion) : visuels + texte + dates + statut.

Usage : python3 meta-ads.py            -> toutes les pages de meta-pages.json
Sortie : pubs-meta/<slug>-<hash>.jpg  et  pubs-meta/ads.json
  ads.json = [{page, slug, id, file, hash, video, status, dates, text}, ...]
  Plusieurs publicités peuvent partager le même visuel (même hash).
"""
import hashlib
import html as H
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT = os.path.join(HERE, "pubs-meta")
URL = ("https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=FR"
       "&is_targeted_country=false&media_type=all&search_type=page"
       "&sort_data[direction]=desc&sort_data[mode]=total_impressions&view_all_page_id={}")


def dump(url):
    prof = tempfile.mkdtemp(prefix="lsf-meta-")
    p = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--window-size=1440,6000",
                          "--virtual-time-budget=20000", "--lang=fr-FR", f"--user-data-dir={prof}",
                          "--dump-dom", url], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        out, _ = p.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
    shutil.rmtree(prof, ignore_errors=True)
    return out.decode("utf8", "ignore")


def text_of(fragment):
    t = re.sub(r"<(br|/div|/p|/span)[^>]*>", "\n", fragment)
    t = H.unescape(re.sub(r"<[^>]+>", "", t))
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def parse(html):
    marks = [m.start() for m in re.finditer(r"ID dans la biblioth[eè]que|Library ID", html)]
    ads = []
    for i, start in enumerate(marks):
        seg = html[start: marks[i + 1] if i + 1 < len(marks) else start + 60000]
        txt = text_of(seg)
        ad_id = (re.search(r"(?:biblioth[eè]que|Library ID)\s*:?\s*(\d{8,})", txt) or [None, None])[1]
        if not ad_id or any(a["id"] == ad_id for a in ads):
            continue
        poster = re.search(r'<video[^>]*poster="([^"]+)"', seg)
        imgs = [H.unescape(u) for u in re.findall(r'<img[^>]*src="(https://scontent[^"]+)"', seg)]
        imgs = [u for u in imgs if not re.search(r"[sp](?:60|64|80|100|148)x(?:60|64|80|100|148)", u)]
        src = H.unescape(poster.group(1)) if poster else (imgs[-1] if imgs else None)
        body = txt.split("Sponsorisé", 1)[1] if "Sponsorisé" in txt else txt
        dates = (re.search(r"(Début de diffusion le [^\n]+|\d+ \S+ \d{4} - \d+ \S+ \d{4})", txt) or [""])[0]
        ads.append({
            "status": "Actif" if dates.startswith("Début") else "Inactif",
            "id": ad_id,
            "src": src,
            "video": bool(poster),
            "dates": (re.search(r"(Début de diffusion le [^\n]+|\d+ \S+ \d{4} - \d+ \S+ \d{4})", txt) or [""])[0],
            "text": body.strip()[:1500],
        })
    return ads


def main():
    pages = json.load(open(os.path.join(HERE, "meta-pages.json")))
    os.makedirs(OUT, exist_ok=True)
    all_ads = []
    for pg in pages:
        ads = parse(dump(URL.format(pg["pageId"])))
        if not ads:  # chargement parfois incomplet : une seconde tentative
            ads = parse(dump(URL.format(pg["pageId"])))
        ok = 0
        for a in ads:
            if not a["src"]:
                continue
            try:
                raw = urllib.request.urlopen(urllib.request.Request(a["src"], headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
            except Exception:
                continue
            h = hashlib.md5(raw).hexdigest()[:10]
            fn = os.path.join(OUT, f"{pg['slug']}-{h}.jpg")
            if not os.path.exists(fn):
                open(fn, "wb").write(raw)
            a.update(page=pg["name"], slug=pg["slug"], file=os.path.relpath(fn, HERE), hash=h)
            a.pop("src")
            all_ads.append(a)
            ok += 1
        print(f"{pg['name']} : {ok} publicités, {len({x['hash'] for x in all_ads if x['slug']==pg['slug']})} visuels")
    json.dump(all_ads, open(os.path.join(OUT, "ads.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
