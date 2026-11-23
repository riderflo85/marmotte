# Lot 0 : préparation et tests préalables — plan détaillé

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Ce lot se fait surtout à la main** (matériel, téléphones) : Claude prépare les commandes et les fichiers, l'auteur les exécute sur le Pi et les téléphones et rapporte les résultats.

**Goal:** lever les risques qui pourraient remettre en cause un choix technique avant d'écrire le code qui en dépend.

**Architecture:** tests jetables (« spikes ») sur le Pi 4, hors du dépôt, sauf le rapport de résultats. Rien n'est gardé de ces essais, sauf ce qu'ils apprennent.

**Tech Stack:** Raspberry Pi OS Lite 64 bits (Trixie), rpicam-apps, go2rtc (binaire arm64), domaine et API Infomaniak, ALSA, ai-edge-litert, YAMNet, image Mender pré-convertie.

**Spec:** `docs/technique/choix-techniques-et-architecture.md` § 20.1 (tests préalables et règle d'arrêt), § 5 (matériel), § 7 (live), § 11 (nom et HTTPS).

## Global Constraints

- Voir `docs/plans/2026-11-19-plan-directeur-v1.md`, « Global Constraints ».
- Les essais tournent sur le **Pi de développement** (le Pi 4) ; rien de ces essais n'entre dans le dépôt, sauf `docs/plans/resultats-tests-prealables.md`.
- Le jeton d'API Infomaniak créé ici est un **secret** : il reste sur le PC de l'auteur et sur le Pi, jamais dans le dépôt.
- **Règle d'arrêt** (§ 20.1) : si un test échoue malgré les parades listées dans sa tâche et que l'échec remet en cause T2, T3, T4, T6 ou T9, Claude s'arrête et revient vers l'auteur avant le lot qui en dépend.

## Review Focus

1. **Box de la maison qui filtre les réponses DNS privées** : le test doit distinguer « la box bloque » de « le nom n'existe pas » (comparaison avec un résolveur public, tâche 3).
2. **Safari qui refuse le flux H.264 de la puce** alors que Chrome l'accepte : tester sur **les deux** téléphones, pas seulement sur le PC (tâche 4).
3. **Ralentissement thermique** pendant l'heure d'endurance : relever `vcgencmd get_throttled` à la fin, pas seulement au début (tâches 4 et 6).
4. **Un seul lecteur du micro à la fois** : le test `dsnoop` doit lancer **deux** lectures simultanées (tâche 5).
5. **Caméra absente avec U-Boot** dans la chaîne de démarrage de l'image Mender : vérifier la caméra, pas seulement le démarrage (tâche 7).

---

### Task 1: Achats

**Files:** aucun.

- [ ] **Step 1: Commander le matériel manquant** (§ 5 des specs techniques, § 18.1)
  - micro numérique I²S **INMP441** (en prendre deux : soudure ratée, test de placement) ;
  - capteur **Sensirion SHT40 ou SHT41** sur carte à connecteur **Qwiic / STEMMA QT** (SHT45 si l'écart de prix est négligeable) ;
  - un **câble Qwiic vers broches femelles** (« Qwiic to female jumper ») de 30 à 50 cm ;
  - un **bouton poussoir** 6 × 6 mm ;
  - deux **cartes microSD de 32 Go** (une pour le développement, une pour l'essai Mender de la tâche 7) ;
  - une **alimentation USB-C 5,1 V / 3 A** si celle du Pi n'est pas l'officielle.
- [ ] **Step 2: Noter les dates de livraison** dans le rapport (tâche 8) : elles conditionnent les tâches 5 et 6.

---

### Task 2: Préparer le Pi de développement

**Files:** aucun dans le dépôt.

- [ ] **Step 1: Flasher Raspberry Pi OS Lite 64 bits (Trixie)** avec Raspberry Pi Imager : nom d'hôte `marmotte-dev`, utilisateur, clé SSH, Wi-Fi de la maison.
- [ ] **Step 2: Relever l'identité du Pi**

Run: `cat /proc/device-tree/model; echo; free -h; python3 --version; uname -m`
Expected: `Raspberry Pi 4 Model B Rev 1.x`, la mémoire totale, `Python 3.13.x` (celui du système ; le projet utilisera 3.14 installé par uv), `aarch64`. Si la révision est **1.1**, noter qu'il ne faut pas de câble USB-C « e-marqué » (§ 6.9 des notes).

- [ ] **Step 3: Vérifier la caméra**

Run: `rpicam-hello --list-cameras`
Expected: une caméra `ov5647` listée. Sinon, ajouter `camera_auto_detect=0` et `dtoverlay=ov5647` dans `/boot/firmware/config.txt`, redémarrer, recommencer.

- [ ] **Step 4: Vérifier l'alimentation**

Run: `vcgencmd get_throttled`
Expected: `throttled=0x0`.

---

### Task 3: Test « DNS rebinding » (condition de T6)

**Files:** aucun dans le dépôt.

**Ce qu'on vérifie** : un nom public (domaine de l'auteur chez Infomaniak, D93) qui pointe vers l'IP privée du Pi est-il résolu par les réseaux habituels ?

- [ ] **Step 1: Acheter le domaine et créer le jeton** chez Infomaniak (D93) : compte avec **double authentification** ; un domaine **sans nom de famille** (P39), de préférence en `.fr` ; renouvellement automatique activé ; jeton d'API avec les droits **`dns:read`** et **`dns:write`**. Procédure détaillée et choix des options : § 10.7 des notes, « Procédure Infomaniak ». Garder le domaine et le jeton dans le gestionnaire de mots de passe de l'auteur.
- [ ] **Step 2: Faire pointer le nom vers l'IP du Pi** : dans le Manager d'Infomaniak, zone DNS du domaine, ajouter un enregistrement **A** `bebe` → IP locale du Pi (`hostname -I` sur le Pi), **TTL 60 s**.

Run (sur le PC) : `dig +short bebe.<domaine> @9.9.9.9`
Expected: l'IP locale du Pi (attendre une à deux minutes après la création si rien ne s'affiche).

Run (facultatif, vérifie le jeton qui servira au lot 7) : `curl -s -H "Authorization: Bearer <jeton>" "https://api.infomaniak.com/2/zones/<domaine>/records"` (chemin **à vérifier** dans la doc de l'API)
Expected: une réponse JSON qui liste les enregistrements, dont `bebe`.

- [ ] **Step 3: Servir une page de test sur le Pi**

Run (sur le Pi) : `mkdir -p /tmp/t && echo "Marmotte OK" > /tmp/t/index.html && python3 -m http.server 8000 -d /tmp/t`
Expected: le serveur écoute sur le port 8000.

- [ ] **Step 4: Comparer la box et un résolveur public** (depuis le PC, sur le Wi-Fi de la maison)

Run: `dig +short bebe.<domaine> @<IP de la box>` puis `dig +short bebe.<domaine> @9.9.9.9`
Expected: **les deux** renvoient l'IP privée du Pi. Si seule la seconde la renvoie, **la box bloque** (protection « DNS rebinding »).

- [ ] **Step 5: Tester depuis les téléphones**, en ouvrant `http://bebe.<domaine>:8000` dans **Safari** (iPhone) et **Chrome** (Android), sur chaque réseau disponible :
  - Wi-Fi de la maison ;
  - partage de connexion de l'iPhone, Pi et Android connectés dessus (relancer l'étape 2 avec la nouvelle IP du Pi) ;
  - partage de connexion de l'Android, de même ;
  - Wi-Fi d'un autre lieu, à la première occasion.

Expected: « Marmotte OK » partout. Noter aussi si **iCloud Private Relay** est actif sur l'iPhone et si la page s'ouvre quand même.

- [ ] **Step 6: En cas d'échec, essayer la parade** : sur Android, Paramètres → Réseau → **DNS privé** → `dns.quad9.net` ; sur iPhone, un profil DNS chiffré. Refaire l'étape 5 sur le réseau en échec.
- [ ] **Step 7: Appliquer la règle d'arrêt** : si la **box de la maison** bloque et que la parade ne suffit pas, arrêt et retour vers l'auteur (T6 serait à revoir).

---

### Task 4: Endurance de go2rtc avec la caméra (condition de T2)

**Files:** `~/go2rtc/go2rtc.yaml` sur le Pi (hors dépôt).

- [ ] **Step 1: Installer go2rtc** : télécharger la dernière version `go2rtc_linux_arm64` depuis <https://github.com/AlexxIT/go2rtc/releases>, la rendre exécutable dans `~/go2rtc/`.
- [ ] **Step 2: Écrire la configuration d'essai**

```yaml
streams:
  bebe:
    - "exec:rpicam-vid -t 0 -n --inline --codec h264 --width 1920 --height 1080 --framerate 25 --bitrate 3000000 --profile baseline --intra 50 -o -"
```

- [ ] **Step 3: Lancer go2rtc** : `./go2rtc_linux_arm64 -c go2rtc.yaml`. Expected : le journal annonce l'API sur le port 1984 et WebRTC sur le port 8555.
- [ ] **Step 4: Ouvrir le live sur les deux téléphones** : `http://<IP du Pi>:1984/stream.html?src=bebe&mode=webrtc` dans Safari (iPhone) et Chrome (Android), en même temps. Expected : image sur les deux.
- [ ] **Step 5: Vérifier l'absence de recompression**

Run: `ps aux | grep -E "ffmpeg|rpicam" | grep -v grep; top -b -n 1 | head -15`
Expected: `rpicam-vid` tourne, **aucun `ffmpeg`** ; go2rtc consomme peu de processeur (quelques pour cent).

- [ ] **Step 6: Mesurer le délai** : filmer un chronomètre affiché sur le PC à côté du live ; noter l'écart. Expected : **moins d'une seconde** (D45).
- [ ] **Step 7: Laisser tourner une heure**, puis relever `vcgencmd get_throttled`, `vcgencmd measure_temp`, et l'état du live sur les deux téléphones. Expected : `throttled=0x0`, live toujours fluide, aucune coupure.
- [ ] **Step 8: Parades si le live se dégrade** : débit à 2 Mb/s (`--bitrate 2000000`), Wi-Fi 5 GHz, 720p (`--width 1280 --height 720`), profil `main` si Safari refuse `baseline`. Refaire l'étape 7.
- [ ] **Step 9: Appliquer la règle d'arrêt** : si l'heure ne tient pas malgré les parades, arrêt et retour vers l'auteur (repli possible : MediaMTX).

---

### Task 5: Micro INMP441 et micro partagé `dsnoop` (condition de T3, à réception du micro)

**Files:** `/boot/firmware/config.txt` et `/etc/asound.conf` sur le Pi (hors dépôt ; les versions retenues seront reprises au lot 11).

- [ ] **Step 1: Câbler le micro** : VDD → 3,3 V (broche 1) ; GND → GND (broche 6) ; SCK → GPIO 18 (broche 12) ; WS → GPIO 19 (broche 35) ; SD → GPIO 20 (broche 38) ; L/R → GND (canal gauche).
- [ ] **Step 2: Déclarer le micro** : ajouter `dtparam=i2s=on` et `dtoverlay=googlevoicehat-soundcard` à `/boot/firmware/config.txt`, redémarrer. (Overlay couramment utilisé pour l'INMP441, **à vérifier** ; alternative : `dtoverlay=adau7002-simple`.)

Run: `arecord -l`
Expected: une carte son de capture apparaît.

- [ ] **Step 3: Enregistrer 5 secondes**

Run: `arecord -D plughw:<carte>,0 -f S32_LE -r 48000 -c 2 -d 5 /tmp/test.wav && aplay /tmp/test.wav` (ou copier le fichier sur le PC pour l'écouter)
Expected: la voix est audible sur un des deux canaux.

- [ ] **Step 4: Définir le micro partagé** dans `/etc/asound.conf`

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

- [ ] **Step 5: Lancer deux lectures en même temps**

Run: `arecord -D micro -f S16_LE -r 16000 -c 1 -d 10 /tmp/a.wav & arecord -D micro -f S16_LE -r 48000 -c 1 -d 10 /tmp/b.wav; wait`
Expected: les **deux** fichiers contiennent la voix, sans erreur « device busy ».

- [ ] **Step 6: Ajouter le son au live** : dans `go2rtc.yaml`, ajouter au flux `bebe` la source `"ffmpeg:-f alsa -i micro#audio=opus"` (syntaxe exacte **à vérifier** dans la doc de go2rtc ; alternative : source `exec:ffmpeg ... -f rtsp {output}`). Expected : son et image synchronisés sur les deux téléphones.
- [ ] **Step 7: Parade et règle d'arrêt** : si `dsnoop` échoue, essayer **PipeWire** (D60). Si les deux échouent, arrêt et retour vers l'auteur.

---

### Task 6: Charge de YAMNet pendant le live (conditions de T4 et D22, après la tâche 5)

**Files:** `~/essai-yamnet/charge.py` sur le Pi (hors dépôt).

- [ ] **Step 1: Préparer l'environnement** : `uv venv --python 3.14 && uv pip install ai-edge-litert numpy`, puis télécharger le modèle YAMNet de classification au format LiteRT (entrée de 15 600 échantillons) et `yamnet_class_map.csv` depuis le dépôt `tensorflow/models`.
- [ ] **Step 2: Écrire `charge.py`** : lit le micro partagé (`arecord -D micro -f FLOAT_LE -r 16000 -c 1` en tube) par tranches de 15 600 échantillons avec un pas de 7 800, appelle le modèle, affiche toutes les 10 secondes le temps d'inférence moyen et au 95e centile, et le score de « Baby cry, infant cry ».
- [ ] **Step 3: Lancer le live (tâche 4) vers un téléphone et `charge.py` pendant 15 minutes**, en faisant jouer des pleurs (vidéo YouTube sur un autre appareil, essai local seulement, D81).

Expected: inférence moyenne **sous 100 ms** par tranche ; le score de pleur monte pendant les pleurs ; live toujours fluide ; `vcgencmd get_throttled` = `throttled=0x0` à la fin.

- [ ] **Step 4: Relever la charge totale** (`top`) et la température. Noter les chiffres dans le rapport.

---

### Task 7: Image Mender et caméra (risque de T9)

**Files:** aucun dans le dépôt.

- [ ] **Step 1: Télécharger l'image pré-convertie** « Raspberry Pi OS Trixie Lite » pour **Raspberry Pi 4** depuis <https://docs.mender.io/downloads/disk-images>, la flasher sur la **seconde** carte microSD.
- [ ] **Step 2: Démarrer le Pi dessus** et vérifier la caméra

Run: `rpicam-hello --list-cameras; lsblk`
Expected: `ov5647` listée malgré U-Boot dans la chaîne de démarrage ; `lsblk` montre les deux partitions système et la partition de données.

- [ ] **Step 3: Vérifier le client Mender**

Run: `mender-update --version`
Expected: une version 4.x ou plus récente.

- [ ] **Step 4: Remettre la carte de développement** dans le Pi.
- [ ] **Step 5: Appliquer la règle d'arrêt** : si la caméra n'est pas vue avec l'image Mender, arrêt et retour vers l'auteur (T9 serait à revoir).

---

### Task 8: Rapport des résultats

**Files:**
- Create: `docs/plans/resultats-tests-prealables.md`

- [ ] **Step 1: Rédiger le rapport** : pour chaque tâche 2 à 7, la date, le résultat (réussi, réussi avec parade, échec), les chiffres relevés (délai du live, processeur, température, temps d'inférence), et la configuration retenue (profil H.264, débit, overlay du micro, `asound.conf`).
- [ ] **Step 2: Mettre à jour les specs techniques** si un résultat change un détail (ex. profil H.264 retenu, overlay du micro) : § 7 et § 20.1 de `docs/technique/choix-techniques-et-architecture.md`.
- [ ] **Step 3: Commit** (une fois le dépôt créé au lot 1)

```bash
git add docs/plans/resultats-tests-prealables.md docs/technique/choix-techniques-et-architecture.md
git commit -m "docs(plans): record preliminary test results"
```
