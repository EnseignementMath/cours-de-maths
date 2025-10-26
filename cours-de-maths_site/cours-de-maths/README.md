# cours-de-maths

Site de cours (GitHub Pages) pour publier automatiquement les séances depuis un `.ods`.

## Déploiement rapide

1. Créez un repo **public** sur GitHub nommé `cours-de-maths`.
2. Téléversez tous les fichiers de ce dossier à la racine du repo.
3. Dans **Settings → Pages**, choisissez **Deploy from branch** (`main / root`).
4. Votre site sera disponible à `https://<votre_compte>.github.io/cours-de-maths`.

## Publier depuis l'ODS

- Placez `cahier_de_texte.ods` à la racine du dépôt.
- Lancer localement :

```bash
pip install pandas odfpy jinja2
python build_site.py
git add . && git commit -m "maj" && git push
```

ou bien laissez GitHub Actions le faire automatiquement à chaque push (workflow fourni).

### Colonnes attendues (ODS)

- `date` (ex: 2025-11-07 ou 07/11/2025)
- `classe` (ex: 5e, 4e, 3e, 2nde)
- `chapitre`
- `titre`
- `resume` (optionnel)
- `lien_externe` (optionnel)
- `pieces_jointes` (optionnel, séparées par `;` — ex: `assets/5e/fiche1.pdf;assets/5e/fig1.png`)

## Publication d'une **sélection** depuis Calc (option)

- Utilisez la macro Calc pour exporter la **sélection** (avec en-tête) vers `%TEMP%\cahier_selection.json`,
- puis exécutez `publish_selection.py` (qui génère uniquement ces séances).

> Pensez à copier les pièces jointes dans `assets/...` et à référencer ces chemins dans l'ODS.

## Liens à mettre dans Pronote

- Pour chaque séance : `Contenu de la séance : https://<compte>.github.io/cours-de-maths/classes/<classe>/`
- Pour chaque devoir : intitulé + date, avec mention `Consigne détaillée sur le site`.

---

*Aucune donnée personnelle d'élève ne doit être publiée ici (noms, photos, notes).*
