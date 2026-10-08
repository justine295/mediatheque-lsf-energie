# Médiathèque LSF Énergie — consignes pour Claude

- Après chaque modification de `mediatheque-lsf.html` : commit, push sur `main`, puis
  republier l'artifact https://claude.ai/artifact/SrdVy9pzpHy25Spsg84cBY avec ce fichier
  (même chemin, sans changer les capabilities). Les deux doivent toujours correspondre.
- Ne jamais committer de secret : la clé GA4 vit dans `~/.config/lsf/`.
- Ne pas ajouter de suivi (GA4, pixels) sur les sites qui n'en ont pas.
- Charte : `charte-lsf.css` (identité commune avec l'outil de reporting).
