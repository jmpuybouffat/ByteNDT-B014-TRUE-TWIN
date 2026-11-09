# Contact graphique et coupe C1 — 9 novembre 2026

Convention utilisateur : C1 INTRADOS → EXTRADOS, 41 acquisitions, 5 EDM. Les tableaux D, ANALYSIS, OPERATOR et DATA restent identiques au commit c895e28. Les CSV UT et le rapport source ne sont pas recalculés.

Le point PA source est une origine acoustique virtuelle ; il ne donne ni le centre du volume mécanique ni sa face de contact. Le contact affiché est obtenu en remontant la direction nominale depuis cette origine jusqu'à l'intersection avec la peau triangulée de la racine. La normale de ce triangle oriente le volume graphique. Les 401 poses intermédiaires sont recalculées par intersection, sans interpoler linéairement leurs points de contact. La surface d'appui colorée est découpée dans les triangles originaux, dans un domaine local 25 × 25 mm. Le contrôle de planéité par rapport aux triangles sources est fourni dans CONTROLE_CONTACT_SURFACE.json.

La forme graphique s'adapte au maillage à chaque pose : elle n'est pas le profil d'un sabot rigide fabriqué. Le maintien physique de 55°, le couplage, la rotule, les efforts et le passage entre aubes restent à vérifier lors du dimensionnement du scanner.

La coupe intersecte le plan local contenant la direction nominale et l'axe transversal avec les triangles de la racine. Les directions des lois sont projetées dans ce plan. Elle affiche les indications du tir courant seulement et les échantillons à moins de 3 mm du plan, afin de ne pas rabattre des indications de plans éloignés sur cette coupe. Le mode 3D conserve le contexte spatial et utilise une coupe visuelle des voisines pour rendre le contact visible.

La tache utilise exclusivement les échantillons du tir courant du nuage source, dans une porte d'affichage ±8 mm autour du parcours nominal vers la cible. Ce n'est ni un nouveau champ de pression calculé ni une nouvelle acquisition. Le nuage global et tous les résultats de détection restent conservés.

La lecture anime d'abord le déplacement sur la surface, puis affiche les résultats à l'arrivée au prochain tir. Les boutons de navigation directe vont directement à une position d'acquisition.

Les exports pour le slot sont des données d'étude : CSV de 401 positions/normales/tangentes, polyligne discrétisée STEP/DXF, et 41 profils plan/triangles DXF. La section DXF conserve les coordonnées 3D, avec un calque par tir. Les offsets de guidage, le rayon du suiveur, les jeux, la retenue et les collisions doivent être définis avant fabrication. Aucun slot fabriquable n'est qualifié par cette vue.
