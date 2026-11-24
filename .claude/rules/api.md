---
paths:
  - "backend/marmotte/**/views/**"
  - "backend/marmotte/**/schemas/**"
  - "backend/marmotte/**/api_urls.py"
  - "backend/marmotte/api.py"
  - "backend/marmotte/urls.py"
---

# API (django-ninja)

- Un module expose son API ainsi : `schemas/<objet>.py` (classes `ninja.Schema`, suffixe `In` pour une entrée, `Out` pour une sortie), `views/<objet>.py` (un `Router` par fichier et ses routes), `api_urls.py` (un `router` qui assemble ceux de `views/` par `add_router`). `marmotte/api.py` monte le `router` de chaque module ; `marmotte/urls.py` sert le tout sous `/api/`. Modèle : `backend/marmotte/base/`.
- Chaque route déclare son schéma de réponse (`response=HealthOut`, ou un dictionnaire `{200: …, 404: …}` quand plusieurs codes sont possibles) et des paramètres et un retour typés : le schéma OpenAPI généré sert au client typé du front (P57).
- Les `tags` du `Router` regroupent les routes dans `/api/docs` : le nom du module.
- Erreurs attendues : renvoyer le bon code avec un schéma d'erreur déclaré, ou lever `ninja.errors.HttpError(<code>, "<message>")` ; une exception non gérée donne une 500, jamais un comportement voulu.
- Accès : en V1, l'API sera réservée aux téléphones appairés (clé d'appareil en cookie, lot 8). Aucune route ne doit exposer le live, une clé ou un secret sans cette protection une fois le lot 8 livré.
- Temps réel : SSE pour pousser l'état vers l'app (P36, lot 4), pas de WebSocket.
- Les réponses sont en anglais pour les identifiants et clés JSON ; les textes montrés aux parents viennent de l'app (en français).
