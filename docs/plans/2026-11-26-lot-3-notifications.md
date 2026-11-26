# Lot 3 : notifications — plan détaillé

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** une alerte décidée par la détection est écrite dans une file SQLite puis envoyée en Web Push à chaque destinataire, par le service `marmotte-notifications` ou, s'il est arrêté ou figé, par le filet de la détection ; une alerte du banc arrive sur l'iPhone de l'auteur, service arrêté compris (issue #5).

**Architecture:** deux applications Django nouvelles : `phones` (le téléphone, `receives_alerts`) et `notifications` (abonnements, notifications, livraisons, envoi). Les trois programmes (web, détection, notifications) partagent une base SQLite en WAL par l'ORM. L'envoi passe par l'interface `PushSender` (vrai : pywebpush ; doublure : `FakePushSender`). Une seule fonction de traitement (réservation atomique, envoi, résultat) sert au service (toutes les 250 ms) et au filet de la détection (livraisons dues depuis 2 s, réservations de plus de 10 s). Si la base refuse l'écriture, un « dernier recours » à part envoie depuis une copie en mémoire.

**Tech Stack:** Python 3.14, Django 6, django-ninja, SQLite (WAL), pywebpush 2.5 (+ py-vapid, http-ece, cryptography, requests), pytest, pytest-django ; HTML et JavaScript écrits à la main pour la page de test.

**Spec:** `docs/plans/2026-11-26-lot-3-notifications-design.md` (validé par l'auteur le 2026-11-26) ; `docs/technique/choix-techniques-et-architecture.md` § 8.3, § 9 ; `docs/fonctionnel/specs-fonctionnelles.md` F-24, F-26, F-32 à F-37, § 15 ; journal D95 à D99, P73 amendé, D88 complété.

## Global Constraints

- Voir `docs/plans/2026-11-19-plan-directeur-v1.md`, « Global Constraints », et `CLAUDE.md` (typage complet, ruff, docstrings sous les constantes, un fichier par objet, tests en classes avec GIVEN/WHEN/THEN).
- Base : `DATA_DIR / "marmotte.sqlite3"`, options `"transaction_mode": "IMMEDIATE"`, `"timeout": 5`, `"init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;"`. Aucun appel réseau dans une transaction.
- Délais (P73 amendé) : service toutes les **0,25 s** ; filet sur les livraisons **dues depuis ≥ 2 s** ; réservation reprise après **10 s** ; envoi HTTP limité à **8 s** ; nouvelles tentatives **1, 2, 4, 8, 16, 32 puis 60 s** (`Retry-After` l'emporte) ; expiration après l'échéance **et** au moins **3** tentatives.
- Garde (D98) : alertes **600 s**, `Urgency: high` ; informations **86 400 s**, `Urgency: normal` ; `TTL` jamais 0. Historique : **7 jours**.
- Contenu : format déclaratif `{"web_push": 8030, "notification": {"title", "body", "lang": "fr-FR", "navigate", "tag"}}`, sans `mutable`, moins de 4 096 octets. `Topic` = `tag` = UUID en 32 caractères hexadécimaux.
- Codes HTTP : 200, 201, 202 → envoyé ; 404, 410 → abonnement mort ; 400, 413 → échec définitif ; tout le reste (403, 429, 5xx, réseau, délai) → nouvelle tentative.
- Textes (D88), heure `HH:MM` en `Europe/Paris` : voir la tâche 2.
- La chaîne de détection (`pipeline`, `decision`, `level`, `classifier`, banc) **reste sans Django**. Seuls `queue_sink.py`, `last_resort.py` et `__main__.py` (sans `--print`) l'importent, et `__main__` seulement dans la branche qui en a besoin.
- Aucun nom de domaine réel ni secret dans le dépôt : `https://marmotte.example` dans `.env.example` et les tests.
- Chaque commit suit `type(module): description` et **attend l'accord de l'auteur** (skill `commit`, une approbation = un commit). Branche : `feat/5-notifications`.

## Review Focus

1. **Horloge en retard au démarrage puis saut en avant** (Pi éteint une nuit, NTP qui se synchronise) : une alerte tentée une seule fois n'expire pas ; un 403 est retenté (tâche 5, `test_does_not_expire_before_three_attempts`, `test_403_is_retried`).
2. **Un téléphone dont le service push est très lent** : l'autre téléphone reçoit l'alerte sans attendre les 8 s du premier (tâche 6, `test_slow_phone_does_not_delay_the_other`).
3. **Abonnement vers une adresse du réseau local** (`https://192.168.1.10/…`, `http://…`, port exotique) : refusé en 422, aucune requête envoyée (tâche 7, `test_rejects_non_push_hosts`).
4. **Base verrouillée par un autre processus au moment d'un pleur** : `emit()` rend la main tout de suite, la boucle du micro n'attend pas (tâche 9, `test_emit_never_blocks`).
5. **Deux programmes qui démarrent ensemble sans clé VAPID** : une seule clé est créée et lue par les deux (tâche 4, `test_concurrent_creation_yields_one_key`).

---

### Task 1: Base SQLite partagée et module `phones`

**Files:**
- Create: `backend/marmotte/settings/django/databases.py`, `backend/marmotte/phones/__init__.py`, `apps.py`, `models/__init__.py`, `models/phone.py`, `migrations/__init__.py`, `migrations/0001_initial.py` (générée), `tests/__init__.py`, `tests/tests_models/__init__.py`, `tests/tests_models/test_phone.py` ; `backend/marmotte/base/tests/test_database.py`, `backend/marmotte/base/tests/concurrent_writer.py`
- Modify: `backend/marmotte/settings/base.py` (import de `databases`), `backend/marmotte/settings/django/apps.py` (`LOCAL_APPS` + `"marmotte.phones"`), `justfile` (recette `deploy` : `uv run python manage.py migrate` après `uv sync`), `.claude/rules/migrations.md` (« à partir du lot 3 »)

**Interfaces:**
- Produces: `marmotte.phones.models.Phone` : `name: CharField(max_length=40)`, `receives_alerts: BooleanField(default=True)`, `created_at: DateTimeField(auto_now_add=True)` ; `DATABASES` comme dans « Global Constraints » ; `DATA_DIR` créé (`mkdir(parents=True, exist_ok=True)`) dans `databases.py` avant `DATABASES`.

- [ ] **Step 1: Écrire les tests qui échouent**

`test_database.py` :
- `TestDatabaseSettings.test_uses_sqlite_in_wal_with_immediate_transactions` : `settings.DATABASES["default"]["OPTIONS"]` vaut exactement le dictionnaire des « Global Constraints » et `NAME` finit par `marmotte.sqlite3`.
- `TestConcurrentWriters.test_three_processes_write_without_lock_errors` : dans `tmp_path`, `manage.py migrate` en sous-processus (`MARMOTTE_DATA_DIR=tmp_path`, `MARMOTTE_ENV_FILE=""`, réglages `prod`), puis trois `subprocess.Popen([sys.executable, "-m", "marmotte.base.tests.concurrent_writer", "200"])` lancés ensemble ; chacun fait 200 fois, dans `transaction.atomic()`, `Phone.objects.count()` puis `Phone.objects.create(...)` (une lecture puis une écriture : le cas qui échoue sans `IMMEDIATE`). Attendu : trois codes de sortie 0, aucun `database is locked` dans la sortie d'erreur, `PRAGMA journal_mode` = `wal`, 600 téléphones.

`test_phone.py` : `TestPhone.test_receives_alerts_by_default` (`@pytest.mark.django_db`).

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `cd backend && uv run pytest marmotte/base/tests/test_database.py marmotte/phones -v`
Expected: FAIL (`DATABASES` absent, module `marmotte.phones` introuvable).

- [ ] **Step 3: Écrire `databases.py`, l'application `phones` et `concurrent_writer.py`, puis générer la migration**

Run: `cd backend && uv run python manage.py makemigrations phones` (relire la migration).

- [ ] **Step 4: Lancer les tests et les contrôles**

Run: `cd backend && uv run pytest -m "not hardware and not model and not bench" && uv run ruff check && uv run pyright && uv run python manage.py makemigrations --check --dry-run`
Expected: tout passe, « No changes detected ».

- [ ] **Step 5: Commit** (accord de l'auteur) — `feat(backend): add the shared SQLite database and the phones module`

---

### Task 2: Modèles de la file et textes des notifications

**Files:**
- Create: `backend/marmotte/notifications/__init__.py`, `apps.py`, `models/__init__.py`, `models/push_subscription.py`, `models/notification.py`, `models/delivery.py`, `migrations/0001_initial.py` (générée), `utils/__init__.py`, `utils/texts.py`, `tests/__init__.py`, `tests/tests_models/__init__.py`, `tests/tests_models/test_delivery.py`, `tests/test_texts.py`
- Modify: `backend/marmotte/common/enums.py` (`NotificationKind`), `backend/marmotte/settings/django/apps.py` (`"marmotte.notifications"`)

**Interfaces:**
- Produces:
  - `NotificationKind(StrEnum)` : `CRY = "cry"`, `WHIMPER = "whimper"`, `BABBLE = "babble"`, `LAUGH = "laugh"`, `SCREAM = "scream"`, `RECIPIENT_REMOVED = "recipient_removed"`, `SUBSCRIPTION_INVALID = "subscription_invalid"`, `TEST = "test"`. Une alerte : `NotificationKind(sound_class.value)`.
  - `PushSubscription` : `phone: OneToOneField(Phone, CASCADE, related_name="push_subscription")`, `endpoint: URLField(max_length=2048, unique=True)`, `p256dh: CharField(128)`, `auth: CharField(64)`, `created_at` (`auto_now_add`), `updated_at` (`auto_now`), `invalid_at: DateTimeField(null=True, blank=True)`, `invalid_reason: CharField(200, blank=True)` ; propriété `is_valid -> bool`.
  - `Urgency(TextChoices)` : `HIGH = "high"`, `NORMAL = "normal"`. `Notification` : `id: UUIDField(primary_key=True, default=uuid4)`, `kind: CharField(32, choices=NotificationKind)`, `title: CharField(120)`, `body: CharField(200)`, `navigate_path: CharField(100)`, `urgency: CharField(8, choices=Urgency.choices)`, `ttl_s: PositiveIntegerField()`, `event_at`, `created_at`, `deadline_at` (= `created_at + ttl_s`, écrit à la mise en file : l'échéance se filtre sans calcul SQL).
  - `DeliveryStatus(TextChoices)` : `PENDING`, `SENDING`, `SENT`, `GONE`, `FAILED`, `EXPIRED` (valeurs en minuscules) ; `Claimant(TextChoices)` : `SERVICE = "service"`, `DETECTION = "detection"`. `Delivery` : `notification: ForeignKey(Notification, CASCADE, related_name="deliveries")`, `subscription: ForeignKey(PushSubscription, CASCADE, related_name="deliveries")`, `status` (défaut `PENDING`), `claimed_by: CharField(10, choices=Claimant.choices, blank=True)`, `claimed_at: DateTimeField(null=True)`, `attempts: PositiveSmallIntegerField(default=0)`, `next_attempt_at: DateTimeField()`, `last_http_status: PositiveSmallIntegerField(null=True)`, `last_error: CharField(300, blank=True)`, `sent_at: DateTimeField(null=True)`, `sent_by: CharField(10, choices=Claimant.choices, blank=True)` ; contrainte d'unicité (`notification`, `subscription`) ; index (`status`, `next_attempt_at`).
  - `marmotte.notifications.utils.texts` : `ALERT_TTL_S = 600`, `INFO_TTL_S = 86_400` ; `@dataclass(frozen=True) class NotificationContent(title: str, body: str, navigate_path: str, urgency: Urgency, ttl_s: int)` ; `notification_content(kind: NotificationKind, event_at: datetime, phone_name: str | None = None) -> NotificationContent`.

- [ ] **Step 1: Écrire les tests qui échouent**

`test_texts.py`, `TestNotificationContent`, avec `event_at = datetime(2026, 1, 15, 13, 32, tzinfo=UTC)` (14:32 à Paris) ; un test paramétré couvre le tableau entier :

| kind | title | body | navigate_path | urgency | ttl_s |
|---|---|---|---|---|---|
| cry | Bébé pleure | Entendu à 14:32 | /live | high | 600 |
| whimper | Bébé gémit | Entendu à 14:32 | /live | high | 600 |
| babble | Bébé babille | Entendu à 14:32 | /live | high | 600 |
| laugh | Bébé rit | Entendu à 14:32 | /live | high | 600 |
| scream | Bébé crie | Entendu à 14:32 | /live | high | 600 |
| recipient_removed | Alertes coupées | Tu ne reçois plus les alertes du babyphone | / | normal | 86400 |
| subscription_invalid (`phone_name="iPhone"`) | iPhone ne reçoit plus les alertes | Ouvre Marmotte sur ce téléphone pour les réactiver | / | normal | 86400 |
| test | Notification de test | Envoyée à 14:32 | /push-test/ | normal | 86400 |

Plus `test_summer_time` (`2026-07-15 12:32 UTC` → « 14:32 ») et `test_subscription_invalid_needs_a_phone_name` (`ValueError` sans `phone_name`).

`test_delivery.py` (`django_db`) : `test_one_delivery_per_subscription_and_notification` (`IntegrityError` au doublon) ; `test_subscription_is_valid_until_invalidated`.

- [ ] **Step 2: Lancer, vérifier l'échec** — `uv run pytest marmotte/notifications -v` : FAIL (module introuvable).

- [ ] **Step 3: Écrire l'enum, les modèles et `texts.py` ; générer la migration** (`makemigrations notifications`, relue).

- [ ] **Step 4: Lancer tests et contrôles** (même commande qu'à la tâche 1) : PASS.

- [ ] **Step 5: Commit** — `feat(notifications): add the send queue models and the notification texts`

---

### Task 3: Mise en file et destinataires

**Files:**
- Create: `backend/marmotte/notifications/utils/queue.py`, `backend/marmotte/notifications/tests/test_queue.py`, `backend/marmotte/notifications/tests/factories.py` (fonctions `make_phone(name="iPhone", receives_alerts=True, endpoint=None) -> Phone` avec abonnement valide sur `https://web.push.apple.com/<n>`)

**Interfaces:**
- Consumes: modèles et `notification_content` (tâche 2).
- Produces (`marmotte.notifications.utils.queue`) :
  - `recipients() -> list[Phone]` : `receives_alerts` vrai et abonnement valide, triés par `id`.
  - `enqueue(kind: NotificationKind, event_at: datetime, *, now: datetime | None = None, notification_id: UUID | None = None, to: Sequence[Phone] | None = None, phone_name: str | None = None) -> Notification` : une transaction ; `now` par défaut `timezone.now()` ; `created_at = now`, `deadline_at = now + ttl_s` ; une `Delivery` `PENDING` avec `next_attempt_at = now` par abonnement valide de `to` (ou de `recipients()`) ; un `notification_id` existant renvoie la notification existante sans rien créer ; zéro destinataire : notification écrite, `logger.warning`.
  - `remove_recipient(phone: Phone, *, now: datetime | None = None) -> Notification` : `receives_alerts = False`, puis `enqueue(RECIPIENT_REMOVED, now, to=[phone])`.

- [ ] **Step 1: Écrire les tests qui échouent** (`TestRecipients`, `TestEnqueue`, `TestRemoveRecipient`, `django_db`) :
  - `test_recipients_skip_muted_and_invalid` : trois téléphones (un normal, un `receives_alerts=False`, un abonnement invalidé) → seul le premier.
  - `test_creates_one_pending_delivery_per_recipient` : deux destinataires → deux livraisons `pending`, `next_attempt_at == now`, `deadline_at == now + 600 s` pour `CRY`.
  - `test_recipients_are_frozen_at_enqueue` : un téléphone ajouté après n'a pas de livraison.
  - `test_replayed_id_creates_nothing` : même `notification_id` deux fois → une notification, deux livraisons au total.
  - `test_zero_recipient_still_writes_the_notification` (et un `WARNING` dans `caplog`).
  - `test_last_message_goes_to_the_removed_phone_only` : après `remove_recipient(b)`, `b.receives_alerts` est faux et la notification `RECIPIENT_REMOVED` n'a qu'une livraison, vers `b`.

- [ ] **Step 2: Lancer, vérifier l'échec** — `uv run pytest marmotte/notifications/tests/test_queue.py -v` : FAIL.
- [ ] **Step 3: Écrire `queue.py` et `factories.py`.**
- [ ] **Step 4: Lancer tests et contrôles** : PASS.
- [ ] **Step 5: Commit** — `feat(notifications): add the send queue and the recipients`

---

### Task 4: Clés VAPID, contenu et envoi

**Files:**
- Create: `backend/marmotte/settings/project/notifications.py`, `backend/marmotte/notifications/utils/vapid.py`, `utils/payload.py`, `utils/push.py`, `tests/fakes.py`, `tests/test_vapid.py`, `tests/test_payload.py`, `tests/test_push.py`
- Modify: `backend/pyproject.toml` (`pywebpush>=2.5`, et `MARMOTTE_APP_URL=https://marmotte.example` dans `env` de pytest), `backend/marmotte/settings/base.py` (import du nouveau thème), `backend/.env.example` (`MARMOTTE_APP_URL`, `MARMOTTE_PUSH_TEST_PAGE`, commentés en français)

**Interfaces:**
- Consumes: `Notification`, `NotificationContent`, `Urgency` (tâche 2).
- Produces:
  - Réglages : `APP_URL = get_config_value("MARMOTTE_APP_URL")` (obligatoire, sans `/` final), `PUSH_TEST_PAGE = get_config_value("MARMOTTE_PUSH_TEST_PAGE", default="false", cast=to_bool)`.
  - `vapid.py` : `VAPID_KEY_FILE = "vapid_private.pem"` ; `@dataclass(frozen=True) class VapidKey(private_key_path: Path, public_key: str)` (clé publique : point non compressé P-256, base64url sans `=`) ; `load_or_create_vapid_key(data_dir: Path) -> VapidKey`. Création atomique : clé générée par `cryptography` (`ec.SECP256R1`), PEM PKCS8 écrit dans un fichier temporaire du même dossier en mode `0o600`, puis `os.link(tmp, final)` ; `FileExistsError` → on lit la clé existante ; le temporaire est toujours supprimé.
  - `payload.py` : `content_of(notification: Notification) -> NotificationContent` ; `build_message(notification_id: UUID, content: NotificationContent, app_url: str) -> PushMessage` (JSON `ensure_ascii=False`, `navigate = app_url + navigate_path`, `topic = tag = notification_id.hex`).
  - `push.py` : `SEND_TIMEOUT_S = 8.0` ; `@dataclass(frozen=True) PushTarget(endpoint: str, p256dh: str, auth: str)` et `PushTarget.of(subscription: PushSubscription)` ; `@dataclass(frozen=True) PushMessage(payload: str, urgency: Urgency, ttl_s: int, topic: str)` ; `SendOutcome(StrEnum)` : `SENT`, `RETRY`, `GONE`, `FAILED` ; `@dataclass(frozen=True) SendResult(outcome: SendOutcome, http_status: int | None, retry_after_s: float | None, duration_s: float, error: str = "")` ; `outcome_for_status(status: int) -> SendOutcome` ; `class PushSender(Protocol): def send(self, target: PushTarget, message: PushMessage) -> SendResult` ; `class PywebpushSender(vapid_key: VapidKey, subject: str, timeout_s: float = SEND_TIMEOUT_S)` : `pywebpush.webpush(..., data=message.payload, vapid_private_key=<Vapid chargé une fois par py_vapid>, vapid_claims={"sub": subject}, ttl=message.ttl_s, headers={"Urgency": …, "Topic": …}, timeout=timeout_s, requests_session=<une session par fil>)` ; `WebPushException` → code de `.response`, `Retry-After` en secondes (une date est ignorée) ; erreur `requests` → `RETRY` sans code.
  - `tests/fakes.py` : `FakePushSender` avec `sent: list[tuple[PushTarget, PushMessage]]`, `respond(endpoint: str, *results: SendResult)` (réponses dans l'ordre, puis 201), `block(endpoint: str) -> threading.Event` (l'envoi attend que l'événement soit posé) ; `sent_result()`, `status_result(code, retry_after_s=None)` pour écrire les tests.

- [ ] **Step 1: Écrire les tests qui échouent**
  - `TestLoadOrCreateVapidKey` (`tmp_path`) : `test_creates_a_private_key_readable_by_owner_only` (mode `0o600`, clé publique de 87 caractères base64url, commence par `B`) ; `test_reuses_the_existing_key` ; `test_concurrent_creation_yields_one_key` (8 fils via `ThreadPoolExecutor` appellent la fonction : une seule clé publique, un seul fichier `.pem` dans le dossier).
  - `TestBuildMessage` : pour `CRY` à 14:32, `json.loads(payload) == {"web_push": 8030, "notification": {"title": "Bébé pleure", "body": "Entendu à 14:32", "lang": "fr-FR", "navigate": "https://marmotte.example/live", "tag": "<hex>"}}`, `urgency == HIGH`, `ttl_s == 600`, `topic == id.hex` (32 caractères) ; `test_longest_message_fits_in_4_kb` (`SUBSCRIPTION_INVALID` avec un nom de 40 « é » → `len(payload.encode()) < 4096`).
  - `TestOutcomeForStatus` paramétré : 201, 200, 202 → `SENT` ; 404, 410 → `GONE` ; 400, 413 → `FAILED` ; 403, 429, 500, 503 → `RETRY`.
  - `TestPywebpushSender` (avec `monkeypatch.setattr` sur `pywebpush.webpush` dans le module `push`) : `test_passes_ttl_urgency_and_topic` (arguments reçus : `ttl=600`, en-têtes `Urgency: high` et `Topic`, `vapid_claims == {"sub": "https://marmotte.example"}`, `timeout=8.0`) ; `test_maps_webpush_exception_to_result` (exception avec réponse 429 et `Retry-After: 30` → `RETRY`, `retry_after_s == 30`) ; `test_network_error_is_retried`.
  - `@pytest.mark.hardware` `test_real_send` : lit `MARMOTTE_TEST_PUSH_SUBSCRIPTION` (JSON d'un abonnement fait avec la clé de `settings.DATA_DIR`), saute sans elle, envoie un `TEST` → `SENT`.

- [ ] **Step 2: Lancer, vérifier l'échec** — FAIL (modules introuvables).
- [ ] **Step 3: `uv add pywebpush` puis écrire réglages, `vapid.py`, `payload.py`, `push.py`, `fakes.py`.**
- [ ] **Step 4: Lancer tests et contrôles** : PASS ; vérifier sur PyPI la licence de chaque paquet que `uv.lock` vient d'ajouter : aucune licence non commerciale ni GPL (attendu : pywebpush et py-vapid MPL 2.0, http-ece MIT, aiohttp et requests Apache 2.0).
- [ ] **Step 5: Commit** — `feat(notifications): add VAPID keys, the declarative payload and the push sender`

---

### Task 5: Traitement des livraisons

**Files:**
- Create: `backend/marmotte/notifications/utils/processing.py`, `backend/marmotte/notifications/tests/test_processing.py`

**Interfaces:**
- Consumes: modèles (tâche 2), `enqueue`, `recipients` (tâche 3), `PushSender`, `PushTarget`, `build_message`, `content_of`, `SendOutcome` (tâche 4), `settings.APP_URL`.
- Produces (`marmotte.notifications.utils.processing`) :
  - `RESERVATION = timedelta(seconds=10)` ; `BACKOFF_S = (1, 2, 4, 8, 16, 32, 60)` ; `MIN_ATTEMPTS_BEFORE_EXPIRY = 3` ; `type Clock = Callable[[], datetime]`.
  - `expire_overdue(now: datetime) -> int` : livraisons `pending`, ou `sending` réservées depuis plus de `RESERVATION`, dont `notification.deadline_at < now` et `attempts >= 3` → `expired`.
  - `claim_due(claimant: Claimant, now: datetime, *, notification_ids: Collection[UUID] | None = None, min_due_age: timedelta = timedelta(0)) -> list[int]` : candidates `pending` avec `next_attempt_at <= now - min_due_age`, et `sending` avec `claimed_at <= now - RESERVATION` ; chacune prise par une requête `filter(pk=…, <même condition>).update(status=SENDING, claimed_by=claimant, claimed_at=now)` ; renvoie les identifiants obtenus.
  - `send_claimed(delivery_id: int, sender: PushSender, claimant: Claimant, clock: Clock) -> SendOutcome | None` : envoie hors transaction, puis écrit le résultat. `SENT` : `status=sent`, `sent_at`, `sent_by` sans condition (jamais annulé). Autres issues : écrites seulement si la livraison est toujours `sending` avec ce `claimed_by` et ce `claimed_at` (sinon renvoie `None` : quelqu'un a repris). `RETRY` : `pending`, `claimed_by=""`, `next_attempt_at = now + max(BACKOFF_S[min(attempts, 7) - 1], retry_after_s or 0)`. `GONE` : `gone`, abonnement invalidé (`invalid_at`, `invalid_reason = f"HTTP {code}"`), puis s'il était valide : `enqueue(SUBSCRIPTION_INVALID, now, phone_name=phone.name)` vers `recipients()` (s'il n'en reste aucun : `logger.warning`). `FAILED` : `failed` et `logger.error`. Toujours : `attempts += 1`, `last_http_status`, `last_error`, et une ligne `logger.info` (notification, type, téléphone, urgence, garde, code, durée, envoyeur).
  - `process_due(sender: PushSender, claimant: Claimant, clock: Clock, *, notification_ids: Collection[UUID] | None = None, min_due_age: timedelta = timedelta(0), pool: Executor | None = None) -> int` : `claim_due` puis `send_claimed` pour chacune (dans `pool` s'il est donné, en attendant la fin ; sinon à la suite) ; renvoie le nombre de livraisons tentées.

- [ ] **Step 1: Écrire les tests qui échouent** (`django_db`, horloge = liste mutable de `datetime`, `FakePushSender`) :
  - `TestClaimDue` : `test_only_one_claimant_wins` (le service réserve, puis le filet sur la même livraison → liste vide) ; `test_min_due_age_leaves_fresh_deliveries` (due depuis 1,9 s → rien pour `min_due_age=2 s` ; depuis 2 s → prise) ; `test_takes_over_a_reservation_older_than_10_s` (réservée par l'un à `t`, l'autre ne prend rien à `t + 9,9 s` mais la prend à `t + 10 s`, quel que soit le détenteur).
  - `TestSendClaimed` : `test_sent_records_who_and_when` ; `test_retry_backs_off_then_honours_retry_after` (503 → `next_attempt_at = now + 1 s` ; puis 429 avec `Retry-After: 30` → `now + 30 s`) ; `test_403_is_retried` ; `test_gone_invalidates_and_warns_the_others` (410 sur l'iPhone, un second téléphone valide → une notification `SUBSCRIPTION_INVALID` titrée « iPhone ne reçoit plus les alertes », livrée au second seulement) ; `test_failed_is_final` (400) ; `test_late_sent_is_never_undone` (A réserve, B reprend après 10 s et envoie, A finit ensuite en `RETRY` → reste `sent`) ; `test_logs_urgency_high_for_alerts` (`caplog` contient `urgency=high`, F-24).
  - `TestExpireOverdue` : `test_expires_after_deadline_and_three_attempts` ; `test_does_not_expire_before_three_attempts` (échéance passée de 2 h après un saut d'horloge, 1 tentative → reste `pending`).
  - `TestProcessDue` : `test_sends_every_due_delivery_and_counts_them`.

- [ ] **Step 2: Lancer, vérifier l'échec** — FAIL.
- [ ] **Step 3: Écrire `processing.py`.**
- [ ] **Step 4: Lancer tests et contrôles** : PASS.
- [ ] **Step 5: Commit** — `feat(notifications): process due deliveries with atomic claims and retries`

---

### Task 6: Service `marmotte-notifications`

**Files:**
- Create: `backend/marmotte/notifications/service.py`, `backend/marmotte/notifications/__main__.py`, `backend/marmotte/notifications/tests/test_service.py`

**Interfaces:**
- Consumes: `expire_overdue`, `process_due` (tâche 5), `load_or_create_vapid_key`, `PywebpushSender` (tâche 4).
- Produces:
  - `service.py` : `POLL_INTERVAL_S = 0.25`, `SERVICE_WORKERS = 4`, `RETENTION = timedelta(days=7)`, `PURGE_EVERY = timedelta(hours=24)` ; `purge_old(now: datetime) -> int` (notifications dont `created_at < now - RETENTION`, livraisons comprises) ; `class NotificationService(sender: PushSender, clock: Clock = timezone.now, pool: Executor | None = None)` avec `run_once() -> None` (expirer, purger si la dernière purge date de plus de `PURGE_EVERY` ou n'a jamais eu lieu, `process_due(..., Claimant.SERVICE, ...)`) et `run(stop: threading.Event) -> None` (boucle `run_once` / `stop.wait(POLL_INTERVAL_S)`, puis `pool.shutdown(wait=True)`).
  - `__main__.py` : `main(argv: list[str] | None = None) -> int` : `prepare_environment()`, `django.setup()`, journal sur la sortie d'erreur, clé VAPID de `settings.DATA_DIR`, `PywebpushSender(key, settings.APP_URL)`, `ThreadPoolExecutor(SERVICE_WORKERS)`, SIGTERM et SIGINT posent l'événement d'arrêt.

- [ ] **Step 1: Écrire les tests qui échouent** (`django_db`) :
  - `test_run_once_sends_pending_alerts` ; `test_purges_after_seven_days_once_a_day` (notification de 8 jours effacée, celle de 6 jours gardée ; un second `run_once` une heure plus tard ne relance pas la purge) ; `test_slow_phone_does_not_delay_the_other` (`django_db(transaction=True)`, pool de 4 fils, `FakePushSender.block` sur l'iPhone : l'envoi au second téléphone est enregistré `sent` pendant que le premier est bloqué, puis on libère) ; `test_stops_when_asked` (`run` dans un fil, `stop.set()` → le fil se termine en moins d'une seconde).
  - `TestCommandLine.test_main_wires_the_real_sender` (`monkeypatch` de `NotificationService.run` pour ne pas boucler : vérifier que `main([])` renvoie 0 et a créé la clé dans un `DATA_DIR` temporaire).

- [ ] **Step 2: Lancer, vérifier l'échec** — FAIL.
- [ ] **Step 3: Écrire `service.py` et `__main__.py`.**
- [ ] **Step 4: Lancer tests et contrôles** : PASS ; essai à la main : `cd backend && uv run python manage.py migrate && timeout 3 uv run python -m marmotte.notifications` se termine sans erreur.
- [ ] **Step 5: Commit** — `feat(notifications): add the notifications service`

---

### Task 7: API des notifications

**Files:**
- Create: `backend/marmotte/notifications/utils/endpoints.py`, `utils/subscriptions.py`, `schemas/__init__.py`, `schemas/vapid_key.py`, `schemas/subscription.py`, `schemas/test_notification.py`, `views/__init__.py`, `views/vapid_key.py`, `views/subscription.py`, `views/test_notification.py`, `api_urls.py`, `tests/tests_views/__init__.py`, `tests/tests_views/test_vapid_key.py`, `tests/tests_views/test_subscription.py`, `tests/tests_views/test_test_notification.py`, `tests/test_endpoints.py`
- Modify: `backend/marmotte/api.py` (`api.add_router("/notifications", notifications_router)`)

**Interfaces:**
- Consumes: `load_or_create_vapid_key` (tâche 4), `enqueue`, `recipients` (tâche 3).
- Produces:
  - `endpoints.py` : `is_push_service_endpoint(url: str) -> bool` : schéma `https`, sans port ou port 443, hôte `fcm.googleapis.com`, `updates.push.services.mozilla.com` ou se terminant par `.push.apple.com`.
  - `subscriptions.py` : `subscribe(name: str, endpoint: str, p256dh: str, auth: str) -> tuple[PushSubscription, bool]` (abonnement trouvé par `endpoint` → clés et nom du téléphone mis à jour, `invalid_at=None`, `False` ; sinon `Phone` + abonnement créés, `True`).
  - Schémas : `VapidKeyOut(public_key: str)` ; `SubscriptionKeysIn(p256dh: str ≤ 128, auth: str ≤ 64)`, `SubscriptionIn(name: str 1–40, endpoint: str ≤ 2048, keys: SubscriptionKeysIn)`, `SubscriptionOut(phone_id: int, receives_alerts: bool)` ; `TestNotificationOut(notification_id: UUID, recipients: int)`.
  - Routes (`tags=["notifications"]`) : `GET /api/notifications/vapid-key` ; `POST /api/notifications/subscriptions` → `{200: SubscriptionOut, 201: SubscriptionOut}`, `HttpError(422, …)` si l'hôte est refusé ; `POST /api/notifications/test` → `TestNotificationOut` (`enqueue(TEST, now)`).

- [ ] **Step 1: Écrire les tests qui échouent** (`client`, `django_db`, `settings.DATA_DIR` remplacé par `tmp_path` avec la fixture `settings`) :
  - `TestIsPushServiceEndpoint` paramétré : vrai pour `https://web.push.apple.com/abc`, `https://fcm.googleapis.com/fcm/send/abc`, `https://updates.push.services.mozilla.com/wpush/v2/abc` ; faux pour `http://fcm.googleapis.com/x`, `https://192.168.1.10/x`, `https://fcm.googleapis.com:8443/x`, `https://evil.example/push.apple.com`, `https://push.apple.com.evil.example/x`.
  - `test_returns_the_public_key` (même valeur que `load_or_create_vapid_key(tmp_path).public_key`).
  - `test_creates_then_updates_a_subscription` (201 puis 200, un seul `Phone`, clés à jour) ; `test_revalidates_an_invalid_subscription` ; `test_rejects_non_push_hosts` (422, aucun `Phone` créé) ; `test_rejects_a_too_long_name` (422).
  - `test_queues_a_test_notification` (deux destinataires → `recipients == 2`, deux livraisons `pending`).

- [ ] **Step 2: Lancer, vérifier l'échec** — FAIL.
- [ ] **Step 3: Écrire utilitaires, schémas, vues, `api_urls.py`, montage.**
- [ ] **Step 4: Lancer tests et contrôles** : PASS ; `/api/docs` montre les trois routes.
- [ ] **Step 5: Commit** — `feat(notifications): add the VAPID key, subscription and test routes`

---

### Task 8: Page de test

**Files:**
- Create: `backend/marmotte/notifications/push_test/index.html`, `push_test/sw.js`, `push_test/manifest.webmanifest`, `backend/marmotte/notifications/views/push_test.py`, `backend/marmotte/notifications/push_test_urls.py`, `backend/marmotte/notifications/tests/tests_views/test_push_test.py`
- Modify: `backend/marmotte/urls.py` (`path("push-test/", include("marmotte.notifications.push_test_urls"))`)

**Interfaces:**
- Consumes: routes de la tâche 7 ; `settings.PUSH_TEST_PAGE`.
- Produces: `GET /push-test/` (`text/html; charset=utf-8`), `GET /push-test/sw.js` (`text/javascript`, `Cache-Control: no-cache`), `GET /push-test/manifest.webmanifest` (`application/manifest+json`) ; chaque vue lève `Http404` si `PUSH_TEST_PAGE` est faux. Les fichiers sont lus depuis `push_test/` et servis tels quels.

Contenu attendu (écrit à la main, en français, sans dépendance) :
- `index.html` : lien vers le manifeste ; champ « Nom du téléphone » (40 caractères au plus) ; bouton « Activer les notifications » qui, **dans le même geste**, appelle `Notification.requestPermission()`, enregistre `/push-test/sw.js` (portée `/push-test/`), récupère la clé (`GET /api/notifications/vapid-key`), s'abonne (`userVisibleOnly: true`) et envoie `{name, endpoint, keys}` à `POST /api/notifications/subscriptions` ; bouton « Envoyer un test » (`POST /api/notifications/test`, affiche le nombre de destinataires) ; ligne d'état ; à l'ouverture, renvoie l'abonnement existant.
- `sw.js` : sur `push`, lit le JSON ; si `web_push === 8030`, `showNotification(n.title, {body: n.body, tag: n.tag, lang: n.lang, data: {navigate: n.navigate}})` ; sur `notificationclick`, ferme la notification, ramène une fenêtre ouverte sur `navigate` ou en ouvre une.
- `manifest.webmanifest` : `name` « Marmotte — test des notifications », `display: "standalone"`, `start_url` et `scope` `/push-test/`, `lang: "fr"`.

- [ ] **Step 1: Écrire les tests qui échouent** : `test_absent_without_the_setting` (les trois adresses → 404) ; `test_served_with_the_setting` (200 et types de contenu ci-dessus) ; `test_manifest_is_installable` (`display`, `start_url`, `scope`) ; `test_service_worker_shows_declarative_payloads` (le texte de `sw.js` contient `web_push` et `showNotification`).
- [ ] **Step 2: Lancer, vérifier l'échec** — FAIL.
- [ ] **Step 3: Écrire les fichiers, les vues et les adresses.**
- [ ] **Step 4: Lancer tests et contrôles, puis essai à la main** : `.env` avec `MARMOTTE_PUSH_TEST_PAGE=true` et `MARMOTTE_APP_URL=http://localhost:8001`, `uv run uvicorn marmotte.asgi:application --port 8001`, ouvrir `http://localhost:8001/push-test/` dans **Google Chrome**, activer, envoyer un test avec `python -m marmotte.notifications` lancé : la notification s'affiche et la toucher ramène la page.
- [ ] **Step 5: Commit** — `feat(notifications): add the push test page`

---

### Task 9: Filet dans la détection

**Files:**
- Create: `backend/marmotte/detection/queue_sink.py`, `backend/marmotte/detection/tests/test_queue_sink.py`
- Modify: `backend/marmotte/detection/__main__.py` (option `--print`, `QueueSink` par défaut), `backend/marmotte/detection/sinks.py` (docstring du module : plus « lot 3 adds »), `backend/marmotte/detection/tests/test_service.py` (`test_alerts_from_a_file` et `TestMain` passent `--print`)

**Interfaces:**
- Consumes: `AlertSink`, `AlertEvent` (lot 2) ; `enqueue` (tâche 3) ; `process_due`, `Clock` (tâche 5) ; `PushSender` (tâche 4).
- Produces (`marmotte.detection.queue_sink`) : `FALLBACK_DELAY = timedelta(seconds=2)`, `FALLBACK_POLL_S = 0.5`, `ENQUEUE_RETRY_S = 2.0`, `DRAIN_TIMEOUT_S = 15.0`, `FALLBACK_WORKERS = 2` ; `class QueueSink(sender: PushSender, clock: Clock = timezone.now)` (la tâche 10 ajoute le paramètre `last_resort`) :
  - `emit(event: AlertEvent) -> None` : `queue.Queue.put_nowait`, rien d'autre ;
  - `write_pending() -> None` : pour chaque alerte en attente, `enqueue(NotificationKind(event.kind.value), event.at, notification_id=event.id)` retenté pendant `ENQUEUE_RETRY_S` sur `DatabaseError` ; succès → identifiant ajouté aux alertes suivies ; échec → `logger.critical` (la tâche 10 y branche le dernier recours) ;
  - `fallback_step() -> None` : `process_due(sender, Claimant.DETECTION, clock, notification_ids=<suivies>, min_due_age=FALLBACK_DELAY, pool=…)`, puis retire des alertes suivies celles dont toutes les livraisons sont `sent`, `gone`, `failed` ou `expired` ;
  - `start() -> None` : un fil d'écriture (bloque sur la file) et un fil de secours (`fallback_step` toutes les `FALLBACK_POLL_S`) ;
  - `close(timeout_s: float = DRAIN_TIMEOUT_S) -> None` : attend que la file soit vide et qu'aucune alerte ne soit suivie, `timeout_s` au plus, puis arrête les fils ;
  - `tracked: frozenset[UUID]` (lecture, pour les tests).
  - `__main__` : sans `--print`, `prepare_environment()`, `django.setup()`, `PywebpushSender(load_or_create_vapid_key(settings.DATA_DIR), settings.APP_URL)`, `QueueSink(...)` démarré avant `run`, `close()` dans le `finally` ; les imports Django sont faits dans cette branche.

- [ ] **Step 1: Écrire les tests qui échouent** (`django_db`, horloge simulée, méthodes appelées directement, sans fils sauf indication) :
  - `test_emit_never_blocks` (`django_db(transaction=True)` : un autre fil tient une transaction d'écriture ouverte ; `emit()` rend la main en moins de 50 ms).
  - `test_writes_the_alert_with_its_id` (`write_pending()` → une `Notification` d'`id == event.id`, de type `cry`).
  - `test_sends_after_two_seconds_when_the_service_is_down` (`fallback_step()` à `t + 1,9 s` → rien envoyé ; à `t + 2 s` → livraison `sent`, `sent_by == "detection"`).
  - `test_leaves_alone_what_the_service_sent` (livraison déjà `sent` par le service → aucun envoi, alerte plus suivie).
  - `test_takes_over_a_frozen_service_after_ten_seconds` (réservée par le service à `t` : rien à `t + 9 s`, envoyée à `t + 10 s`).
  - `test_close_waits_for_the_fallback` (`django_db(transaction=True)`, fils démarrés, horloge réelle, service absent : `close()` revient après l'envoi par le filet, en moins de 15 s).
  - `TestMain.test_default_sink_is_the_queue` (`monkeypatch` de `QueueSink`, `ensure_yamnet`, `YamnetClassifier`, `AlsaSource` : `main(["--alsa", "micro"])` démarre puis ferme le `QueueSink`).

- [ ] **Step 2: Lancer, vérifier l'échec** — FAIL.
- [ ] **Step 3: Écrire `queue_sink.py`, modifier `__main__.py`, `sinks.py`, `test_service.py`.**
- [ ] **Step 4: Lancer tests et contrôles, puis le banc** : `uv run pytest -m "model or bench"` passe toujours (le banc ne doit pas importer Django : `python -c "import marmotte.detection.bench.runner, sys; assert 'django' not in sys.modules"`).
- [ ] **Step 5: Commit** — `feat(detection): queue the alerts and send them when the notifications service is down`

---

### Task 10: Dernier recours

**Files:**
- Create: `backend/marmotte/detection/last_resort.py`, `backend/marmotte/detection/tests/test_last_resort.py`
- Modify: `backend/marmotte/detection/queue_sink.py` (paramètre `last_resort: LastResort | None = None` de `QueueSink` ; `write_pending()` appelle `last_resort.send(event)` quand l'écriture échoue ; le fil de secours appelle aussi `last_resort.refresh_if_due()` et `last_resort.step()`), `backend/marmotte/detection/__main__.py` (crée le `LastResort` et le passe au `QueueSink`)

**Interfaces:**
- Consumes: `recipients` (tâche 3) ; `PushTarget`, `PushSender`, `build_message`, `SendOutcome` (tâche 4) ; `notification_content` (tâche 2) ; `BACKOFF_S`, `MIN_ATTEMPTS_BEFORE_EXPIRY` (tâche 5).
- Produces (`marmotte.detection.last_resort`) : `SNAPSHOT_EVERY_S = 60.0` ; `class LastResort(sender: PushSender, app_url: str, monotonic: Callable[[], float] = time.monotonic, clock: Clock = timezone.now)` :
  - `refresh_if_due() -> None` : toutes les `SNAPSHOT_EVERY_S`, relit les `PushTarget` des `recipients()` ; sur `DatabaseError`, garde la copie précédente et l'écrit au journal ;
  - `send(event: AlertEvent) -> None` : `logger.critical` (alerte, cause), message construit par `build_message(event.id, notification_content(kind, event.at), app_url)`, une tentative par cible de la copie ;
  - `step() -> None` : retente les envois dus (même `BACKOFF_S`, `Retry-After`), abandonne une cible sur `SENT`, `GONE`, `FAILED`, ou après la garde de l'alerte (temps monotone) **et** au moins `MIN_ATTEMPTS_BEFORE_EXPIRY` tentatives ;
  - `pending: int` (lecture, pour les tests).
- La **docstring du module** explique, en anglais : quand ce code sert (la base refuse l'écriture d'une alerte : carte SD en lecture seule, pleine, verrou, erreur d'entrée-sortie), pourquoi il existe (D99 : un babyphone ne doit pas devenir muet sur une carte qui meurt ; tout le reste du filet repose sur la base), ce qu'il fait, ses limites (destinataires de la dernière copie, 410 non enregistré, rien après un redémarrage) et le fait qu'il ne sert presque jamais, donc qu'il est couvert par des tests.

- [ ] **Step 1: Écrire les tests qui échouent** :
  - `test_sends_from_the_snapshot_when_the_database_refuses` (`django_db` ; copie faite avec deux destinataires ; `queue_sink.enqueue` remplacé par une fonction qui lève `OperationalError("disk I/O error")` ; `write_pending()` → deux envois par `FakePushSender`, aucune `Notification` en base, une ligne `CRITICAL` dans `caplog`).
  - `test_keeps_the_last_snapshot_when_reading_fails`.
  - `test_retries_in_memory_until_sent` (503 puis 201 : envoyé au second `step()` après 1 s de temps monotone).
  - `test_gives_up_after_the_ttl_and_three_attempts`.
  - `test_back_to_the_queue_when_the_database_returns` (après un échec, l'alerte suivante est écrite en base).

- [ ] **Step 2: Lancer, vérifier l'échec** — FAIL.
- [ ] **Step 3: Écrire `last_resort.py` et le brancher.**
- [ ] **Step 4: Lancer tests et contrôles** : PASS.
- [ ] **Step 5: Commit** — `feat(detection): send alerts from memory when the database refuses to store them`

---

### Task 11: Documentation

**Files:**
- Create: `docs/features/notifications.md` (skill `write-doc`), `docs/runbooks/tester-les-notifications-sur-iphone.md` (skill `write-doc`)
- Modify: `docs/technique/choix-techniques-et-architecture.md` (§ 8.3 : mention « Amendé le 2026-11-26 » pour P73, relecture toutes les 250 ms, dernier recours D99 ; § 9.1 : pywebpush derrière `PushSender`, format déclaratif ; § 9.3 : tables réelles), `docs/fonctionnel/specs-fonctionnelles.md` (§ 15 : textes du lot 3 définitifs, mention « Amendé le 2026-11-26 » ; F-26 : délais du filet), `CLAUDE.md` (commandes `python -m marmotte.notifications` et page de test ; réglages `MARMOTTE_APP_URL`, `MARMOTTE_PUSH_TEST_PAGE` ; modules `phones`, `notifications`), `backend/README.md`, `.claude/rules/api.md` (exception : les textes des notifications sont écrits par le Pi)

Le runbook donne les commandes exactes, avec `<domaine>` à la place du domaine réel :
1. `uv tool install certbot --with certbot-dns-infomaniak` sur le Pi ; jeton d'Infomaniak dans `~/.config/marmotte/infomaniak.ini` (ou la variable que l'extension attend, **à vérifier dans sa documentation au moment d'écrire le runbook**), droits 600 ; `certbot certonly --authenticator dns-infomaniak … -d sentinelle.<domaine>.fr --config-dir ~/.config/marmotte/letsencrypt --work-dir … --logs-dir …`.
2. `.env` du Pi : `MARMOTTE_APP_URL=https://sentinelle.<domaine>.fr:8443`, `DJANGO_ALLOWED_HOSTS=sentinelle.<domaine>.fr`, `MARMOTTE_PUSH_TEST_PAGE=true`.
3. `just deploy` depuis le PC, puis sur le Pi `uv run uvicorn marmotte.asgi:application --host 0.0.0.0 --port 8443 --ssl-certfile … --ssl-keyfile …` et, dans un second terminal, `uv run python -m marmotte.notifications`.
4. Repartir d'une base vide : arrêter les services, supprimer `~/marmotte/backend/.data/marmotte.sqlite3` (et ses fichiers `-wal`, `-shm`) par leurs chemins absolus, `uv run python manage.py migrate`. La clé VAPID est gardée.

- [ ] **Step 1: Écrire les docs** (skill `write-doc` pour les deux nouveaux fichiers).
- [ ] **Step 2: Vérifier** : `uvx pre-commit run --all-files` passe ; `grep -rn "<domaine réel>"` sur le dépôt ne trouve rien (le chercher avec le nom réel, sans l'écrire nulle part).
- [ ] **Step 3: Commit** — `docs(notifications): document the notifications and the iPhone test`

---

### Task 12: Test sur l'iPhone (livrable, avec l'auteur)

Fait par l'auteur sur le Pi de dev et son iPhone, en suivant le runbook ; Claude prépare les commandes et note les résultats.

- [ ] **Step 1:** certificat, `.env`, `just deploy`, serveur HTTPS et service lancés (runbook, étapes 1 à 3).
- [ ] **Step 2:** iPhone : Safari → `https://sentinelle.<domaine>.fr:8443/push-test/` → « Partager → Sur l'écran d'accueil » → ouvrir l'app → nom « iPhone » → « Activer les notifications ». PC : même chose dans Google Chrome, nom « PC ».
- [ ] **Step 3: Scénarios** (attendus du design) :
  1. « Envoyer un test » : arrive sur les deux ; la toucher sur l'iPhone ouvre la page de test.
  2. Service lancé : `uv run python -m marmotte.detection --wav bench/clips/<pleur du banc>` → l'alerte « Bébé pleure » arrive ; journal `urgency=high`.
  3. Service arrêté : même commande → l'alerte arrive, journal `sent_by=detection`.
  4. Service figé avant l'alerte (`kill -STOP <pid>`) : même commande → l'alerte arrive par le filet ; `kill -CONT <pid>` ensuite.
  5. App supprimée de l'iPhone, puis un test : noter la réponse d'Apple (410 ou non) et, si 410, l'arrivée sur Chrome de « iPhone ne reçoit plus les alertes ».
- [ ] **Step 4:** résultats ajoutés à `docs/plans/resultats-tests-prealables.md` (section « Lot 3 : notifications »), sans le domaine réel ; si Apple refuse le jeton (403 `BadJwtToken`), ouvrir une entrée au backlog avec la piste du design (en-tête VAPID gardé une heure).
- [ ] **Step 5: Commit** — `docs(notifications): add the iPhone test results`

---

### Fin du lot

- [ ] Relecture de toute la branche par un relecteur neuf (superpowers:requesting-code-review), corrections.
- [ ] Relire `docs/backlog.md` (entrées réglées ou nouvelles).
- [ ] Skill `pre-push`, puis `pr-create` (titre `feat(notifications): send push notifications with a fallback in the detection`, `Closes #5`) ; fusion par squash après accord de l'auteur ; CI verte, durée du job `detection` sur ARM notée (moins de 15 min).
- [ ] Mettre à jour la mémoire du projet (avancement du lot 3).
