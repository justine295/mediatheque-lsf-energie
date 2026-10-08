# Médiathèque contenus · LSF Énergie

Bibliothèque privée de tous les contenus marketing LSF Énergie, classés par cible
(prescripteurs, installateurs, bénéficiaires, obligés, institutionnel, interne) et par
format (site, landing page, outils, visuels RS, vidéos, articles, plaquettes…).

Application en ligne : https://claude.ai/artifact/SrdVy9pzpHy25Spsg84cBY (accès privé + code).

## Contenu du dépôt

| Fichier | Rôle |
|---|---|
| `mediatheque-lsf.html` | L'application (vue d'ensemble, bibliothèque, cartographie, analytics) |
| `charte-lsf.css` | Tokens de la charte commune aux outils internes LSF |
| `sync-ga4.py` · `ga4-config.json` · `ga4-mapping.json` | Import quotidien des chiffres GA4 |
| `meta-ads.py` · `meta-pages.json` | Récupération des publicités de la bibliothèque Meta |
| `capture-vignettes.py` | Captures d'écran des pages pour les vignettes |
| `prepare-sync.py` | Prépare la synchro du jour (vignettes et pubs à ajouter) |

La clé du compte de service GA4 n'est pas dans le dépôt : elle reste dans
`~/.config/lsf/ga4-key.json` sur le poste qui fait tourner la synchro.

## Mise à jour

- **Données** (contenus, chiffres, vignettes, pubs) : synchro automatique chaque jour
  à 10 h par une tâche programmée Claude, directement dans la base de l'application.
- **Application** (`mediatheque-lsf.html`) : après une modification poussée sur `main`,
  Claude republie la page au même lien. La base de données n'est pas touchée.
