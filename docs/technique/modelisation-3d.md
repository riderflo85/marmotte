# Marmotte : modélisation 3D du boîtier

> **Statut** : version 1.1 du 2026-11-19, avec les réponses de l'auteur (outils D90, matériau et imprimante D91). Le boîtier se construit **en dernier**, une fois le projet fonctionnel (D80).
> **Rôle** : rassembler les contraintes et l'approche du boîtier imprimé qui cache les composants. Complète les specs techniques (`docs/technique/choix-techniques-et-architecture.md`, § 5).
> **Licence** des modèles 3D : **CC BY-NC-SA 4.0** (D56).

---

## 1. Objectif

Un **objet décoratif en forme de marmotte** (D48, D54), imprimé sur l'imprimante 3D de l'auteur, qui **cache le Pi, la caméra, les LED infrarouges, le micro et le capteur** (D16). L'installation sur place doit être rapide (§ 1.1 des notes), et l'objet propre, « pas un Pi nu sur une étagère ».

Le modèle de la marmotte sert aussi **dans l'app**, au format glTF : la même marmotte sur l'étagère et à l'écran (P58).

---

## 2. Composants à loger

Toutes les dimensions sont **à mesurer** sur les pièces réelles avant de modéliser.

| Composant | Dimensions de référence | Points d'attention |
|---|---|---|
| Raspberry Pi 4 | Carte de 85 × 56 mm ; trous de fixation M2,5 espacés de 58 × 49 mm | Chauffe ; prises USB-C (alimentation), Ethernet, jack, carte microSD |
| Boîtier alu à deux ventilateurs (s'il est gardé, D50) | À mesurer | Bruit capté par le micro ; il change le volume et l'aération (§ 6) |
| Caméra Quimat OV5647 avec ses deux cartes de LED infrarouges | Module caméra d'environ 25 × 24 mm ; largeur totale avec les LED à mesurer | **Bague de mise au point** à atteindre ; cellule photo des LED à laisser à la lumière ; nappe CSI vers le Pi |
| Micro INMP441 | Petit module, à mesurer | Orientation de l'ouverture du micro à vérifier sur le module |
| Capteur SHT31-D sur sa carte à broches | À mesurer | **Compartiment séparé**, au bout d'un câble de 30 à 50 cm (P61) |
| Bouton de réinitialisation | Bouton poussoir de 6 × 6 mm typiquement | Accessible avec un trombone seulement (P43) |
| Étiquette | Format à définir avec l'outil de préparation | Collée sous le boîtier, lisible et scannable (P47) |

---

## 3. Contraintes

| Contrainte | Origine |
|---|---|
| **Aérer le Pi** (fentes, circulation d'air), de préférence **sans ventilateur** | P33, D50 |
| **Fenêtre pour la caméra et les LED IR** ; garder discrète la faible lueur rouge des LED | § 6.1 des notes |
| **Accès à la bague de mise au point**, au moins au montage | Caméra à mise au point réglable |
| **Ouverture pour le micro**, loin des sources de bruit du Pi (ventilateurs) | D19, D20 |
| **Capteur isolé de la chaleur** du Pi et des LED IR : compartiment séparé et ventilé (oreille, queue ou socle de la marmotte) | § 6.8, P61 |
| **Sorties de câbles** : alimentation USB-C, Ethernet | D13, D38 |
| **Prise jack** du Pi accessible (berceuse en V2) | D40 |
| **Carte microSD** accessible pour la reflasher, sans tout démonter | T9 (D71) |
| **Trou du bouton de réinitialisation** | P43 |
| **Emplacement de l'étiquette**, sous le boîtier | P47 |
| **Place prévue pour un module batterie** intégré plus tard (accus 18650) | D38 |
| **Pas de vis photo 1/4"** sous le boîtier, et une **rotule** pour orienter la caméra vers le lit | D47 |
| **Base stable** pour une pose directe sur un meuble | Proposé (§ 6.11 des notes) |
| **Câbles à plus d'un mètre du lit** (recommandation à sourcer) | Sécurité |
| **Dessin original** (à la main ou en code), pas un modèle tiers sous licence non commerciale, pour que l'auteur garde tous les droits sur l'objet | § 6.12 des notes |

---

## 4. Architecture proposée du boîtier

**Deux familles de pièces** (proposition de Claude) :

1. **Le châssis technique**, à l'intérieur : il porte le Pi, la caméra, le micro et le bouton, avec les fixations, les passages de nappe et de câbles, les fentes d'aération et l'insert du pas de vis 1/4". Pièces précises, sans recherche esthétique.
2. **La coque décorative** en forme de marmotte, qui vient se fixer sur le châssis (vis ou clips). Elle porte la fenêtre de la caméra (les yeux ou le ventre de la marmotte, par exemple), l'ouverture du micro et le compartiment du capteur.

Raisons : on peut **réimprimer ou redessiner la coque** sans toucher au châssis, et **tester le châssis** (chaleur, fixation, accès) avant d'avoir fini la forme décorative.

**Détails à prévoir** :

- **Pas de vis 1/4"-20** : un insert fileté posé à chaud ou un écrou prisonnier, dans la base.
- **Trappe d'accès** pour la carte microSD et la bague de mise au point.
- **Fenêtre de la caméra** : ouverte, ou dans un matériau transparent aux infrarouges (à tester : certains plastiques bloquent les infrarouges).
- **Capteur** dans une oreille, la queue ou un socle séparé, avec des ouïes, et une **paroi entre lui et le Pi**.
- **Micro** derrière une ouverture fine, avec si possible un joint souple pour limiter les vibrations du boîtier.

---

## 5. Outils de modélisation

### 5.1 Décision (D90)

- **Coque marmotte : Blender.** Forme organique libre, export glTF soigné pour l'app, modèle articulable pour l'animer (P58).
- **Premier boîtier rectangulaire et simple : Fusion 360**, possible. Il sert de **châssis** (§ 4) et de **boîtier d'essai**.
- **Points à savoir sur Fusion 360** (vérifiés le 2026-11-19) :
  - **Pas de version Linux** : il faut un PC sous Windows ou macOS, ou une solution de contournement (machine virtuelle, Wine), plutôt fragile.
  - **Licence « usage personnel »** : gratuite, renouvelable chaque année, aux fonctions limitées, **réservée à un usage non commercial**. Pour tout usage autre que personnel (§ 6.12 des notes), vérifier les conditions d'Autodesk ou redessiner le châssis.
  - **Alternative** sous Linux, libre et paramétrique : **FreeCAD**.
  - Sources : [All3DP, Fusion sous Linux](https://all3dp.com/2/fusion-360-for-linux-how-to-install-it/), [Fusion 360 pour Linux (projet archivé)](https://gh.r-mj.com/cryinkfly/Autodesk-Fusion-360-for-Linux).
- **Proposition de Claude** : le boîtier rectangulaire peut être imprimé **dès que le matériel est monté**, pour les tests de chaleur, de micro et de cadrage. La coque marmotte reste **en dernier** (D80).

### 5.2 Options étudiées

Première présentation, avant la décision D90. La recommandation de Claude était A, à cause de l'échéance.

| | **A. Tout en code Python (build123d ou CadQuery)** | **B. Châssis en code, coque sculptée dans Blender** | **C. OpenSCAD** |
|---|---|---|---|
| Principe | Châssis et coque décrits en Python, paramétrés (dimensions des composants en variables). La marmotte est **stylisée** : formes simples, facettes (« low-poly »). | Le châssis en Python (comme A) ; la coque **sculptée librement** dans Blender, puis rendue imprimable (épaisseurs, découpe en pièces). | Le châssis et la coque dans le langage d'OpenSCAD. |
| Pour | Langage déjà utilisé par le projet. **Précis** pour les ajustements. Versionnable dans Git (du texte). Modifier une dimension régénère tout. Export STL ou 3MF pour l'impression, et glTF pour l'app. Licences Apache 2.0. | **Forme organique libre** : une vraie marmotte, ronde et douce. Blender exporte un glTF soigné, et sait **articuler le modèle** pour l'animer dans l'app (clignement, tête qui tourne). | Très répandu pour les objets imprimables, nombreux exemples. |
| Contre | L'aspect est forcément **géométrique et stylisé**. Animer la marmotte dans l'app se limite à bouger des pièces séparées. | **Deux outils**, et Blender demande un apprentissage. Ajuster précisément une coque sculptée sur un châssis est délicat. Fichiers Blender binaires, moins pratiques dans Git. | Un langage de plus, sans gain sur A ; arrondis et formes douces malcommodes ; pas d'export glTF direct. |

L'auteur a retenu **Blender** pour la coque (proche de B), avec **Fusion 360** (ou FreeCAD) au lieu du code pour le premier boîtier rectangulaire.

---

## 6. Chaleur et matériaux

- Le Pi 4 chauffe, plus encore en compressant la vidéo, et les LED IR chauffent aussi. Le Pi ralentit vers 80-85 °C (P33).
- **Le PLA ramollit vers 55-60 °C** : à éviter pour les pièces proches du Pi. **PETG** tient vers 75-80 °C ; **ABS** et **ASA** vers 95-100 °C. Valeurs usuelles des fabricants de filament, **à vérifier** pour le filament utilisé.
- **L'imprimante utilisée imprime l'ABS** (D91) : c'est le meilleur choix pour le châssis, au plus près du Pi. Deux précautions :
  - la **CR-10S Pro est une imprimante ouverte**, sans caisson : l'ABS s'y déforme et se fend facilement sur les grandes pièces. Il faut un **caisson** (même artisanal) ou au moins un pare-courant d'air ; sinon, le **PETG** reste le repli ;
  - l'ABS dégage des **vapeurs à l'impression** : imprimer dans une pièce aérée, hors de la chambre du bébé.
- La **coque** décorative, plus loin de la chaleur, peut être en PETG, en ABS, ou en PLA si les mesures de température le permettent.
- **Mesures à faire** dans le boîtier fermé, en pleine charge (vidéo, LED IR, IA) pendant une heure : température du processeur (`vcgencmd measure_temp`), ralentissement éventuel (`vcgencmd get_throttled`), température de la coque au toucher.
- Si les ventilateurs du boîtier alu sont retirés (P33), le boîtier alu peut servir de dissipateur à l'intérieur du châssis.

---

## 7. Impression

- **Imprimante** : **Creality CR-10S Pro** (D91). Volume d'impression de **300 × 300 × 400 mm** : le boîtier tient en une seule pièce si besoin. Buse jusqu'à **260 °C** et plateau jusqu'à **110 °C** d'après la plupart des sources (fiche officielle non lue) : suffisant pour l'ABS (buse vers 230-250 °C, plateau vers 100-110 °C). Sources : [comparatif (Comparigon)](https://comparigon.com/fdm-printers/creality-cr-10s-pro), [fiche 3IDEA](https://www.3idea.in/assets/doc/Brochure/3D1/3IDEA-CRLT-CR10S-PRO.pdf), [ICAR-CNR](https://www.icar.cnr.it/attrezzature/printer-3d/).
- **Tolérances** : prévoir du jeu entre les pièces (environ 0,2 à 0,3 mm, à calibrer avec une pièce de test).
- **Orientation** des pièces pour limiter les supports, surtout dans les ouïes et les fentes.
- **Pièces de test** avant la coque complète : fixation du Pi, fenêtre de la caméra, insert du pas de vis, clips de la coque.

---

## 8. Étapes et vérifications

1. **Mesurer** tous les composants réels (§ 2) et noter les dimensions.
2. **Boîtier rectangulaire** (châssis, Fusion 360 ou FreeCAD) : impression en ABS, montage, **test thermique** d'une heure (§ 6).
3. **Coque marmotte** (Blender) : forme, impression, montage sur le châssis.
4. **Caméra** : cadrage du lit, netteté (bague), lueur des LED IR dans le noir.
5. **Micro** : le banc d'essai et une écoute du live, boîtier fermé : pas de bruit de ventilateur ni de résonance.
6. **Capteur** : comparaison avec un thermomètre de référence, boîtier fermé après une heure de fonctionnement ; réglage du décalage de correction si besoin (P62).
7. **Stabilité** : pose sur un meuble, sur un trépied, sur la rotule.
8. **Export glTF** de la marmotte pour l'app (P58).

---

## 9. Organisation dans le dépôt

Dans le dossier `hardware/` (P69) :

- les **fichiers sources** : le fichier Blender de la coque (`.blend`) et le boîtier rectangulaire (export **STEP** depuis Fusion 360 ou FreeCAD, plus le fichier natif) ; une note des dimensions mesurées des composants ;
- les fichiers pour l'impression (STL ou 3MF) et pour l'app (glTF, exporté depuis Blender) ;
- le câblage (broches GPIO utilisées) ;
- un fichier de licence CC BY-NC-SA 4.0 pour ce dossier (D56).
