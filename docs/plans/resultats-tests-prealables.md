# Résultats des tests préalables (lot 0)

L'auteur a fait les tests sur le Pi de développement les 22 et 23 novembre 2026, d'après le plan `docs/plans/2026-11-19-lot-0-preparation.md`. Les fichiers d'essai (scripts, enregistrements, journaux) restent hors du dépôt.

## Synthèse

| Tâche | Résultat | Choix confirmé |
|---|---|---|
| 1. Achats | Réussi, avec un écart : capteur SHT31-D au lieu du SHT40 | — |
| 2. Pi de développement | Réussi : Pi 4 Rev 1.4 de 8 Go, caméra vue, alimentation saine | — |
| 3. « DNS rebinding » | Réussi sur le réseau de la maison ; famille et partages de connexion pas encore testés | T6 (à la maison) |
| 4. Endurance de go2rtc | Réussi : 2 h fluides, délai sous 1 s | T2 |
| 5. Micro et `dsnoop` | Réussi après correction de la source son de go2rtc | T3 |
| 6. Charge de YAMNet | Réussi : 26,7 ms par tranche, 12 à 14 % du Pi au total | T4, D22 |
| 7. Image Mender et caméra | Réussi : caméra vue avec U-Boot ; client Mender absent de l'image | T9 (démarrage) |
| Hors plan : vision nocturne | Réussi : filtre IR-Cut piloté par GPIO 17 | — |

La règle d'arrêt n'a jamais été déclenchée.

## Tâche 1 : achats

- **Micro** : 3 INMP441, broches à souder.
- **Capteur** : 3 **SHT31-D**, achetés par erreur à la place du SHT40/41 à connecteur Qwiic. Ils restent utilisables :
  - précision de ±0,3 °C et ±2 % d'humidité, suffisante pour les plages de couleur du § 14 des specs ;
  - même adresse I²C (0x44) ;
  - pas de connecteur Qwiic : broches à souder et fils Dupont femelle-femelle de 30 à 50 cm.

  **D76 est à amender.**
- **Cartes microSD** : une de 64 Go pour le développement, plusieurs de 16 Go. Une 16 Go suffit pour l'image Mender, qui demande 8 Go.
- **Alimentation** : l'officielle du Pi 4. **Bouton poussoir** : déjà possédé.
- **Dates de livraison** : non relevées ; tout était reçu au début des tests.

## Tâche 2 : Pi de développement

- **Modèle** : `Raspberry Pi 4 Model B Rev 1.4`, 7,6 Gi de mémoire (modèle 8 Go), `aarch64`, Python 3.13.5 pour le système. La révision 1.4 n'est pas concernée par le refus des câbles USB-C « e-marqués », propre à la 1.1.
- **Caméra** : `ov5647 [2592x1944 10-bit GBRG]`, détectée sans `dtoverlay`. Modes : 640×480 à 62,5 i/s, 1296×972 à 46,3 i/s, 1920×1080 à 32,8 i/s, 2592×1944 à 15,6 i/s.
- **Alimentation** : `throttled=0x0`.

## Tâche 3 : « DNS rebinding »

- **Le nom** : domaine en `.fr` acheté chez Infomaniak, sans nom de famille (P39), avec le sous-domaine **`sentinelle`** au lieu de `bebe`. Le nom complet reste dans le gestionnaire de mots de passe de l'auteur, hors du dépôt, comme le jeton. Enregistrement A vers l'IP locale du Pi, TTL de 60 s.
- **Le test** : page affichée sur le Wi-Fi de la maison depuis deux PC, l'iPhone (Safari) et l'Android (Chrome). Les appareils passent par le DNS de la box : **la box ne bloque pas** un nom public qui pointe vers une IP privée.
- **`dig +short`** : la box comme le résolveur public 9.9.9.9 renvoient l'IP du Pi.
- **iCloud Private Relay** : non testé. L'option n'existe qu'avec iCloud+, et l'iPhone de test ne l'a pas. À tester avec un téléphone qui l'a.
- **Pas encore testés** : le Wi-Fi d'un autre lieu et les partages de connexion des deux téléphones.
  - L'auteur les fera quand l'app saura donner un Wi-Fi au Pi (lot 9).
  - Risque : si le DNS d'un opérateur mobile bloque, on ne le saura qu'après le lot 7. Le test peut se faire plus tôt en connectant le Pi au partage avec `nmcli`.
- **API d'Infomaniak**, testée avec Postman (jeton rangé dans le coffre de Postman, absent de l'export), base `https://api.infomaniak.com/2` :
  - `GET /zones/{zone}/records` liste les enregistrements ;
  - `GET /zones/{zone}/records/{id}` lit un enregistrement ;
  - `PUT /zones/{zone}/records/{id}` avec `{"ttl": 60, "target": "<IP>"}` le met à jour (réponse 200 en 2,7 s environ) ;
  - le jeton est refusé sur `/profile` (pas de droit `user_info`) : il est bien limité au DNS ;
  - pour le lot 7, retrouver l'`id` par le nom (`source` = `sentinelle`, `type` = `A`) au lieu de l'écrire en dur.

## Tâche 4 : endurance de go2rtc

- **Logiciel** : go2rtc 1.9.15 (arm64). Source `exec:rpicam-vid … --profile baseline --intra 50 …` en 1080p, 25 i/s, 3 Mb/s.
- **Affichage** : image sur Safari (iPhone) et Chrome (Android) en même temps. **Délai sous 1 s** (D45).
- **Charge sans le son** :
  - aucun `ffmpeg`, donc pas de recompression ;
  - go2rtc et rpicam-vid à 18 % d'un cœur chacun ;
  - Pi inactif à 91,7 %.
- **Endurance** : 30 min sur les téléphones (32,6 °C, `throttled=0x0`), puis **2 h** fluides sur deux PC, son compris. Le type d'écran ne change pas la charge du Pi : go2rtc transmet le H.264 sans le recompresser.
- **Profil H.264** : Safari accepte `baseline`. L'iPhone cible utilise **Brave** (D84). Sur iOS, Brave s'appuie sur le même moteur WebKit que Safari, donc le comportement devrait être le même ; à confirmer au lot 5.

## Tâche 5 : micro et `dsnoop`

- **Carte son** : câblage du plan (L/R relié à GND) avec `dtparam=i2s=on` et `dtoverlay=googlevoicehat-soundcard`. La carte de capture `sndrpigooglevoi` apparaît (carte 1). **Overlay confirmé.**
- **Partage** : avec l'`asound.conf` du plan (`dsnoop` en S32_LE, 48 kHz, 2 canaux, puis `plug`), deux lectures simultanées passent sans « device busy ».
- **Le micro n'émet que sur le canal gauche** (L/R à GND), le droit est un silence numérique. Une lecture en mono par `plug` fait la moyenne des deux canaux et perd 6 dB. Il faut lire en stéréo et garder le canal gauche, comme l'essai de la tâche 6.
- **Son du live** : la syntaxe du plan ne marchait pas, à cause de deux pièges de go2rtc (configuration corrigée plus bas) :
  1. `ffmpeg:-f alsa -i micro#audio=opus` tombe dans le gabarit « fichier » de go2rtc (`-re -i …`), et ffmpeg refuse la commande.
  2. `{input}` écrit dans la source d'un flux en fait un « gabarit » à l'adresse vide. ffmpeg n'est jamais lancé, et l'erreur n'apparaît qu'au niveau de journal `trace`. Seul indice : `/api/streams` montre un producteur `"url": ""`.

  **Solution** : déclarer un gabarit nommé `alsa` dans la section `ffmpeg:` et l'appeler par `#input=alsa`.
- **Source native `alsa:` de go2rtc : inutilisable ici.** Elle ouvre `/dev/snd/pcm…` directement, contourne donc `dsnoop` et prendrait le micro à la détection.
- **ffmpeg** est à installer (`sudo apt install ffmpeg`) : il est absent de Raspberry Pi OS Lite.
- **Serveur RTSP** : la source ffmpeg de go2rtc publie le son sur le serveur RTSP interne de go2rtc. Ce serveur doit rester actif, limité à `127.0.0.1` (§ 7.2 corrigé).

## Tâche 6 : charge de YAMNet pendant le live

**Le script** : `charge.py`, jetable et hors dépôt. Il fait tourner le modèle YAMNet « classification » au format LiteRT (SHA-256 `10c95ea3eb9a7bb4cb8bddf6feb023250381008177ac162ce169694d05c317de`) avec `ai-edge-litert` 2.4.0 sous Python 3.14 (via uv), sur 1 thread. Il lit le micro partagé en stéréo à 16 kHz, garde le canal gauche, et passe **toutes les tranches** à YAMNet, sans premier étage : c'est le pire cas.

**Les conditions** : live image et son vers deux PC ; pleurs joués par un téléphone, de 30 cm à 1,5 m du micro ; musique douce par moments. Durée : 20,6 min, soit 2 534 tranches.

| Mesure | Objectif | Résultat |
|---|---|---|
| Inférence par tranche | moyenne < 100 ms | moyenne 26,7 ms ; p95 29,1 ms ; max 35,1 ms |
| Charge du script | — | 6 % d'un cœur |
| Charge totale (`top`) | — | Pi inactif à 86,4 % : go2rtc 18,5 %, rpicam-vid 15,6 %, ffmpeg (son) 8,6 %, YAMNet 6 % d'un cœur ; 365 Mo de mémoire |
| Température | — | 46,8 °C au maximum |
| `get_throttled` | `0x0` | `0x0` |
| Score « Baby cry, infant cry » | monte pendant les pleurs | jusqu'à 0,92 |
| Live | fluide | fluide |

### Observations pour le lot 2

- **Aucune fausse alerte** : hors des pleurs (silence, parole, musique, clavier), aucune tranche n'a dépassé 0,5.
- **« Crying, sobbing »** sort souvent en tête pendant les pleurs, à côté de « Baby cry, infant cry ». **Proposition** : l'évaluer comme catégorie de pleur pendant le réglage des seuils (lot 2, tâche 8).
- **Musique de fond et distance** réduisent le nombre de tranches au-dessus de 0,5 : de 4 à 10 sur 21 par période de 10 s sans musique, une ou deux avec. Cet essai est pessimiste : un haut-parleur de téléphone est bien plus faible qu'un vrai bébé.
- **Le premier étage (P11) n'est pas nécessaire pour la charge** : YAMNet sur toutes les tranches ne coûte que 6 % d'un cœur.

### Niveau du micro

L'enregistrement `niveau.wav` contient 10 s de silence, puis de la parole à 1 m.

- **Le silence brut est à -50 dBFS**, bien au-dessus du bruit propre de l'INMP441 (vers -87 dBFS). Ce niveau vient de variations de pression très lentes, vers 1 à 2 Hz, inaudibles : 97 % de l'énergie du silence est sous 20 Hz. Le décalage continu est négligeable (-86 dBFS).
- **Après un filtre passe-haut à 60 Hz**, le silence descend à **-68 dBFS** et la parole à 1 m est à **-53 dBFS**, soit 15 dB d'écart.
- **À l'ouverture du micro**, les 2 premières secondes contiennent une forte variation lente : c'est le démarrage.
- **Conséquence pour le lot 2** : mesurer le niveau (bruit de fond, filet « hurlement ») **après un filtre passe-haut**, vers 60 à 100 Hz. Sinon, ces variations lentes cachent le vrai bruit de fond. YAMNet, lui, n'est pas gêné : il a bien classé ces moments en « Silence ».

## Tâche 7 : image Mender et caméra

- **L'image** : « Raspberry Pi OS Trixie Lite » 64 bits du 2026-10-06 pour Pi 4, pré-convertie par mender-convert 5.3.1. Flashée sur une carte de 16 Go avec Raspberry Pi Imager et le dépôt d'images de Mender (`https://docs.mender.io/releases/rpi_imager_schema.json`).
- **La caméra fonctionne avec U-Boot dans la chaîne de démarrage** : `rpicam-hello --list-cameras` liste `ov5647`, et `rpicam-still` prend une photo.
- **`lsblk`** montre la partition de démarrage, les deux partitions système (A/B) et la partition de données `/data`.
- **Le client Mender n'est pas dans l'image** : `mender-update` est introuvable et aucun paquet `mender` n'est installé.
  - La doc de Mender l'installe après coup (étape 6 de son guide Raspberry Pi), avec le paquet `mender-client4` de son dépôt APT, qui existe pour Trixie.
  - Nos choix ne changent pas. Au lot 11, notre image sera construite par mender-convert, qui sait installer le client (option `MENDER_CLIENT_INSTALL`, dont la valeur par défaut est à vérifier).
  - La version du client, le mode autonome (`mender-update install`) et le retour arrière seront vérifiés au lot 11.

## Hors plan : vision nocturne

- **Symptôme** : image bleue dans le noir. **Cause** : le filtre IR-Cut restait en position jour.
- **Caméra** Quimat (Amazon B07KG8Y8SV) : chaque carte LED infrarouge a sa photorésistance et s'allume seule dans le noir, mais **le filtre ne bascule pas tout seul**.
- **Commande du filtre** :
  - un trou métallisé non soudé, entouré d'un carré, à droite de l'objectif, entre les vis de la carte LED droite ;
  - il est à **1,8 V environ** : la logique de la caméra est en 1,8 V, il ne faut jamais y mettre 3,3 V ;
  - ligne au niveau bas = nuit (filtre retiré) ; ligne relâchée = jour.
- **Câblage** : trou, résistance de 1 kΩ, puis broche 11 du Pi (**GPIO 17**), en « drain ouvert » :
  - nuit : `pinctrl set 17 op dl` ; jour : `pinctrl set 17 ip pn` ; **jamais `op dh`**, qui enverrait 3,3 V ;
  - `gpio=17=ip,pn` dans `/boot/firmware/config.txt` fait démarrer en mode jour. Sans cette ligne, le tirage vers le bas de GPIO 17 par défaut lutte contre la remontée de la caméra, et le filtre peut rester à mi-course.
- **Essais** : 10 bascules sans position intermédiaire. `--saturation 0` dans `rpicam-vid` donne une image en noir et blanc.
- **Pour le lot 5** :
  - décider jour/nuit par logiciel (luminosité estimée ou gain dans les métadonnées de libcamera, avec hystérésis) ;
  - forçage manuel dans l'app ;
  - noir et blanc la nuit. Le changement de saturation demande sans doute de relancer `rpicam-vid` : à étudier.
- **Pour le lot 14** (boîtier) : un fil de plus entre la caméra et le Pi.

## Écarts par rapport aux documents

- Capteur SHT31-D au lieu du SHT40/41 : D76, § 5 et § 14 des specs, lot 10.
- Sous-domaine `sentinelle` au lieu de `bebe` ; flux go2rtc nommé `sentinelle` pendant les essais.
- Cartes de 64 Go (développement) et 16 Go (essai Mender) au lieu de deux cartes de 32 Go.
- Commande du filtre IR-Cut par GPIO 17 (§ 5).
- Son du live par ffmpeg seulement, avec le serveur RTSP interne actif sur `127.0.0.1` (§ 7.1 et 7.2).
- Micro lu en stéréo, canal gauche ; niveau mesuré après un filtre passe-haut (§ 7.3 et 8.1, lot 2).

Mis à jour dans `docs/technique/choix-techniques-et-architecture.md` : § 5, 7.1, 7.2, 7.3, 8.1, 14, 15 et 20.1.

## Impacts sur les lots suivants

- **Lot 2** (détection) :
  - `AlsaSource` doit lire en stéréo et garder le canal gauche, au lieu de demander du mono à `plug` (-6 dB) ;
  - `rms_dbfs` doit être calculé après un filtre passe-haut ;
  - « Crying, sobbing » est à évaluer au réglage des seuils.
- **Lot 5** (live) :
  - gabarit `alsa` et serveur RTSP en `127.0.0.1` ;
  - à essayer : remplacer `#raw=-ac 1`, qui fait aussi la moyenne avec le canal muet (-6 dB), par `#raw=-af pan=mono|c0=c0`, qui ne garde que le canal gauche. Autre piste, au niveau d'ALSA : un module `route` qui ne garde que le gauche pour tous les lecteurs ;
  - logique jour/nuit et noir et blanc ;
  - vérification sur Brave (iPhone).
- **Lot 7** (nom et HTTPS) : sous-domaine `sentinelle` ; enregistrement retrouvé par son nom.
- **Lot 10** (capteur) : SHT31-D.
- **Lot 11** (système et mises à jour) : client Mender à installer dans notre image ; la configuration retenue ci-dessous est à reprendre dans le script de préparation.
- **Lot 14** (boîtier) : fil de commande du filtre IR-Cut.

## Reste à tester (non bloquant)

| Test | Quand |
|---|---|
| Nom du babyphone sur le Wi-Fi d'un autre lieu et sur les partages de connexion des deux téléphones | Par l'auteur, quand l'app saura donner un Wi-Fi au Pi (lot 9), ou plus tôt avec `nmcli` |
| Live sur Brave (iPhone) | Lot 5 |
| iCloud Private Relay | Avec un téléphone qui a iCloud+ |
| Client Mender, mode autonome, retour arrière | Lot 11 |
| Autres lignes du § 20.1 (portail captif, PWA sur iPhone, partage de connexion de l'iPhone retrouvé, batterie) | Dans leurs lots |

## Configuration retenue

Ajouts à `/boot/firmware/config.txt` :

```
dtparam=i2s=on
dtoverlay=googlevoicehat-soundcard
gpio=17=ip,pn
```

`/etc/asound.conf`, tel que testé (`<carte>` = 1 sur le Pi de développement) :

```
pcm.micro_hw {
    type dsnoop
    ipc_key 4242
    slave { pcm "hw:<carte>,0"; format S32_LE; rate 48000; channels 2; }
}
pcm.micro {
    type plug
    slave.pcm "micro_hw"
}
```

Au lot 11, désigner la carte par son nom (`hw:CARD=sndrpigooglevoi,DEV=0`), pour ne pas dépendre de l'ordre de détection des cartes son.

`go2rtc.yaml` de l'essai :

```yaml
log:
  exec: debug

ffmpeg:
  alsa: "-f alsa -i {input}"

streams:
  sentinelle:
    - "exec:rpicam-vid -t 0 -n --inline --codec h264 --width 1920 --height 1080 --framerate 25 --bitrate 3000000 --profile baseline --intra 50 -o -"
    - "ffmpeg:micro#input=alsa#audio=opus#raw=-ac 1"
```

Commandes du filtre IR-Cut : `pinctrl set 17 op dl` (nuit) et `pinctrl set 17 ip pn` (jour).

## Banc de détection (lot 2)

Mesuré le 25 novembre 2026 sur le PC avec le banc `backend/bench/` (`uv run python -m marmotte.detection.bench run`, dans `backend/`), d'après la tâche 8 du plan `docs/plans/2026-11-19-lot-2-detection.md`. Les 127 sons viennent de Freesound, sous licence CC0 ou CC BY, et l'auteur les a vérifiés à l'écoute (crédits : `backend/bench/CREDITS.md`).

**Le banc** : 33 pleurs (dont 32 pleurs longs de plus de 8 s), 10 gémissements, 10 babillages, 10 rires, 8 cris, et 56 bruits de fond (75 min : pièce calme, conversation, fête, télévision, musique, cuisine, toux, animaux, bruits de la maison). Chaque son de bébé est rejoué entre 15 s de pièce calme (le bruit de fond a fini sa mise en route de 10 s) et 5 s de fin. Les bruits de fond s'enchaînent dans un ordre tiré au sort, à ±6 dB, jusqu'à **6 h**. Deux tirages indépendants (graine fixe 42) : ajouter un son de bébé ne change ni l'ordre ni le gain des bruits de fond.

**Un pleur long est signalé** si une alerte part dans les 8 s qui suivent son début. Les sons de bébé sont rejoués sans pause anti-rafale : une alerte plus tôt, sur le début du pleur, ne peut pas cacher un pleur long que la chaîne ne détecte pas. Les bruits de fond sont rejoués avec la pause, comme en vrai.

**Pourquoi 6 h** : sur 2 h, les bruits de fond ne passent qu'environ 1,6 fois, et le résultat dépend du tirage. Le même réglage donnait de 0 à 2 fausses alertes par 2 h selon la graine (6 graines : 1,99 ; 2,0 ; 0 ; 1,0 ; 0,99 ; 1,0). Sur 6 h, chaque bruit de fond passe environ 5 fois.

### Réglage retenu

| Réglage | Plan | Retenu |
|---|---|---|
| Catégories « pleur » | « Baby cry, infant cry » | + « Crying, sobbing » |
| Seuil (`THRESHOLDS`) | faible 0,5, moyenne 0,3, forte 0,15 | faible 0,7, **moyenne 0,5**, forte 0,3 |
| Fenêtre glissante | 2 tranches sur 4 | **3 tranches sur 6** |
| Premier étage (`gate_margin_db`) | 6 dB (3 dB dès la tâche 5, cf. registre du lot) | 3 dB |
| Pause anti-rafale | 60 s | 60 s |
| Filet « hurlement » | niveau 25 dB au-dessus du bruit de fond pendant 1 s, ou « Screaming » ≥ 0,5 | **« Screaming » ≥ 0,5 seulement**, avec sa propre pause de 60 s ; son alerte relance aussi la pause des pleurs |

### Rapport final

| Mesure | Objectif (D81) | Résultat |
|---|---|---|
| Pleurs longs manqués | 0 | **0 sur 32** ; alerte 2,1 s après le début en médiane, 7,8 s au plus |
| Fausses alertes | au plus 1 par 2 h | **4 en 6 h, soit 1,33 par 2 h : objectif pas encore tenu** (toutes dues à la porte qui grince) |
| Sons signalés (au moins une alerte) | — | pleurs 97 %, gémissements 70 %, rires 70 %, cris 62 %, babillages 60 % |

**Le garde-fou de la CI** (P67, décision de l'auteur) : la fusion est refusée si un pleur long est manqué, ou si les fausses alertes dépassent le niveau mesuré à ce réglage (4 en 6 h, `MAX_FALSE_ALERTS_PER_2H` dans `backend/marmotte/detection/bench/runner.py`). L'objectif D81 reste affiché dans le rapport du banc (« NOT met ») ; la piste pour l'atteindre est EfficientAT, derrière la même interface `Classifier` (D62).

**Premier passage, avec les réglages du plan** (2 h de fonds) : 1 pleur long manqué, 161 fausses alertes en 2 h, dont 157 du filet « hurlement » déclenché par le niveau.

### Sensibilités

Le banc mesure la sensibilité moyenne. Les seuils faible et forte l'encadrent, mais **aucun des deux ne tient le garde-fou** :

| Sensibilité | Pleurs longs manqués | Fausses alertes par 2 h | Gémissements, babillages, rires signalés |
|---|---|---|---|
| faible (0,7) | 4 sur 32 | 1,0 | 50 %, 40 %, 20 % |
| moyenne (0,5) | 0 | 1,33 | 70 %, 60 %, 70 % |
| forte (0,3) | 0 | 2,66 (porte, chat) | 90 %, 70 %, 90 % |

La sensibilité n'est pas encore réglable dans l'app ; avant de l'ouvrir, il faudra revoir ce qu'elle change (par exemple, ne jamais monter le seuil des pleurs).

### Autres réglages essayés

Sur 6 tirages de 2 h, aucun réglage ne tient à la fois « 0 pleur long manqué » et « au plus 1 fausse alerte par 2 h » :

| Seuil moyen, fenêtre | Pleurs longs manqués | Fausses alertes par 2 h (6 tirages) |
|---|---|---|
| 0,5, 3 sur 6 (retenu) | 0 | de 0 à 2, moyenne 1,16 |
| 0,4, 3 sur 6 | 0 | de 1 à 3, moyenne 1,66 |
| 0,4, 4 sur 7 ou 8 ; 0,5, 4 sur 8 | 1 ou 2 (`cry-346663`…) | 0 partout |
| 0,4 ou 0,5, 4 sur 6, ou 5 et 6 sur 8 à 10 | 2 à 5 | 0 partout |
| 0,3, 4 sur 6 à 8 | 1 (`cry-346663`) | 0 à 2 (chat) |
| 0,2, 4 sur 6 | 0 | 0 à 3 (porte, chat) |

Exiger 4 tranches positives fait disparaître la porte, mais fait manquer un vrai pleur ; le pleur manqué est l'erreur la plus grave (D23).

### Écarts et limites

- **Filet « hurlement » sur le niveau, retiré** (décision de l'auteur ; spec amendée, § 8.1 point 5 et F-20). Le bruit de fond monte lentement (0,1 dB/s), pour qu'un long pleur ne s'y fonde pas. Du coup, toute toux, casserole ou début de musique au-dessus d'un fond calme déclenchait le filet. Fausses alertes par 2 h, selon le réglage : 157 (25 dB pendant 1 s), 45 (35 dB pendant 1 s, avec sa propre pause), 31 (45 dB pendant 3 s, avec sa propre pause). Sans lui, 2 cris du banc ne passent plus par le filet : un bébé de 4 mois que YAMNet prend pour un chien, un enfant excité qui court.
- **Le filet sonnait à chaque respiration** : pendant un pleur de 100 s, il se réarmait entre deux souffles et passait outre la pause anti-rafale, soit 13 notifications. Il a désormais sa propre pause, et son alerte relance celle des pleurs : un pleur continu ne donne qu'une notification par pause (F-21).
- **La porte qui grince** (`background-household-346267`) donne toutes les fausses alertes : YAMNet la note 0,96 « Baby cry, infant cry » et 0,98 « Crying, sobbing ». Elle alerte à la plupart de ses passages, selon le gain tiré.
- **Gémissements et babillages** sont moins souvent signalés qu'avec le réglage du plan (90 % et 100 %) : c'est le prix des fausses alertes. Ils ne font pas partie des objectifs bloquants. Un pleur court (`cry-393769`, 6 s) ne donne aucune alerte.
- **Un son continu peu au-dessus du bruit de fond** finit par s'y fondre : le bruit de fond monte de 0,1 dB/s, et le modèle cesse de tourner quand l'écart passe sous 3 dB. Un pleur continu 6 dB au-dessus d'une musique n'est plus analysé après environ 30 s (une seule alerte sur 2 min). Les vrais pleurs ont des respirations qui font redescendre le bruit de fond ; à vérifier avec les enregistrements du bébé.
- **Le délai** de 7,8 s au plus tient dans le budget de 8 s, avec peu de marge.
- **Mesuré sur PC (x86)** : le job `detection` de la CI rejoue le banc aussi sur ARM, comme le Pi ; son premier passage dira si les résultats y sont les mêmes.
- **Les niveaux du banc ne sont pas ceux d'une vraie chambre** : chaque enregistrement a son propre gain. À reprendre avec les enregistrements du bébé, gardés en local (`python -m marmotte.detection.bench run --local`).
