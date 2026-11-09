# Publication C1 / C1 deployment

GitHub contient le code ; Streamlit héberge l'application exécutable. Le déploiement doit être lancé depuis le compte Streamlit qui a accès au dépôt.

GitHub stores the code; Streamlit hosts the executable application. Start deployment from the Streamlit account with access to the repository.

Paramètres / Settings:

```text
Repository: jmpuybouffat/ByteNDT-B014-TRUE-TWIN
Branch: publication/c1-3aubes-fr-en
Main file path: app.py
Python: 3.12
```

Après déploiement, vérifier / After deployment, check:

- Français puis English. / French then English.
- Le PA, l'A-scan, le PAUT et le nuage suivent le même tir. / PA, A-scan, PAUT and cloud follow the same shot.
- À 41/41, cocher la comparaison : 5/5 EDM de référence. / At 41/41, enable comparison: 5/5 reference EDMs.
- Notice PDF, rapport HTML et CSV des 3 485 lois focales accessibles. / PDF guide, HTML report and 3,485-law CSV accessible.

Application publiée : https://bytendt-lsb941-c1-fr-en.streamlit.app/

Published application: https://bytendt-lsb941-c1-fr-en.streamlit.app/


## Reprise si une ancienne scène reste affichée

Un rafraîchissement navigateur ne prouve pas que le serveur Streamlit utilise la nouvelle révision. Dans Manage app → Settings, vérifier Repository `jmpuybouffat/ByteNDT-B014-TRUE-TWIN`, Branch `publication/c1-3aubes-fr-en`, Main file path `app.py`, Python3.12. Ensuite Manage app → Reboot. Le marqueur attendu en haut est **C1 · Première gorge ·27,6mm ·R3**. La scène doit proposer **Volume3D calculé** et **Coupes sectorielle/skew**. Si ce marqueur manque, la nouvelle entrée n'est pas chargée.

The app reads and verifies the current assets against the published SHA256 manifest on each run. No previous-revision document cache is reused. Browser refresh alone is not a server deployment check.
