#!/usr/bin/env python3
"""
Récupère les chiffres GA4 par page et par mois pour la Médiathèque LSF Énergie.

Sortie : ga4-export.json, une ligne par (propriété, site, page, mois) :
  {"property", "host", "path", "period": "AAAA-MM", "views", "clicks", "conversions"}
Claude rattache ensuite chaque ligne au contenu qui a la même URL et met à jour
la médiathèque.

Correspondance des colonnes :
  vues        = screenPageViews (vues de page)
  clics       = sessions (visites)
  conversions = keyEvents (événements clés GA4)

Pré-requis (une seule fois) :
  pip3 install --user google-auth requests
  Remplir ga4-config.json (voir ga4-config.example.json).

Usage :
  python3 sync-ga4.py            # 3 derniers mois
  python3 sync-ga4.py --months 6
"""
import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "ga4-config.json")
OUT = os.path.join(HERE, "ga4-export.json")
SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
API = "https://analyticsdata.googleapis.com/v1beta/properties/{}:runReport"


def month_start(d, back):
    y, m = d.year, d.month - back
    while m <= 0:
        m += 12
        y -= 1
    return dt.date(y, m, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=3)
    args = ap.parse_args()

    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import AuthorizedSession
    except ImportError:
        sys.exit("Bibliothèques manquantes : pip3 install --user google-auth requests")

    if not os.path.exists(CONFIG):
        sys.exit("ga4-config.json introuvable (copier ga4-config.example.json)")
    cfg = json.load(open(CONFIG))
    key = os.path.expanduser(cfg["key_file"])
    creds = service_account.Credentials.from_service_account_file(key, scopes=[SCOPE])
    session = AuthorizedSession(creds)

    today = dt.date.today()
    start = month_start(today, args.months - 1)
    rows = []
    for prop in cfg["property_ids"]:
        body = {
            "dateRanges": [{"startDate": start.isoformat(), "endDate": today.isoformat()}],
            "dimensions": [{"name": "yearMonth"}, {"name": "hostName"}, {"name": "pagePath"}],
            "metrics": [{"name": "screenPageViews"}, {"name": "sessions"}, {"name": "keyEvents"}],
            "limit": 10000,
        }
        r = session.post(API.format(prop), json=body, timeout=60)
        if r.status_code != 200:
            sys.exit(f"GA4 a refusé la requête pour la propriété {prop} : {r.status_code} {r.text[:300]}")
        for row in r.json().get("rows", []):
            ym, host, path = (d["value"] for d in row["dimensionValues"])
            views, sessions, keys = (float(m["value"]) for m in row["metricValues"])
            rows.append({
                "property": prop,
                "host": host.lower().removeprefix("www."),
                "path": path.split("?")[0].rstrip("/") or "/",
                "period": f"{ym[:4]}-{ym[4:]}",
                "views": int(views),
                "clicks": int(sessions),
                "conversions": int(keys),
            })

    json.dump(rows, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"{len(rows)} lignes GA4 écrites dans {os.path.basename(OUT)} ({start:%Y-%m} → {today:%Y-%m})")

    # Totaux mensuels par fiche, selon ga4-mapping.json -> ga4-updates.json
    mapping = json.load(open(os.path.join(HERE, "ga4-mapping.json")))
    totals, unknown = {}, set()
    for r in rows:
        rule = next((m for m in mapping["rules"] if m["host"] == r["host"]
                     and r["path"].startswith(m.get("path", "/"))), None)
        if not rule:
            if r["host"] not in mapping["ignored_hosts"]:
                unknown.add(r["host"])
            continue
        t = totals.setdefault(rule["content_id"], {}).setdefault(
            r["period"], {"period": r["period"], "views": 0, "clicks": 0, "conversions": 0})
        for k in ("views", "clicks", "conversions"):
            t[k] += r[k]
    updates = {cid: sorted(p.values(), key=lambda x: x["period"]) for cid, p in totals.items()}
    json.dump(updates, open(os.path.join(HERE, "ga4-updates.json"), "w"), ensure_ascii=False, indent=1)
    print(f"Fiches à mettre à jour : {', '.join(sorted(updates)) or 'aucune'}")
    if unknown:
        print(f"Domaines non rattachés (à ajouter dans ga4-mapping.json) : {', '.join(sorted(unknown))}")


if __name__ == "__main__":
    main()
