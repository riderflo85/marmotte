# Marmotte : spécifications fonctionnelles

> **Statut** : version 1.1 du 2026-11-19, avec les réponses de l'auteur (F-43 et F-53 confirmées, textes des notifications à définir plus tard, Android 13).
> **Rôle** : décrire ce que fait Marmotte **du point de vue des parents**, exigence par exigence, avec pour chacune un critère vérifiable. Le « comment » est dans les specs techniques : `docs/technique/choix-techniques-et-architecture.md`.
> **Traçabilité** : les identifiants **Dxx** (décisions) et **Pxx** (propositions validées) renvoient au journal des décisions du projet (non publié).
> **Conventions** : **F-xx** = exigence fonctionnelle ; **NF-xx** = exigence non fonctionnelle ; « Critère » = ce qu'on vérifie pour la déclarer remplie.

---

## 1. Objet et périmètre

Marmotte est un babyphone vidéo et son, fait maison, pour **surveiller le bébé pendant ses siestes**, à la maison comme en déplacement (amis, famille, salle des fêtes, lieux publics). Il prévient les parents **quand le bébé pleure ou fait du bruit**, et leur permet de **regarder le live** à tout moment depuis leur téléphone.

**Dans la V1** : live image et son, détection des pleurs et notifications, modes Sieste et Surveillance silencieuse, température et humidité, configuration du Wi-Fi sans écran, appairage des deux téléphones, mises à jour avec retour arrière, boîtier imprimé.

**Hors V1** : voir § 14.

---

## 2. Utilisateurs et vocabulaire

**Utilisateurs** : les **deux parents** (D33), chacun avec son téléphone : un iPhone et un Android (D3, D84). Pas d'accès invité.

| Terme | Sens |
|---|---|
| **Babyphone** | Le boîtier Marmotte, posé dans la chambre |
| **App** | L'app Marmotte installée sur l'écran d'accueil du téléphone |
| **Téléphone appairé** | Un téléphone autorisé à utiliser le babyphone |
| **Destinataire** | Un téléphone appairé qui reçoit les alertes et les notifications d'information |
| **Alerte** | Notification envoyée quand le bébé pleure, gémit, babille, rit ou crie |
| **Notification d'information** | Changement de mode, panne, mise à jour, changement de destinataires |
| **Mode Sieste** | Image, son, écoute par l'IA et alertes actives |
| **Mode Surveillance silencieuse** | Image et son, sans alerte (ex. moment de jeu) |
| **Mode Maintenance** | Pendant une mise à jour |
| **Réseau de configuration** | Le Wi-Fi que diffuse le babyphone quand il ne trouve aucun réseau connu |
| **Étiquette** | L'étiquette collée sous le boîtier (QR code, mot de passe, adresse, code d'appairage) |

---

## 3. Installation et appairage

**F-01 Préparation du boîtier** (D71, P47, § 6.5 des specs techniques)
Avant la première utilisation, un outil sur le PC prépare la carte SD (image Marmotte, secrets propres au boîtier, nom du babyphone dans le domaine de son propriétaire) et produit l'**étiquette à imprimer** : QR code du réseau de configuration, son mot de passe, adresse de la page de configuration, code d'appairage initial.
*Critère* : la carte préparée démarre ; l'étiquette imprimée permet de rejoindre le réseau de configuration et d'appairer le premier téléphone.

**F-02 Connexion au réseau sans intervention** (P3, D13)
Au démarrage, le babyphone essaie l'**Ethernet**, puis les **Wi-Fi déjà connus**. Il retient chaque réseau utilisé.
*Critère* : dans un lieu déjà visité, le babyphone se connecte seul, sans aucune manipulation.

**F-03 Réseau de configuration** (D14, P4, P48, P49)
Si ni l'Ethernet ni aucun réseau connu ne répond **au démarrage**, au bout d'environ **45 secondes**, le babyphone diffuse son propre Wi-Fi, protégé par le **mot de passe de l'étiquette**. En s'y connectant (ou en scannant le QR code de l'étiquette), **la page de configuration s'ouvre toute seule** ; sinon, l'adresse de l'étiquette permet de l'ouvrir. La page liste les Wi-Fi visibles, permet de choisir le réseau du lieu et d'en saisir le mot de passe, puis explique au parent de remettre son téléphone sur ce même réseau.
*Critère* : sur iPhone et sur Android, la page s'ouvre seule ou par l'adresse de l'étiquette ; après saisie, le babyphone rejoint le réseau choisi et le retient.

**F-04 Installation de l'app** (D7, D84)
L'app s'installe sur l'écran d'accueil depuis le navigateur : **Safari sur iPhone** (même si Brave est le navigateur par défaut : Brave ne sait pas installer une app web sous iOS), **Chrome sur Android**. Une fois installée, elle s'ouvre comme une app, sans navigateur. Sur iPhone, l'installation est **obligatoire** pour recevoir les notifications.
*Critère* : l'app s'installe et s'ouvre en plein écran sur les deux téléphones ; le guide d'installation décrit le passage par Safari.

**F-05 Appairage du premier téléphone** (P40)
Dans l'app installée, on saisit le **code d'appairage initial** de l'étiquette. Ce code ne fonctionne **que si aucun téléphone n'est appairé**.
*Critère* : avec le code, le premier téléphone est appairé ; dès qu'un téléphone est appairé, le code initial est refusé.

**F-06 Ajout d'un téléphone** (P41)
Depuis un téléphone appairé, « **Ajouter un téléphone** » affiche un **QR code** (il ouvre l'adresse de l'app sur le nouveau téléphone, pour l'installer) et un **code à 6 caractères, valable 5 minutes, à usage unique**, à saisir **dans l'app installée** du nouveau téléphone. Le premier téléphone est prévenu quand l'appairage réussit.
*Critère* : le nouveau téléphone est appairé avec le code ; un code expiré ou déjà utilisé est refusé.

**F-07 Autorisation des notifications** (§ 6.3 des notes)
Après l'appairage, l'app explique à quoi servent les notifications puis demande l'autorisation, **à la suite d'un geste du parent** (exigence de l'iPhone). Elle conseille d'ajouter l'app aux exceptions des modes « Ne pas déranger » et « Concentration » du téléphone.
*Critère* : sur les deux téléphones, l'autorisation est demandée et une notification de test arrive.

**F-08 Retrait d'un téléphone** (P42, P26, P27)
Depuis n'importe quel téléphone appairé, la liste des téléphones permet d'en **retirer** un. Le **dernier destinataire des alertes ne peut pas être retiré en mode Sieste** (bouton grisé, avec l'explication). Le téléphone retiré reçoit une dernière notification.
*Critère* : un téléphone retiré n'accède plus à rien et affiche « Ce téléphone n'est plus appairé » (F-47).

**F-09 Réinitialisation** (P43)
Un **bouton caché** dans le boîtier, maintenu une dizaine de secondes, **efface tous les appairages** et réactive le code initial de l'étiquette.
*Critère* : après réinitialisation, aucun téléphone n'a accès, et le code initial permet d'appairer un nouveau premier téléphone.

**F-10 Protection des codes** (P44)
Après quelques essais de code erronés, le babyphone impose une attente avant d'accepter de nouveaux essais.
*Critère* : une série d'essais au hasard est ralentie puis bloquée temporairement.

---

## 4. Modes de surveillance

**F-11 Démarrage et compte à rebours** (D28, P20)
Quand le babyphone est **prêt** (caméra, micro et réseau opérationnels), un **compte à rebours de 30 secondes** démarre, affiché dans l'app (« Mode sieste dans 25 s »). Le **live est disponible pendant le compte à rebours**, pour orienter la caméra. À la fin, le babyphone passe en **mode Sieste**.
*Critère* : de la mise sous tension à la Sieste, l'app affiche « démarrage », puis le compte à rebours, puis « Sieste » ; le live fonctionne pendant le compte à rebours.

**F-12 Retour en Sieste après un redémarrage** (P21)
Après **tout redémarrage** (plantage, coupure brève), le babyphone repasse en Sieste après le compte à rebours.
*Critère* : un redémarrage provoqué en Surveillance silencieuse ramène en Sieste.

**F-13 Surveillance silencieuse** (D30, D32, P23)
Depuis l'app, on active la Surveillance silencieuse pour une **durée choisie** (ex. 30 min, 1 h). Image, son et mesures de température continuent ; **aucune alerte**, filet « hurlement » compris.
*Critère* : pendant ce mode, des pleurs et des cris ne déclenchent aucune alerte.

**F-14 Retour automatique en Sieste** (D32)
À la fin de la durée, le babyphone repasse **seul** en Sieste et envoie « **Mode sieste réactivé** ». On peut **prolonger** avant la fin.
*Critère* : à l'échéance, le mode change et la notification arrive ; la prolongation repousse l'échéance.

**F-15 Mode visible et partagé** (P22, P28)
Le mode en cours est **affiché en grand** dans l'app. Un changement de mode fait par un parent est **notifié aux destinataires**.
*Critère* : un changement de mode sur un téléphone produit une notification sur l'autre (s'il est destinataire) et l'affichage se met à jour.

**F-16 Mode Maintenance** (D46)
Pendant une mise à jour, le babyphone est en **Maintenance**, affiché dans l'app et notifié.
*Critère* : voir F-53.

---

## 5. Détection et alertes

**F-17 Ce qui déclenche une alerte** (D19, P10, D29)
En **mode Sieste uniquement**, les **sons de voix d'un bébé** : pleurs, gémissements, babillages, rires.
*Critère* : sur le banc d'essai, ces sons déclenchent une alerte (cf. NF-04).

**F-18 Ce qui ne déclenche pas d'alerte** (D19, P10)
Le bruit ambiant, les conversations, la musique, la télévision, les bruits d'objets (coup contre le lit, jouet qui tombe).
*Amendé le 2026-11-26 (banc d'essai, lot 2)* : au plus deux fausses alertes par tranche de 2 heures, au lieu d'une. YAMNet alerte sur une porte qui grince (1,33 fausse alerte par 2 h au banc, sur 6 h de bruits de fond) ; l'auteur l'accepte : elle peut signaler que quelqu'un entre dans la pièce.
*Critère* : sur le banc d'essai, au plus deux fausses alertes par tranche de 2 heures de bruits de fond (NF-04).

**F-19 Délai d'alerte** (D24, P18)
Un pleur qui dure est notifié **au plus environ 8 secondes après son début**. Un pleur peut passer inaperçu environ 5 secondes s'il est capté dans les 3 secondes suivantes.
*Critère* : sur le banc d'essai, l'alerte de chaque pleur de plus de 8 secondes part dans ce délai.

**F-20 Hurlement** (D25, P16, P17)
Un **hurlement n'est jamais raté**, même au prix d'une fausse alerte : une alerte part si le son dépasse **nettement le bruit de fond** pendant environ une seconde, ou si l'IA reconnaît un cri. Il **passe outre la pause anti-rafale**. Le seuil est relatif au bruit de fond du lieu, pour ne pas sonner sans arrêt en salle des fêtes.
*Amendé le 2026-11-25 (banc d'essai, lot 2)* : l'alerte ne part plus que si l'IA reconnaît un cri. Sur le niveau seul, elle donnait des dizaines de fausses alertes par sieste (toux, casseroles, musique). Elle garde sa propre pause, pour ne pas sonner à chaque respiration d'un long cri.
*Critère* : un cri fort déclenche une alerte même pendant la pause anti-rafale.

**F-21 Pas de rafale** (P12)
Un pleur qui dure déclenche **une notification, puis une pause** (durée réglable) avant la suivante.
*Critère* : un pleur continu de 2 minutes produit une première alerte, puis une seule par pause.

**F-22 Texte de l'alerte** (P14)
Le texte dit **ce qui a été entendu** et **l'heure** (§ 15).
*Critère* : les textes du § 15 sont utilisés.

**F-23 Sensibilité réglable** (P13)
La sensibilité de la détection se règle dans l'app.
*Amendé le 2026-11-26 (banc d'essai, lot 2)* : la sensibilité ne monte jamais le seuil des pleurs. Faible et moyenne gardent celui réglé sur le banc d'essai ; seule forte le baisse, pour des pleurs plus faibles. Elle règle surtout les autres sons du bébé (gémissements, babillages, rires).
*Critère* : sur le banc d'essai, aucune sensibilité ne manque un pleur de plus de 8 secondes, et la forte déclenche sur des pleurs plus faibles.

**F-24 Priorité des alertes** (P19)
Les alertes sont envoyées avec la **priorité haute** des notifications web.
*Critère* : vérifiable dans les journaux d'envoi.

**F-25 Toucher l'alerte ouvre le live** (D5)
Toucher une alerte ouvre l'app **directement sur le live**.
*Critère* : depuis l'écran verrouillé, une alerte touchée mène au live, image et son, sans autre manipulation (si le téléphone est sur le réseau du babyphone).

**F-26 Une alerte n'est jamais perdue** (P73)
Une alerte part même si un composant du babyphone (API, live, service de notifications) est en panne à ce moment-là.
*Critère* : service de notifications arrêté exprès, un pleur du banc d'essai produit quand même une alerte.

---

## 6. Live

**F-27 Accès au live** (D10, P6)
Seuls les **téléphones appairés** voient le live, et seulement depuis **le même réseau** que le babyphone (V1). Une autre personne sur le même Wi-Fi n'y a pas accès.
*Critère* : un téléphone non appairé sur le même Wi-Fi n'obtient ni l'image ni le son.

**F-28 Qualité du live** (D45)
Délai **inférieur à 1 seconde** ; **1080p à 25-30 images/s** si le Pi et le Wi-Fi suivent, sinon **720p** ; **noir et blanc la nuit** (infrarouge) ; **son mono** en qualité voix.
*Critère* : délai mesuré (chronomètre filmé) sous 1 seconde ; image et son nets et synchronisés.

**F-29 Zoom au doigt** (D45)
On zoome sur l'image en écartant deux doigts.
*Critère* : le zoom fonctionne sur les deux téléphones.

**F-30 Hors du réseau du babyphone** (P5)
Si le téléphone n'est pas sur le même réseau, l'app l'affiche clairement (« Tu n'es pas sur le réseau du babyphone ») au lieu d'un écran noir. Les **notifications arrivent partout**, tant que le babyphone a internet.
*Critère* : téléphone en 4G, l'app affiche le message ; une alerte arrive quand même.

**F-31 Caméra permanente ou à la demande** (D61)
Par défaut, la caméra reste **allumée en permanence** (live instantané, caméra surveillée). Un réglage permet de passer en **caméra à la demande** (allumée seulement quand quelqu'un regarde), par exemple sur batterie. L'app affiche alors « caméra en veille » au lieu d'une alerte.
*Critère* : en mode « à la demande », le live s'ouvre en quelques secondes et l'état ne signale aucune panne.

---

## 7. Destinataires des notifications

**F-32 Choix des destinataires** (D34, D35, P26)
On choisit quels téléphones appairés reçoivent les alertes. En mode Sieste, **au moins un** téléphone doit les recevoir : couper le dernier est impossible (bouton grisé, avec l'explication).
*Critère* : impossible de laisser zéro destinataire en Sieste.

**F-33 « Je prends les alertes »** (D36, P25)
Un bouton, en un geste, fait de ce téléphone **le seul destinataire**. Un réglage à côté permet « les deux ».
*Critère* : après le geste, seul ce téléphone reçoit les alertes.

**F-34 Gestion croisée** (P24)
Depuis n'importe quel téléphone appairé, on active ou coupe les notifications **des deux** téléphones (en V1, un téléphone hors du réseau ne peut pas joindre le babyphone : l'autre parent le fait pour lui).
*Critère* : le téléphone A retire le téléphone B des destinataires.

**F-35 Prévenir le téléphone retiré** (P27)
Un téléphone retiré des destinataires par l'autre reçoit une **dernière notification** : « Tu ne reçois plus les alertes du babyphone ».
*Critère* : la notification arrive sur le téléphone retiré.

**F-36 Notifications d'information** (P28)
Elles suivent **les mêmes destinataires** que les alertes.
*Critère* : un téléphone non destinataire ne reçoit pas les notifications d'information.

**F-37 Abonnement invalide** (P29)
Si un téléphone ne peut plus recevoir de notifications (app désinstallée, autorisation retirée), le babyphone le détecte, **prévient l'autre téléphone**, et l'app l'affiche. S'il ne reste **aucun destinataire valide**, l'app affiche une **grosse alerte** à l'ouverture.
*Critère* : autorisation retirée sur un téléphone, l'autre est prévenu au prochain envoi.

---

## 8. Température et humidité

**F-38 Mesures** (D17, D41, D43, P30)
Une mesure **au démarrage du mode Sieste**, puis **une par minute**, en Sieste comme en Surveillance silencieuse.
*Critère* : la valeur affichée se met à jour chaque minute.

**F-39 Affichage en couleurs** (D43, P31)
Température et humidité sont **seulement affichées** (pas d'alerte ni de courbe en V1), avec un code **vert / jaune / orange** à seuils fixes (**à sourcer**) :

| | Vert | Jaune | Orange |
|---|---|---|---|
| Température | 18 à 20 °C | 16 à 18 °C ou 20 à 22 °C | sous 16 °C ou au-dessus de 22 °C |
| Humidité | 40 à 60 % | 30 à 40 % ou 60 à 70 % | sous 30 % ou au-dessus de 70 % |

*Critère* : les couleurs correspondent aux seuils.

**F-40 Dernière mesure et capteur indisponible** (P32)
L'app affiche **l'heure de la dernière mesure**. Si le capteur ne répond plus, la valeur passe en **gris « capteur indisponible »**, sans notification.
*Critère* : capteur débranché, l'affichage passe en gris dans les deux minutes.

**F-41 Correction réglable** (P62)
Un **décalage de correction** (ex. −0,5 °C) se règle dans l'app, après comparaison avec un thermomètre de référence.
*Critère* : la valeur affichée tient compte du décalage.

---

## 9. État du babyphone et pannes

**F-42 État visible** (D26)
L'app affiche en permanence : **en ligne**, **âge de la dernière image**, **micro actif**, **IA active**, **mode**, et l'état des destinataires.
*Critère* : chaque indicateur change d'état quand on débranche ou arrête le composant correspondant.

**F-43 Babyphone injoignable** (D26)
Si le babyphone ne répond plus alors que l'app est ouverte, l'app affiche une **grosse alerte**.
*Critère* : babyphone débranché, l'alerte s'affiche dans l'app ouverte en moins de 30 secondes (valeur à confirmer en recette).

**F-44 Auto-surveillance** (D26)
Si la caméra, le micro, l'IA ou l'envoi des notifications plante, le babyphone **relance le composant** et **envoie une notification d'information**.
*Critère* : composant arrêté exprès, il redémarre et la notification arrive.

**F-45 Trou accepté en V1** (D26)
Une **coupure de courant** ou une **perte de Wi-Fi** du babyphone ne se voit **qu'en ouvrant l'app** (le veilleur à la maison viendra en V2, D27).
*Critère* : documenté dans le guide d'utilisation.

**F-46 Coupure réseau pendant une sieste** (P48)
Une coupure en cours de route n'ouvre pas le réseau de configuration : le babyphone **retente ses réseaux connus**.
*Critère* : box redémarrée pendant une sieste, le babyphone se reconnecte seul.

**F-47 Téléphone désappairé** (P45)
Si le babyphone ne reconnaît plus le téléphone, l'app affiche « **Ce téléphone n'est plus appairé** » et explique comment refaire l'appairage.
*Critère* : après un retrait (F-08), l'app affiche ce message.

---

## 10. Réseaux Wi-Fi

**F-48 Ajout de réseaux à l'avance** (P46)
Depuis l'app, on enregistre à l'avance des Wi-Fi (grands-parents, amis) et le **partage de connexion de chaque téléphone**. Sur place, il suffit de brancher le babyphone.
*Critère* : un réseau ajouté depuis l'app est rejoint automatiquement sur place.

**F-49 Liste des réseaux connus** (P46)
L'app liste les réseaux connus et permet d'en **supprimer**.
*Critère* : un réseau supprimé n'est plus rejoint.

**F-50 App utilisable sur le réseau de configuration** (P50)
Un téléphone déjà appairé, connecté au réseau de configuration, peut choisir le Wi-Fi **depuis l'app** (sans notifications, faute d'internet).
*Critère* : la configuration du Wi-Fi fonctionne depuis l'app sur le réseau de configuration.

**F-51 Lieux publics** (D13)
Dans un lieu public, le babyphone et l'autre téléphone se connectent au **partage de connexion d'un téléphone**.
*Critère* : sieste d'essai complète sur le partage de connexion de chaque téléphone.

---

## 11. Mises à jour

**F-52 Mise à jour disponible** (D46)
L'app affiche « **Mise à jour disponible** ». Un **rappel discret** apparaît si elle attend depuis longtemps (environ 15 jours).
*Critère* : une nouvelle version publiée est signalée dans l'app.

**F-53 Lancement et déroulement** (D46, P53)
Un parent lance la mise à jour **en dehors du mode Sieste** (le bouton est indisponible en Sieste, avec l'explication). Le babyphone passe en **Maintenance**, se met à jour, redémarre et **vérifie que tout fonctionne** (live, son, IA, réseau). Le résultat est notifié : « Mise à jour réussie » ou « Mise à jour annulée ».
*Critère* : une mise à jour réussie aboutit à la nouvelle version et à la notification.

**F-54 Retour arrière automatique** (D46, D71)
En cas d'échec, le babyphone **revient tout seul à la version précédente**, réglages compris, et le notifie.
*Critère* : une mise à jour volontairement défectueuse est annulée et le babyphone fonctionne comme avant.

**F-55 Où mettre à jour**
L'app conseille de faire la mise à jour **à la maison** : elle télécharge plusieurs centaines de Mo, ce qui est déconseillé sur un partage de connexion.
*Critère* : le conseil apparaît avant le lancement.

---

## 12. Réglages

| Réglage | Valeur par défaut | Exigence |
|---|---|---|
| Sensibilité de la détection | Moyenne (réglée sur le banc d'essai) | F-23 |
| Pause anti-rafale | À régler sur le banc d'essai | F-21 |
| Caméra permanente ou à la demande | Permanente | F-31 |
| Correction de température | 0 °C | F-41 |
| Destinataires des alertes | Les téléphones appairés | F-32 à F-34 |
| Réseaux Wi-Fi connus | Ceux déjà utilisés | F-48, F-49 |
| Durée de Surveillance silencieuse | Choisie à chaque activation | F-13 |

---

## 13. Exigences non fonctionnelles

**NF-01 Confidentialité** (D9, D11, D66, D85, P1)
L'image et le son **ne sortent jamais du réseau local** et ne passent par **aucun tiers**. Aucun compte, aucun cloud. Internet sert uniquement aux notifications (texte seul, chiffré de bout en bout), aux mises à jour, à la mise à jour du nom, au certificat et à l'heure.
*Critère* : une capture du trafic sortant du babyphone ne montre que ces destinations.

**NF-02 Aucun enregistrement** (D6)
Aucune image ni aucun son n'est stocké, ni sur le babyphone ni ailleurs.
*Critère* : aucun fichier audio ou vidéo n'est écrit pendant une sieste.

**NF-03 Délais**
Live sous 1 seconde (F-28) ; alerte envoyée au plus ~8 secondes après le début d'un pleur qui dure (F-19). La **livraison** par Apple ou Google ajoute en général quelques secondes, **sans garantie** (§ 14).

**NF-04 Fiabilité de la détection** (D23, D81)
Sur le banc d'essai : **zéro pleur manqué** parmi ceux qui durent plus de 8 secondes ; **au plus une fausse alerte par sieste de 2 heures**.
*Amendé le 2026-11-26 (banc d'essai, lot 2)* : **au plus deux fausses alertes** par sieste de 2 heures. YAMNet alerte sur une porte qui grince (1,33 fausse alerte par 2 h au banc, sur 6 h de bruits de fond) ; l'auteur l'accepte : elle peut signaler que quelqu'un entre dans la pièce.
*Critère* : seuils vérifiés à chaque modification de la détection (intégration continue).

**NF-05 Endurance**
Le live tient **au moins une heure** sans coupure vers les deux téléphones ; la surveillance tient une sieste de **2 heures et plus**.
*Critère* : recette sur le vrai matériel avant chaque version.

**NF-06 Installation rapide sur place** (§ 1.1 des notes)
Dans un lieu connu, **brancher suffit**. Aucun écran, aucun clavier.

**NF-07 Compatibilité** (D84)
iPhone sous **iOS 27** (app installée depuis Safari ; iOS 16.4 au minimum pour les notifications) ; Android **13** avec **Chrome** (modèle à préciser).

**NF-08 Langue** (D51)
Interface et documentation **en français**.

**NF-09 Sobriété et accessibilité** (P59)
La 3D se met en pause pendant le live ; l'app respecte le réglage « réduire les animations » du téléphone.

**NF-10 Autonomie sur batterie** (D38, § 6.9 des notes)
Sur la batterie UGREEN PB722, plusieurs siestes par charge (estimation : 8 à 15 heures, **à mesurer**). Le babyphone ne connaît pas le niveau de la batterie : le vérifier sur l'écran de la batterie avant la sieste.

**NF-11 Sécurité physique**
Le boîtier et ses câbles sont installés **à plus d'un mètre du lit** (recommandation à sourcer, § 6.11 des notes). Le guide d'utilisation le rappelle.

---

## 14. Limites connues et hors périmètre

**Limites connues de la V1** :

- Une coupure de courant ou de Wi-Fi du babyphone ne se voit **qu'en ouvrant l'app** (F-45).
- La **livraison des notifications** par Apple et Google n'est **pas garantie** : économie d'énergie, Android en veille profonde, modes Concentration et Ne pas déranger (d'où le conseil de F-07).
- Le **son du live en arrière-plan**, téléphone verrouillé, n'est pas garanti, surtout sur iPhone : l'usage visé est « je regarde de temps en temps, sinon je reçois une alerte ».
- L'IA reconnaît **un bébé**, pas **ce bébé-là** : un autre enfant qui pleure fort près du micro peut déclencher une alerte.
- Si **internet tombe sur le lieu**, le téléphone ne trouve plus le babyphone au bout d'environ une minute, et les alertes ne partent plus.
- Certains réseaux bloquent le nom du babyphone (protection « DNS rebinding ») : parade sur le téléphone, décrite dans le guide.
- **Pas de live hors du réseau local** : il viendra avec le tunnel WireGuard (V2).

**Hors périmètre de la V1** :

- Live à distance (V2, D18) ; veilleur à la maison (V2, D27) ; berceuse (V2, D40).
- Alertes et courbes de température ; accès invité ; module batterie intégré.
- Enregistrement et replay (D6), parler au bébé (D39), veilleuse intégrée (D42).

---

## 15. Notifications : liste et textes

Les textes ci-dessous sont des **exemples provisoires** : ils seront définis au moment du développement (D88). L'heure est celle de l'événement.

| Type | Quand | Texte (exemple) | Priorité |
|---|---|---|---|
| Alerte pleur | F-17 | « Bébé pleure — 14:32 » | Haute |
| Alerte gémissement | F-17 | « Bébé gémit — 14:32 » | Haute |
| Alerte babillage | F-17 | « Bébé babille — 14:32 » | Haute |
| Alerte rire | F-17 | « Bébé rit — 14:32 » | Haute |
| Alerte hurlement | F-20 | « Bébé crie — 14:32 » | Haute |
| Mode changé | F-15 | « Surveillance silencieuse activée pour 1 h » | Normale |
| Sieste réactivée | F-14 | « Mode sieste réactivé » | Normale |
| Panne relancée | F-44 | « Micro relancé après un incident » | Normale |
| Destinataire retiré | F-35 | « Tu ne reçois plus les alertes du babyphone » | Normale |
| Abonnement invalide | F-37 | « L'iPhone ne reçoit plus les alertes » | Normale |
| Nouveau téléphone | F-06 | « Nouveau téléphone appairé » | Normale |
| Maintenance | F-16 | « Mise à jour en cours » | Normale |
| Mise à jour réussie | F-53 | « Mise à jour réussie (version 1.2.0) » | Normale |
| Mise à jour annulée | F-54 | « Mise à jour annulée, retour à la version 1.1.0 » | Normale |
