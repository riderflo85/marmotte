# Piste : EfficientAT pour la détection des pleurs

> **Statut : évolution V2, à ressortir si YAMNet ne suffit pas en conditions réelles** (décision de l'auteur du 2026-11-26). La V1 garde YAMNet. Au banc d'essai, sa seule fausse alerte qui revient vient d'une porte qui grince, et l'auteur l'accepte : elle peut signaler que quelqu'un entre dans la pièce. La V1 ne bloque pas cette piste : le modèle est caché derrière l'interface `Classifier`, et passer à un autre modèle ne toucherait que cette partie.

## Le besoin auquel elle répond

YAMNet (Google, 2019) est un modèle généraliste, moins précis que les modèles récents. Au banc du lot 2 (32 pleurs longs, 6 h de bruits de fond) :

- il note une porte qui grince 0,96 « Baby cry, infant cry » et 0,98 « Crying, sobbing ». Elle alerte à chaque passage, quel que soit le seuil essayé (de 0,3 à 0,6) : 4 fausses alertes en 6 h, soit 1,33 par 2 h ;
- le réglage retenu (seuil 0,5, 3 tranches sur 6) ne signale que 70 % des gémissements, 60 % des babillages et 70 % des rires ;
- le seuil de 0,5 tombe pile sur un des niveaux de score de YAMNet : la marge est nulle.

Si, à l'usage, YAMNet manque des pleurs ou se trompe trop souvent dans la vraie chambre, EfficientAT est le candidat suivant. Le détail des mesures est dans `docs/plans/resultats-tests-prealables.md`, section « Banc de détection ».

## EfficientAT en bref

- Une famille de modèles de reconnaissance de sons publiée en 2022 (dépôt `fschmid56/EfficientAT`), construits sur MobileNetV3, un réseau conçu pour les petits processeurs.
- Entraînés sur AudioSet, comme YAMNet : les catégories de bébé (« Baby cry, infant cry », « Whimper », « Babbling », « Baby laughter ») devraient exister aussi. À confirmer dans la liste des classes.
- Code sous licence **MIT** (vérifié le 2026-11-19). La licence des poids pré-entraînés reste **à vérifier** : aucune brique sous licence non commerciale (§ 6.12 des specs techniques).

Précision sur AudioSet (précision moyenne, mAP, sur toutes les catégories) :

| Modèle | Paramètres | mAP |
|---|---|---|
| YAMNet (V1) | — | 0,31 |
| EfficientAT `mn04_as` | 0,98 million | 0,432 |
| EfficientAT `mn10_as` | 4,88 millions | 0,471 |

La mAP porte sur les quelque 500 catégories d'AudioSet, pas sur les pleurs seuls : la comparaison reste indicative. Seul le banc d'essai dira si EfficientAT fait mieux sur les pleurs.

## Les difficultés connues

- **Pas de version prête pour le Pi** : les modèles sont publiés pour PyTorch, sans export ONNX ou LiteRT documenté. Il faut les convertir, puis vérifier que les scores ne changent pas.
- **Prétraitement à refaire** : le modèle attend un spectrogramme mel calculé avec PyTorch. Il faudra le refaire sans PyTorch (numpy, ou dans le graphe exporté), car PyTorch est trop lourd pour le Pi.
- **Fréquence d'entrée** : probablement 32 kHz, à vérifier. Marmotte lit le micro à 16 kHz pour YAMNet (`AlsaSource`) : il faudrait lire à 32 kHz (le `plug` d'ALSA sait convertir) ou rééchantillonner.
- **Extraits de 10 s** : les modèles sont entraînés sur des extraits de 10 secondes. Leur précision sur des tranches d'environ 1 seconde, nécessaires pour alerter en ~8 secondes (D24), reste à mesurer.
- **Charge** : à mesurer sur le Pi pendant le live. Référence YAMNet : 26,7 ms par tranche, 6 % d'un cœur (lot 0).

## Si on la ressort

1. Vérifier la licence du code **et des poids**.
2. Choisir le format et le moteur : ONNX avec ONNX Runtime (vérifier les roues ARM64 pour la version de Python du projet), ou conversion vers LiteRT, le moteur déjà utilisé pour YAMNet.
3. Refaire le prétraitement hors de PyTorch, et vérifier sur PC que les scores sont identiques à ceux du modèle d'origine.
4. Écrire `EfficientAtClassifier` derrière l'interface `Classifier` (`backend/marmotte/detection/classifier.py`), et déclarer le fichier du modèle dans `backend/models/models.toml` (URL, SHA-256, licence).
5. Comparer à YAMNet sur le même banc : pleurs longs manqués, fausses alertes sur 6 h, gémissements, babillages et rires signalés (`uv run python -m marmotte.detection.bench run`). Puis mesurer la charge sur le Pi pendant le live.
6. Garder le meilleur. Si c'est EfficientAT, ramener le garde-fou de la CI (`MAX_FALSE_ALERTS_PER_2H`) au niveau mesuré.

## Références

- Dépôt EfficientAT : <https://github.com/fschmid56/EfficientAT>
- Détection des pleurs (fonctionnement, banc, garde-fou de la CI) : `docs/features/detection-des-pleurs.md`
- Choix du modèle : `docs/technique/choix-techniques-et-architecture.md`, § 8 et tableau des choix (T4)
