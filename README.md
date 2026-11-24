# Marmotte

**Un babyphone vidéo fait maison, qui garde tout à la maison.**

Une marmotte imprimée en 3D veille sur la sieste du bébé : caméra infrarouge, micro et capteur de température dans un Raspberry Pi 4. Quand le bébé pleure, les parents reçoivent une notification sur leur téléphone. Ils la touchent et arrivent sur le live, image et son. L'image et le son ne quittent jamais le réseau du lieu.

> **État du projet** : en construction. Les fonctions et les choix techniques sont arrêtés ; la première version est en cours. Rien n'est encore installable.

## Fonctions

- **Alerte quand le bébé pleure**, gémit, babille ou crie, grâce à une petite IA qui tourne sur le Pi. Les bruits de la maison ne déclenchent rien.
- **Live** image et son, avec moins d'une seconde de délai, en noir et blanc dans le noir, avec un zoom au doigt.
- **Modes Sieste et Surveillance silencieuse**, avec retour automatique en Sieste.
- **Choix des téléphones** qui reçoivent les alertes.
- **Température et humidité** de la chambre.
- **Surveillance de lui-même** : si un composant plante, il le relance et prévient.
- **Nomade** : configuration du Wi-Fi depuis le téléphone, sans écran ; partage de connexion dans les lieux publics.
- **Mises à jour à la demande**, avec retour automatique à la version précédente en cas d'échec.
- **Pas d'enregistrement, pas de cloud, pas de compte.**

## Matériel

- Raspberry Pi 4 et carte microSD de 32 Go
- Caméra OV5647 avec filtre IR-Cut et LED infrarouges
- Micro numérique I²S INMP441
- Capteur de température et d'humidité Sensirion SHT40 ou SHT41 (carte Qwiic / STEMMA QT)
- Un bouton poussoir (réinitialisation)
- Alimentation USB-C 5,1 V / 3 A, ou une batterie externe
- Une imprimante 3D pour le boîtier

## Installation (prévue)

Les étapes détaillées seront écrites avec le code. Dans les grandes lignes :

1. **Flasher** l'image Marmotte sur la carte microSD.
2. **Préparer le boîtier** avec l'outil fourni : il demande son propre nom de domaine chez [Infomaniak](https://www.infomaniak.com/) et un jeton d'API, crée le nom du babyphone et produit l'**étiquette** à coller sous le boîtier.
3. **Brancher** le babyphone. S'il ne connaît aucun réseau, il diffuse son propre Wi-Fi : scanner le QR code de l'étiquette, puis choisir le Wi-Fi du lieu.
4. **Installer l'app** sur l'écran d'accueil : depuis **Safari** sur iPhone (même si un autre navigateur est utilisé par défaut), depuis **Chrome** sur Android.
5. **Appairer** le premier téléphone avec le code de l'étiquette, puis inviter le second depuis l'app.

## Documentation

| Document | Contenu |
|---|---|
| [Présentation](docs/presentation.md) | Le projet, le pourquoi, ce qu'il fait |
| [Specs fonctionnelles](docs/fonctionnel/specs-fonctionnelles.md) | Ce que fait Marmotte, exigence par exigence |
| [Specs techniques](docs/technique/choix-techniques-et-architecture.md) | Architecture et raison de chaque choix technique |
| [Modélisation 3D](docs/technique/modelisation-3d.md) | Le boîtier imprimé |
| [Piste : tunnel WireGuard](docs/pistes/tunnel-wireguard.md) | Le live à distance, prévu pour la V2 |

Les identifiants **D…** (décisions) et **P…** (propositions) cités dans la documentation renvoient au journal des décisions du projet, qui n'est pas publié.

## Développement

Le dépôt est organisé en :

- `backend/` : services Python (Django + django-ninja, détection des pleurs avec YAMNet et LiteRT, notifications Web Push) ;
- `frontend/` : l'app (React, TypeScript, React Three Fiber) ;
- `system/` : préparation du système, services, go2rtc, construction de l'image A/B ;
- `hardware/` : modèles 3D en code et câblage ;
- `docs/` : la documentation.

Outils à installer une fois sur le poste de développement :

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python et dépendances du back) ;
- Node.js 24, de préférence avec [nvm](https://github.com/nvm-sh/nvm) (front) ;
- [just](https://just.systems), qui regroupe les commandes du dépôt : `uv tool install rust-just`, puis `just --list` ;
- les contrôles Git : `uvx pre-commit install` à la racine du dépôt. Ils vérifient le code avant chaque commit, pré-remplissent le début du message (`type(module): `) d'après la branche, et refusent un message hors convention.

Installation, configuration et lancement en développement : [`backend/README.md`](backend/README.md) pour le back, [`frontend/README.md`](frontend/README.md) pour l'app. Tout le lint : `just lint` ; tous les tests : `just test`. Le suivi des tâches se fait dans les **issues GitHub**.

**Contributions** : les contributions de code ne sont pas acceptées pour l'instant.

## Licences

- **Code** : [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/). C'est du **code source ouvert, à usage non commercial** : vous pouvez le lire, le copier, le modifier et le partager, mais pas l'utiliser à des fins commerciales. Ce n'est pas une licence « open source » au sens de l'Open Source Initiative.
- **Modèles 3D et documentation** : [Creative Commons BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.fr).

## Avertissement

Marmotte est un projet personnel. Ce n'est **ni un dispositif médical, ni un produit certifié**, et il ne remplace pas la surveillance d'un adulte. Une notification peut arriver en retard ou ne pas arriver (économie d'énergie du téléphone, mode Ne pas déranger, coupure d'internet). Gardez les câbles **hors de portée du bébé**, à plus d'un mètre du lit.
