#!/usr/bin/env python3
"""
Capture d'écran des pages des contenus pour les vignettes de la Médiathèque.

Entrée : vignettes-todo.json  -> [{"id": "<content_id>", "url": "https://..."}]
Sortie : vignettes/<content_id>.png (1440x900, haut de page) + vignettes-result.json
         {"<content_id>": "vignettes/<content_id>.png" | null si échec}

Usage : python3 capture-vignettes.py
"""
import json
import os
import shutil
import subprocess
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT_DIR = os.path.join(HERE, "vignettes")
TIMEOUT = 45  # secondes par page


def capture(url, dest):
    prof = tempfile.mkdtemp(prefix="lsf-chrome-")
    tmp = dest + ".tmp.png"
    if os.path.exists(tmp):
        os.remove(tmp)
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
         "--window-size=1440,900", "--virtual-time-budget=8000",
         f"--user-data-dir={prof}", f"--screenshot={tmp}", url],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    start, last = time.time(), -1
    try:
        # Chrome écrit la capture puis ne rend pas toujours la main : on attend un fichier stable.
        while time.time() - start < TIMEOUT:
            if proc.poll() is not None and os.path.exists(tmp):
                break
            if os.path.exists(tmp):
                size = os.path.getsize(tmp)
                if size > 0 and size == last:
                    break
                last = size
            time.sleep(1)
    finally:
        proc.kill()
        proc.wait()
        shutil.rmtree(prof, ignore_errors=True)
    if os.path.exists(tmp) and os.path.getsize(tmp) > 10000:
        os.replace(tmp, dest)
        return True
    if os.path.exists(tmp):
        os.remove(tmp)
    return False


def main():
    todo = json.load(open(os.path.join(HERE, "vignettes-todo.json")))
    os.makedirs(OUT_DIR, exist_ok=True)
    result = {}
    for item in todo:
        dest = os.path.join(OUT_DIR, f"{item['id']}.png")
        ok = capture(item["url"], dest)
        result[item["id"]] = os.path.relpath(dest, HERE) if ok else None
        print(("OK    " if ok else "ÉCHEC ") + item["id"] + "  " + item["url"])
    json.dump(result, open(os.path.join(HERE, "vignettes-result.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
