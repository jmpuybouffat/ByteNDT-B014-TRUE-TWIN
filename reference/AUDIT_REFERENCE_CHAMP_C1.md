# Référence du champ acoustique — état au 9 novembre 2026

## C1 actuellement publié

Le calcul source `B014_TRUE_TWIN_LIVING_ENGINEERING_FINAL.py`, révision `9c5a7b4edea07050edc0bd937893608c69f767bc`, utilise les 64 éléments, les retards des 85 lois par position et `vectorized_coherent_gain`, puis des réponses géométriques et EDM synthétiques (`run_true_twin_scan`). Les résultats des 41 positions sont conservés. La tache dans la vue provient des échantillons UT ; elle n'est pas un champ de pression résolu.

Source : https://github.com/jmpuybouffat/ByteNDT-B014-TRUE-TWIN/blob/9c5a7b4edea07050edc0bd937893608c69f767bc/B014_TRUE_TWIN_LIVING_ENGINEERING_FINAL.py

## Bloc physique retrouvé, à raccorder sans mélange

Le dépôt `ByteNDT-LSB941-Digital-Twin` contient `engine/LSB941_US_DEMO_PART1_ACTIVE_SCAN_B006.py` et les résultats publics B006. `coherentFieldSheets` calcule des nappes de champ à partir des 64 éléments avec propagation harmonique et pondération 1/r. La fonction de réponse EDM combine des termes nommés Kirchhoff-like face, GTD-like pointes/bords et Born-like diffus, avec phases cohérentes. Ce sont des modèles réduits, pas une qualification d'un solveur élastique complet.

Source : https://github.com/jmpuybouffat/ByteNDT-LSB941-Digital-Twin/blob/main/engine/LSB941_US_DEMO_PART1_ACTIVE_SCAN_B006.py

La banque publique PA1/C1 examinée affiche 70 stations et 176 directions par station. Elle utilise une convention de faces et un repère distincts de la publication C1 actuelle. Les RF/FMC/TFM complets sont exclus du bundle public. Les deux jeux de résultats n'ont pas été substitués ni fusionnés. Le raccordement du champ incident et rétrodiffusé aux 41 positions/85 lois C1 n'est pas finalisé.

## Références de présentation

- Formation Alpha : https://byte-ndt-twin-formation-alpha.streamlit.app/ — présentation pédagogique ; le README indique des réponses heuristiques.
- Soudure P03 : https://byte-ndt-soudure.streamlit.app/ — module scalaire à ouverture finie, optique physique et Born faible, avec limitations explicites dans `plate_physics.js`.

Aucune enveloppe illustrative n'est présentée comme un résultat Green/Kirchhoff/Born/GTD. Il faut raccorder un même jeu de géométrie, d'ouvertures, de lois, de réponses et de champs avant de déclarer cette étape physique complète.
