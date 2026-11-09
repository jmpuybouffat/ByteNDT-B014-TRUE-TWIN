# BYTE NDT — LSB941 C1 — TWIN FR / EN

Publication bilingue du cycle C1 dans le modèle à trois aubes : déplacement du PA, A-scan, construction progressive du PAUT encodé, nuage UT, candidats regroupés, validation finale, TFM/voxel et rapport.

Bilingual C1 publication replay in the three-blade model: PA motion, A-scan, progressive encoded PAUT, UT cloud, grouped candidates, final validation, TFM/voxel and report.

## Identification

| Élément / Item | Référence / Reference |
| --- | --- |
| Cas / Case | **C1 — PA sur EXTRADOS → gorge INTRADOS** |
| Positions | **41** |
| Matrice / Array | **8 × 8 — 64 éléments / elements** |
| Lois focales / Focal laws | **3 485** |
| Validation de référence / Reference validation | **5/5 EDM** |
| Langues / Languages | Français et English |
| Entrée Streamlit / Streamlit entry point | **`app.py`** |

Les calculs C1 d'origine ne sont pas modifiés. La publication rejoue leurs matrices et états validés ; elle ne calcule pas une nouvelle acquisition physique. Les candidats regroupés restent distincts des cinq correspondances EDM de référence. Le volume mécanique global est illustratif et ne valide pas le passage du scanner.

The original C1 computation is unchanged. This publication replays its verified matrices and states; it does not calculate a new physical acquisition. Grouped candidates are distinct from the five matched reference EDMs. The global mechanical volume is illustrative and does not validate scanner clearance.

## Déployer sur Streamlit / Deploy on Streamlit

Dans Streamlit Community Cloud, créer une application avec ces paramètres :

In Streamlit Community Cloud, create an app with these settings:

| Champ / Field | Valeur / Value |
| --- | --- |
| Repository | `jmpuybouffat/ByteNDT-B014-TRUE-TWIN` |
| Branch | `publication/c1-3aubes-fr-en` |
| Main file path | `app.py` |
| Python | `3.12` |

Application publiée : https://bytendt-lsb941-c1-fr-en.streamlit.app/

Published application: https://bytendt-lsb941-c1-fr-en.streamlit.app/

Aucun secret, chemin Windows ou accès à un dossier Téléchargements n'est requis. Les scripts et données sont embarqués ; la notice, le rapport et les CSV sont proposés via des fichiers Blob locaux au navigateur.

No secret, Windows path or Downloads-folder access is required. Scripts and data are bundled; the guide, report and CSVs are served as browser-local Blob files.

## Utilisation / Use

1. Choisir **Français** ou **English**. / Select **Français** or **English**.
2. Cliquer **Lecture / Play** : les vues suivent le même tir. / All views follow the same shot.
3. Après le tir 41, cocher la comparaison aux références pour afficher les cinq EDM correspondantes. / After shot 41, enable reference comparison to display the five matched EDMs.
4. Sélectionner une EDM pour les analyses TFM/voxel ; ouvrir le rapport ou télécharger les exports. / Select an EDM for TFM/voxel analyses; open the report or download exports.

La notice détaillée est dans [assets/NOTICE_C1_FR_EN.pdf](assets/NOTICE_C1_FR_EN.pdf).

The detailed guide is in [assets/NOTICE_C1_FR_EN.pdf](assets/NOTICE_C1_FR_EN.pdf).

## Exécuter localement / Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Périmètre / Scope

Cette branche contient la publication du **TWIN C1**. La construction des scanners C1/C2 et leur intégration en réalité virtuelle feront l'objet d'un dépôt distinct, après vérification des deux cas et du passage mécanique. Cette branche n'est pas un dossier de fabrication.

This branch contains the **C1 TWIN** publication. C1/C2 scanner construction and virtual-reality integration belong in a separate repository after both cases and mechanical clearance have been checked. This branch is not a manufacturing release.

## Continuité / Provenance

- Source C1 : `ByteNDT-B014-TRUE-TWIN`, révision `9c5a7b4edea07050edc0bd937893608c69f767bc`.
- Les assets validés FR/EN V02 sont copiés sans modification ; leurs empreintes sont conservées dans `reference/MANIFESTE_ASSETS_ORIGINAUX.json`.
- Les 53 fonctions du calcul source et les contrôles de continuité sont conservés dans `reference/`.
- `publication_view.py` adapte uniquement l'intégration HTML, les fichiers locaux et les liens de téléchargement pour Streamlit.

The verified FR/EN V02 assets are copied unchanged. Their hashes, original calculation source and continuity checks are retained in `reference/`. `publication_view.py` changes only HTML embedding, local resources and download links for Streamlit.

Three.js and Plotly are distributed under their included MIT licences.

## Lecture opérateur restaurée / Restored operator reading

La cartographie principale est de nouveau la vue bleue du générateur C1 d'origine, calibrée **3 mm = 50 % FSH**, avec les cinq EDM à leurs positions de référence. Dans ce rejeu connu, leurs étiquettes apparaissent au tir support correspondant. La trace encodée en dB reste disponible dans **Détails du signal**, sans modification.

The main cartography is again the original C1 blue operator view, calibrated **3 mm = 50% FSH**, with the five EDMs at their reference positions. In this known replay, their labels appear at the corresponding supporting shot. The encoded dB trace remains available in **Signal details**, unchanged.

La commande **Gorge C1 visée / C1 target groove** rétablit la vue rapprochée, les couleurs et l'opacité. La courbe rouge reprend les 41 points cibles source ; la direction verte relie la position PA à sa cible source. Aucun tableau de résultats, seuil ou point de trajectoire n'est modifié. Les contrôles de cette correction d'affichage figurent dans `reference/CONTROLE_RESTAURATION_OPERATEUR.json` et `reference/CONTROLE_CORRECTION_AFFICHAGE.json`.

## Accès directs / Direct access

Le bandeau donne accès au scan, aux indications, à la TFM, au voxel 3D, au rapport et à la notice en FR/EN. Les analyses et le rapport ouvrent directement les résultats finaux des 41 positions. Le sélecteur EDM parcourt les cinq analyses originales.

The navigation bar opens the scan, indications, TFM, 3D voxel, report and bilingual guide. Analyses and report open the final 41-position reference results. The EDM selector browses the five original analyses.

La rubrique mécanique de la rupture indique explicitement le module manquant : aucun calcul de criticité n’existe dans cette source C1. Matériau, ténacité, chargement et géométrie de fissure sont nécessaires avant intégration. Les extensions TFM/voxel ne sont pas des dimensions de fissure validées.

## Contact et coupe C1 — 09 novembre 2026

Le PA affiché est ancré sur la peau du maillage, séparément de l'origine UT virtuelle. Lecture anime 401 poses de surface avant d'afficher les acquisitions aux 41 positions. La coupe utilise les triangles réels de la racine ; les échantillons du tir courant et les directions UT sources y sont synchronisés. Le bouton 3D montre le contact avec une coupe visuelle des voisines. Les données numériques initiales sont inchangées. Le paquet unique `downloads/C1_FINAL_FR_EN.zip` contient aussi CSV/DXF/STEP d'étude du slot. Voir `reference/CONTACT_C1_METHODE.md` pour la méthode et ses limites mécaniques.
