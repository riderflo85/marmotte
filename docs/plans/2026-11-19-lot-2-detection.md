# Lot 2 : détection des pleurs — plan détaillé

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** le service `marmotte-detection` reconnaît les pleurs (et gémissements, babillages, rires, cris) dans un flux audio et émet des alertes qui tiennent les objectifs du banc d'essai : **zéro pleur manqué au-delà de 8 secondes, au plus une fausse alerte par sieste de 2 heures** (D81).

**Architecture:** une chaîne en Python pur, sans Django, testable sur le PC : source audio → niveau et bruit de fond → YAMNet (si le niveau dépasse le bruit de fond) → fenêtre glissante → filet « hurlement » → anti-rafale → alerte. Le modèle est isolé derrière une interface `Classifier` (D62). Le banc d'essai rejoue des sons sous licence libre à travers la même chaîne et mesure les pleurs manqués et les fausses alertes. Les alertes sortent ici vers un journal ; le lot 3 les branchera sur la file d'envoi.

**Tech Stack:** Python 3.14, numpy, scipy (`resample_poly`), soundfile (lecture WAV/FLAC), sounddevice (ALSA), ai-edge-litert, modèle YAMNet de classification au format LiteRT, pytest.

**Spec:** `docs/technique/choix-techniques-et-architecture.md` § 8 (chaîne, précautions, banc, limites) ; `docs/fonctionnel/specs-fonctionnelles.md` F-17 à F-23, NF-04 ; notes P10 à P18, D23 à D25, D62, D81.

## Global Constraints

- Voir `docs/plans/2026-11-19-plan-directeur-v1.md`, « Global Constraints ».
- Format interne du son : **mono, 16 000 Hz, `float32`, valeurs dans [-1, 1]** ; tranche YAMNet de **15 600 échantillons** (0,975 s) ; pas de **7 800 échantillons** (0,4875 s) entre deux tranches.
- Catégories retenues (P10, P16), par nom dans `yamnet_class_map.csv` : `"Baby cry, infant cry"` → `cry`, `"Whimper"` → `whimper`, `"Babbling"` → `babble`, `"Baby laughter"` → `laugh`, `"Screaming"` → `scream`. Une catégorie peut regrouper plusieurs noms YAMNet (son score est le plus haut des leurs) : l'ajout de `"Crying, sobbing"` à `cry` est évalué en tâche 8 (lot 0 : cette catégorie sortait souvent en tête pendant des pleurs).
- Micro réel (lot 0) : l'INMP441 n'émet que sur le **canal gauche** ; il se lit en stéréo et on garde le gauche (du mono demandé à `plug` ferait la moyenne avec le canal muet, soit -6 dB). Il capte aussi des variations de pression lentes (1 à 2 Hz) vers -50 dBFS : le **niveau** se mesure après un filtre passe-haut.
- Alertes **seulement en mode `sieste`** ; en `silent` (Surveillance silencieuse), **ni alerte ni filet** (F-13, P23).
- Objectifs bloquants (D81) : pleurs de plus de 8 s manqués = **0** ; fausses alertes **≤ 1 par 2 heures** de bruits de fond.
- Sons du banc publié : **CC0 ou CC BY uniquement**, avec crédits ; **aucune vidéo YouTube** dans le dépôt (D81). Modèle YAMNet sous Apache 2.0 ; jamais committé (téléchargé et vérifié par empreinte SHA-256).
- Ce module **n'importe pas Django** : il doit tourner seul (D82).

## Review Focus

1. **Micro muet** (module débranché, zéros parfaits) : après 10 s de silence numérique, `stats.mic_silent` passe à vrai (test dans la tâche 2).
2. **Porte qui claque** (0,3 s très fort) : aucune alerte (test dans la tâche 5).
3. **Arrivée en pleine fête** (musique forte dès le démarrage) : aucune alerte du filet pendant l'adaptation du bruit de fond (test dans la tâche 5).
4. **Bébé qui pleure par-dessus la musique** (6 dB au-dessus du bruit de fond) : l'alerte part quand même (test dans la tâche 5).
5. **Son saturé ou abîmé** (valeurs hors de [-1, 1], `NaN`) : pas de plantage, valeurs nettoyées (test dans la tâche 1).
6. **Variations lentes du micro** (1 à 2 Hz vers -50 dBFS, mesurées au lot 0) : retirées par le filtre passe-haut avant la mesure du niveau, sinon le bruit de fond serait fixé 18 dB trop haut (test dans la tâche 2).

---

### Task 1: Types communs et sources audio

**Files:**
- Create: `backend/marmotte/common/__init__.py`, `backend/marmotte/common/enums.py`, `backend/marmotte/detection/__init__.py`, `backend/marmotte/detection/types.py`, `backend/marmotte/detection/audio.py`
- Modify: `backend/pyproject.toml` (dépendances `numpy`, `scipy`, `soundfile`, `sounddevice`)
- Test: `backend/marmotte/detection/tests/test_audio.py`

**Interfaces:**
- Produces:
  - `marmotte.common.enums` : `class Mode(StrEnum)` : `STARTING = "starting"`, `COUNTDOWN = "countdown"`, `SIESTE = "sieste"`, `SILENT = "silent"`, `MAINTENANCE = "maintenance"` ; `class SoundClass(StrEnum)` : `CRY = "cry"`, `WHIMPER = "whimper"`, `BABBLE = "babble"`, `LAUGH = "laugh"`, `SCREAM = "scream"` ; `class Sensitivity(StrEnum)` : `LOW = "low"`, `MEDIUM = "medium"`, `HIGH = "high"`. Partagés par tous les services (le lot 4 les réutilise).
  - `marmotte.detection.types` : `SAMPLE_RATE = 16_000`, `WINDOW = 15_600`, `HOP = 7_800` ; `Audio = NDArray[np.float32]` ; `@dataclass(frozen=True) class AlertEvent(id: UUID, kind: SoundClass, at: datetime, offset_s: float, via_scream_net: bool)`.
  - `marmotte.detection.audio` : `to_mono_16k(data: NDArray[np.floating], rate: int) -> Audio` ; `class AudioSource(Protocol): def read(self, n: int) -> Audio | None` (`None` = fin du flux) ; `ArraySource(samples: Audio)` ; `WavFileSource(path: Path, loop: bool = False)` ; `AlsaSource(device: str = "micro", block: int = HOP, channel: int = 0)`.

- [ ] **Step 1: Écrire les tests qui échouent**

```python
def test_to_mono_16k_downmixes_and_resamples():
    stereo_48k = np.ones((48_000, 2), dtype=np.float32) * 0.5
    out = to_mono_16k(stereo_48k, 48_000)
    assert out.dtype == np.float32 and out.shape == (16_000,)
    assert np.allclose(out[100:-100], 0.5, atol=1e-3)

def test_to_mono_16k_cleans_nan_and_clips():
    out = to_mono_16k(np.array([np.nan, 2.0, -3.0, 0.25], dtype=np.float32), 16_000)
    assert out.tolist() == [0.0, 1.0, -1.0, 0.25]

def test_wav_file_source_reads_then_ends(tmp_path):  # écrit 1 s de FLAC 48 kHz stéréo avec soundfile
    src = WavFileSource(path)
    assert src.read(16_000).shape == (16_000,)
    assert src.read(16_000) is None

def test_wav_file_source_loops(tmp_path):
    src = WavFileSource(path, loop=True)
    for _ in range(3):
        assert src.read(16_000) is not None

@pytest.mark.hardware
def test_alsa_source_reads_shared_micro():
    assert AlsaSource().read(HOP).shape == (HOP,)
```

- [ ] **Step 2: Vérifier qu'ils échouent** — Run: `cd backend && uv run pytest marmotte/detection/tests/test_audio.py -v -m "not hardware"` — Expected: FAIL (modules absents).
- [ ] **Step 3: Implémenter** : `to_mono_16k` fait la moyenne des canaux, rééchantillonne par `scipy.signal.resample_poly` (rapport réduit par PGCD), remplace `NaN`/infinis par 0 et borne à [-1, 1]. `WavFileSource` lit tout le fichier avec `soundfile`, le convertit une fois, puis sert des tranches ; la dernière tranche incomplète est complétée par des zéros. `AlsaSource` ouvre un `sounddevice.InputStream` **stéréo** 16 kHz `float32` sur le périphérique ALSA donné (le module `plug` d'ALSA convertit la fréquence, lot 0 tâche 5) et garde le canal `channel` (0 = gauche, celui de l'INMP441 ; Global Constraints).
- [ ] **Step 4: Vérifier** — Run: `uv run pytest marmotte/detection/tests/test_audio.py -v -m "not hardware" && uv run pyright` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(detection): add shared enums and audio sources"`

---

### Task 2: Niveau sonore, bruit de fond et santé du micro

**Files:**
- Create: `backend/marmotte/detection/level.py`
- Test: `backend/marmotte/detection/tests/test_level.py`

**Interfaces:**
- Produces: `SILENCE_DB = -120.0` ; `rms_dbfs(frame: Audio) -> float` ; `class HighPass(cutoff_hz: float = 80.0, order: int = 2)` avec `process(frame: Audio) -> Audio` ; `class NoiseFloor(warmup_s: float = 10.0, rise_db_per_s: float = 0.1, fall_tau_s: float = 2.0)` avec `update(level_db: float, dt: float) -> float` et `value_db: float` ; `class MicHealth(silent_db: float = -100.0, silent_after_s: float = 10.0)` avec `update(level_db: float, dt: float) -> None` et `is_silent: bool`.

- [ ] **Step 1: Écrire les tests qui échouent**

```python
def test_rms_of_full_scale_sine_is_minus_3_dbfs():
    t = np.arange(16_000) / 16_000
    assert rms_dbfs(np.sin(2 * np.pi * 440 * t).astype(np.float32)) == pytest.approx(-3.01, abs=0.05)

def test_rms_of_silence_is_floor():
    assert rms_dbfs(np.zeros(HOP, dtype=np.float32)) == SILENCE_DB

def test_high_pass_removes_slow_drift():             # lot 0 : variations de 1 à 2 Hz vers -50 dBFS
    t = np.arange(16_000 * 4) / 16_000
    drift = (0.0045 * np.sin(2 * np.pi * 1.5 * t)).astype(np.float32)
    hp = HighPass()
    out = np.concatenate([hp.process(c) for c in np.split(drift, 8)])  # état gardé d'un appel à l'autre
    assert rms_dbfs(out[16_000:]) < -90.0

def test_high_pass_keeps_voice_band():
    t = np.arange(16_000) / 16_000
    tone = np.sin(2 * np.pi * 500 * t).astype(np.float32)
    assert rms_dbfs(HighPass().process(tone)[4_000:]) == pytest.approx(-3.01, abs=0.2)

def test_noise_floor_starts_at_first_level():
    nf = NoiseFloor()
    nf.update(-20.0, 0.4875)
    assert nf.value_db == pytest.approx(-20.0)

def test_noise_floor_converges_during_warmup():
    nf = NoiseFloor()
    nf.update(-60.0, 0.4875)
    for _ in range(19):                       # 20 × 0,4875 s < 10 s
        nf.update(-20.0, 0.4875)
    assert nf.value_db == pytest.approx(-20.0, abs=1.0)

def test_noise_floor_falls_fast_and_rises_slowly_after_warmup():
    nf = warmed_up_floor(-50.0)                # aide : 30 s à -50 dB
    nf.update(-20.0, 1.0)
    assert nf.value_db <= -49.85               # monte d'au plus 0,1 dB/s
    for _ in range(10):
        nf.update(-70.0, 1.0)
    assert nf.value_db < -68.0                 # descend vite

def test_mic_health_flags_digital_silence_after_10_s():
    mh = MicHealth()
    for _ in range(21):
        mh.update(SILENCE_DB, 0.4875)
    assert mh.is_silent
    mh.update(-60.0, 0.4875)
    assert not mh.is_silent
```

- [ ] **Step 2: Vérifier qu'ils échouent** — Run: `uv run pytest marmotte/detection/tests/test_level.py -v` — Expected: FAIL.
- [ ] **Step 3: Implémenter** : `rms_dbfs` = 20·log10(RMS), borné à `SILENCE_DB`. `HighPass` : filtre de Butterworth (`scipy.signal.butter(order, cutoff_hz, "highpass", fs=SAMPLE_RATE, output="sos")`) appliqué par `sosfilt` en gardant l'état (`zi`) d'un appel à l'autre ; il ne sert qu'à la mesure du niveau, YAMNet reçoit le son non filtré. `NoiseFloor` : **le premier niveau mesuré initialise le bruit de fond** (arrivée en pleine fête, Review Focus 3) ; pendant `warmup_s`, il suit le niveau dans les deux sens avec une constante de temps de 1 s ; ensuite, descend vers un niveau plus bas avec la constante `fall_tau_s`, et monte vers un niveau plus haut d'au plus `rise_db_per_s` par seconde. `MicHealth` : vrai quand le niveau reste sous `silent_db` pendant `silent_after_s` d'affilée.
- [ ] **Step 4: Vérifier** — Run: `uv run pytest marmotte/detection/tests/test_level.py -v` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(detection): add level, noise floor and mic health"`

---

### Task 3: Classifieur YAMNet

**Files:**
- Create: `backend/marmotte/detection/classifier.py`, `backend/marmotte/detection/model_files.py`, `backend/marmotte/detection/data/yamnet_class_map.csv` (copié de `tensorflow/models`, `research/audioset/yamnet/`, Apache 2.0), `backend/models/models.toml`, `backend/marmotte/detection/tests/fakes.py`, `backend/marmotte/detection/tests/fixtures/cry_cc0.flac` (court pleur CC0, crédité dans `backend/bench/CREDITS.md`)
- Modify: `backend/pyproject.toml` (dépendance `ai-edge-litert`)
- Test: `backend/marmotte/detection/tests/test_classifier.py`

**Interfaces:**
- Produces: `class Classifier(Protocol): def scores(self, window: Audio) -> Mapping[SoundClass, float]` ; `YAMNET_NAMES: dict[SoundClass, tuple[str, ...]]` (Global Constraints ; au départ un seul nom par catégorie) ; `DEFAULT_CLASS_MAP: Path` (le CSV du paquet) ; `load_class_names(path: Path) -> list[str]` ; `class YamnetClassifier(model_path: Path, class_map: Path = DEFAULT_CLASS_MAP)` ; `ensure_yamnet(models_dir: Path) -> Path` ; `class ModelChecksumError(Exception)`. Dans les tests (`marmotte/detection/tests/fakes.py`) : `FakeClassifier(rule: Callable[[Audio], Mapping[SoundClass, float]])`, appelé avec la tranche ; `loud_is_cry(threshold_db: float) -> FakeClassifier` (renvoie `{CRY: 0.9}` si le niveau de la tranche dépasse `threshold_db`, sinon `{}`) ; `silent() -> FakeClassifier` (renvoie toujours `{}`).

- [ ] **Step 1: Récupérer le modèle** : le modèle YAMNet **de classification** au format LiteRT (entrée de 15 600 échantillons, sortie de 521 scores). URL candidate, **à vérifier** : `https://storage.googleapis.com/download.tensorflow.org/models/tflite/task_library/audio_classification/rpi/lite-model_yamnet_classification_tflite_1.tflite` ; sinon la variante `tfLite/classification-tflite` de `google/yamnet` sur Kaggle. Noter l'URL, l'empreinte SHA-256 et la licence dans `backend/models/models.toml` (`[yamnet] url, sha256, file, license`).
- [ ] **Step 2: Écrire les tests qui échouent**

```python
def test_class_map_contains_all_retained_classes():
    retained = {name for group in YAMNET_NAMES.values() for name in group}
    assert retained <= set(load_class_names(DEFAULT_CLASS_MAP))

def test_ensure_yamnet_rejects_bad_checksum(tmp_path, monkeypatch):
    # models.toml d'essai avec un sha256 faux, téléchargement simulé
    with pytest.raises(ModelChecksumError):
        ensure_yamnet(tmp_path)

@pytest.mark.model
def test_yamnet_returns_retained_classes_only():
    scores = yamnet().scores(np.zeros(WINDOW, dtype=np.float32))
    assert set(scores) == set(SoundClass)
    assert all(0.0 <= v <= 1.0 for v in scores.values())

@pytest.mark.model
def test_yamnet_scores_cry_fixture_as_cry():
    window = first_window_of(FIXTURES / "cry_cc0.flac")  # FIXTURES = Path(__file__).parent / "fixtures"
    assert yamnet().scores(window)[SoundClass.CRY] > 0.3
```

- [ ] **Step 3: Vérifier qu'ils échouent** — Run: `uv run pytest marmotte/detection/tests/test_classifier.py -v` — Expected: FAIL.
- [ ] **Step 4: Implémenter** : `ensure_yamnet` lit `models.toml`, télécharge le fichier s'il manque, vérifie le SHA-256, lève `ModelChecksumError` sinon. `YamnetClassifier` charge le modèle avec `ai_edge_litert.interpreter.Interpreter`, trouve les indices des catégories retenues **par leur nom** dans la table des classes (jamais par numéro en dur), et renvoie leurs scores ; le score d'une catégorie est le plus haut des scores de ses noms YAMNet. `FakeClassifier` dans `marmotte/detection/tests/fakes.py`.
- [ ] **Step 5: Vérifier** — Run: `uv run pytest marmotte/detection/tests/test_classifier.py -v` (après `ensure_yamnet`) — Expected: PASS, tests `model` compris.
- [ ] **Step 6: Commit** — `git commit -m "feat(detection): add YAMNet classifier behind Classifier interface"`

---

### Task 4: Décision : fenêtre glissante, filet « hurlement », anti-rafale

**Files:**
- Create: `backend/marmotte/detection/decision.py`
- Test: `backend/marmotte/detection/tests/test_decision.py`

**Interfaces:**
- Produces: `THRESHOLDS: dict[Sensitivity, float] = {LOW: 0.5, MEDIUM: 0.3, HIGH: 0.15}` (valeurs de départ, réglées en tâche 8) ; `BABY_CLASSES = (CRY, WHIMPER, BABBLE, LAUGH)` (ordre = priorité en cas d'égalité) ; `class SlidingWindowDecider(threshold: float, n: int = 4, k: int = 2)` avec `push(scores: Mapping[SoundClass, float]) -> SoundClass | None` ; `class ScreamNet(margin_db: float = 25.0, min_duration_s: float = 1.0, score_threshold: float = 0.5)` avec `push(level_db: float, floor_db: float, scream_score: float, dt: float) -> bool` ; `class AntiBurst(pause_s: float = 60.0)` avec `allow(now_s: float, via_scream_net: bool) -> bool`.

- [ ] **Step 1: Écrire les tests qui échouent**

```python
def test_decider_needs_k_positive_slices_among_last_n():
    d = SlidingWindowDecider(threshold=0.3)
    assert d.push({CRY: 0.9}) is None
    assert d.push({CRY: 0.1}) is None
    assert d.push({CRY: 0.8}) == CRY

def test_decider_forgets_slices_older_than_n():
    d = SlidingWindowDecider(threshold=0.3)
    d.push({CRY: 0.9})
    for _ in range(4):
        d.push({})
    assert d.push({CRY: 0.9}) is None

def test_decider_prefers_cry_on_tie():
    d = SlidingWindowDecider(threshold=0.3)
    d.push({CRY: 0.9, BABBLE: 0.9})
    assert d.push({CRY: 0.9, BABBLE: 0.9}) == CRY

def test_scream_net_fires_after_one_second_far_above_floor():
    net = ScreamNet()
    assert not net.push(-20.0, -50.0, 0.0, 0.4875)
    assert not net.push(-20.0, -50.0, 0.0, 0.4875)
    assert net.push(-20.0, -50.0, 0.0, 0.4875)

def test_scream_net_fires_at_once_on_scream_score():
    assert ScreamNet().push(-40.0, -50.0, 0.8, 0.4875)

def test_scream_net_fires_once_per_episode():
    net = ScreamNet()
    fired = [net.push(-20.0, -50.0, 0.0, 0.4875) for _ in range(10)]
    assert fired.count(True) == 1
    net.push(-48.0, -50.0, 0.0, 0.4875)          # retour sous la marge : réarmé
    assert any(net.push(-20.0, -50.0, 0.0, 0.4875) for _ in range(3))

def test_anti_burst_blocks_during_pause_but_not_screams():
    ab = AntiBurst(pause_s=60.0)
    assert ab.allow(0.0, via_scream_net=False)
    assert not ab.allow(30.0, via_scream_net=False)
    assert ab.allow(31.0, via_scream_net=True)
    assert ab.allow(61.0, via_scream_net=False)
```

- [ ] **Step 2: Vérifier qu'ils échouent** — Run: `uv run pytest marmotte/detection/tests/test_decision.py -v` — Expected: FAIL.
- [ ] **Step 3: Implémenter** selon les interfaces : une tranche est « positive » pour une catégorie si son score dépasse le seuil ; le décideur renvoie la catégorie de `BABY_CLASSES` qui a au moins `k` tranches positives parmi les `n` dernières (priorité dans l'ordre de `BABY_CLASSES`). `ScreamNet` cumule la durée pendant laquelle `level_db - floor_db >= margin_db` (remise à zéro sinon) et renvoie vrai dès `min_duration_s`, ou tout de suite si `scream_score >= score_threshold` ; il ne se déclenche **qu'une fois par épisode** et se réarme quand le niveau repasse sous la marge et le score sous le seuil (sinon un long cri, qui passe outre l'anti-rafale, sonnerait toutes les secondes). `AntiBurst.allow` mémorise l'instant de chaque alerte autorisée.
- [ ] **Step 4: Vérifier** — Run: `uv run pytest marmotte/detection/tests/test_decision.py -v` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(detection): add sliding window, scream net and anti-burst"`

---

### Task 5: Pipeline, sorties et service

**Files:**
- Create: `backend/marmotte/detection/pipeline.py`, `backend/marmotte/detection/sinks.py`, `backend/marmotte/detection/service.py`, `backend/marmotte/detection/__main__.py`
- Test: `backend/marmotte/detection/tests/test_pipeline.py`, `backend/marmotte/detection/tests/test_service.py`

**Interfaces:**
- Consumes: tâches 1 à 4.
- Produces:
  - `@dataclass(frozen=True) class DetectionConfig(gate_margin_db: float = 6.0, n: int = 4, k: int = 2, sensitivity: Sensitivity = MEDIUM, scream_margin_db: float = 25.0, pause_s: float = 60.0)` ;
  - `@dataclass(frozen=True) class PipelineStats(level_db: float, floor_db: float, mic_silent: bool, last_alert: AlertEvent | None)` ;
  - `class DetectionPipeline(classifier: Classifier, config: DetectionConfig, mode_provider: Callable[[], Mode], start: datetime)` avec `feed(chunk: Audio) -> list[AlertEvent]` et `stats: PipelineStats` (utilisé par le lot 10) ;
  - `class AlertSink(Protocol): def emit(self, event: AlertEvent) -> None` ; `class JsonLinesSink(stream: TextIO)` (le lot 3 ajoutera la sortie vers la file d'envoi) ;
  - `run(source: AudioSource, pipeline: DetectionPipeline, sink: AlertSink) -> None` (lit par pas de `HOP` jusqu'à `None`) ;
  - ligne de commande : `python -m marmotte.detection (--wav CHEMIN [--loop] | --alsa PÉRIPHÉRIQUE) [--sensitivity low|medium|high] [--models-dir CHEMIN]`, mode fixé à `sieste` (le lot 4 branchera le vrai mode).

- [ ] **Step 1: Écrire les tests qui échouent** (avec les faux classifieurs de la tâche 3 et du son synthétique ; aides de test : `noise(seconds, dbfs)` = bruit blanc au niveau donné, concaténable ; `pipeline(mode, classifier)` = `DetectionPipeline` avec `DetectionConfig()` et un mode fixe ; `feed_all(p, audio)` = alimente par pas de `HOP` et renvoie toutes les alertes)

```python
def test_cry_alert_within_8_s_of_onset():
    # « pleur » 20 dB au-dessus du fond : sous la marge du filet (25 dB), au-dessus de la porte (6 dB)
    alerts = feed_all(pipeline(SIESTE, loud_is_cry(-45)), noise(20, -55) + noise(15, -35))
    assert alerts and alerts[0].kind == CRY and not alerts[0].via_scream_net
    assert 20.0 <= alerts[0].offset_s <= 28.0

def test_no_alert_outside_sieste():
    assert feed_all(pipeline(SILENT, loud_is_cry(-45)), noise(20, -55) + noise(15, -10)) == []

def test_door_slam_does_not_alert():                         # Review Focus 2
    assert feed_all(pipeline(SIESTE, silent()), noise(20, -55) + noise(0.3, -3) + noise(10, -55)) == []

def test_loud_party_from_start_does_not_trigger_scream_net():  # Review Focus 3
    assert feed_all(pipeline(SIESTE, silent()), noise(60, -20)) == []

def test_cry_6_db_over_loud_music_still_alerts():             # Review Focus 4
    alerts = feed_all(pipeline(SIESTE, loud_is_cry(-22)), noise(40, -25) + noise(15, -19))
    assert any(a.kind == CRY for a in alerts)

def test_stats_report_mic_silence():                          # Review Focus 1
    p = pipeline(SIESTE, silent())
    feed_all(p, np.zeros(16_000 * 11, dtype=np.float32))
    assert p.stats.mic_silent

def test_cli_prints_alerts_as_json_lines(tmp_path, capsys):   # test_service.py, run() + JsonLinesSink
    run(ArraySource(cry_signal), fake_pipeline, JsonLinesSink(sys.stdout))
    assert json.loads(capsys.readouterr().out.splitlines()[0])["kind"] == "cry"
```

- [ ] **Step 2: Vérifier qu'ils échouent** — Run: `uv run pytest marmotte/detection/tests/test_pipeline.py marmotte/detection/tests/test_service.py -v` — Expected: FAIL.
- [ ] **Step 3: Implémenter `DetectionPipeline.feed`** : accumule le son ; pour chaque pas de `HOP` complet, calcule le niveau du pas **après le filtre `HighPass`** (le classifieur reçoit le son non filtré), met à jour `NoiseFloor` et `MicHealth` (avec `dt = HOP / SAMPLE_RATE`) ; la porte est ouverte si un des pas de la tranche courante dépasse le bruit de fond de `gate_margin_db` ; si la porte est ouverte et que la tranche de `WINDOW` échantillons est complète, demande les scores au classifieur, sinon pousse des scores vides au décideur ; consulte `ScreamNet` (niveau, bruit de fond, score `scream`) ; si `mode_provider()` vaut `SIESTE` et qu'une décision ou le filet se déclenche et que `AntiBurst` l'autorise, crée un `AlertEvent` (`offset_s` = position dans le flux, `at = start + offset`).
- [ ] **Step 4: Implémenter `JsonLinesSink`, `run` et `__main__`** selon les interfaces ; `__main__` journalise aussi `stats` toutes les 10 secondes sur la sortie d'erreur.
- [ ] **Step 5: Vérifier** — Run: `uv run pytest marmotte/detection/tests -v -m "not hardware and not model" && uv run pyright` — Expected: PASS.
- [ ] **Step 6: Commit** — `git commit -m "feat(detection): add detection pipeline and service entry point"`

---

### Task 6: Banc d'essai : manifeste, préparation des sons, mesures

**Files:**
- Create: `backend/marmotte/detection/bench/__init__.py`, `.../bench/manifest.py`, `.../bench/prepare.py`, `.../bench/runner.py`, `.../bench/__main__.py`, `backend/bench/manifest.toml` (vide au départ), `backend/bench/CREDITS.md`
- Test: `backend/marmotte/detection/tests/test_bench.py`

**Interfaces:**
- Produces:
  - format de `manifest.toml` : des entrées `[[clip]]` avec `file` (chemin relatif), `label` (`cry`, `whimper`, `babble`, `laugh`, `scream`, `background`), `tags` (ex. `["room"]` pour un fond de pièce calme, `["music"]`, `["tv"]`), `source` (URL), `author`, `license` (`CC0-1.0`, `CC-BY-3.0`, `CC-BY-4.0` seulement), `segments` (liste de `[début, fin]` en secondes, pour les sons de bébé) ;
  - `load_manifest(path: Path) -> list[Clip]` (refuse toute autre licence) ;
  - `missed_long_cries(segments: list[tuple[float, float]], alert_offsets: list[float], shift_s: float, long_s: float = 8.0, budget_s: float = 8.0) -> tuple[int, int]` (nombre de pleurs longs, nombre manqués) ;
  - `false_alerts_per_2h(n_alerts: int, seconds: float) -> float` ;
  - `@dataclass class BenchReport(long_cries: int, missed_long_cries: int, false_alerts: int, background_s: float, false_alerts_per_2h: float, recall_by_label: dict[str, float])` avec `meets_targets() -> bool` (`missed_long_cries == 0 and false_alerts_per_2h <= 1.0`) ;
  - `run_bench(clips: list[Clip], make_pipeline: Callable[[Callable[[], Mode]], DetectionPipeline], seed: int = 42) -> BenchReport` ;
  - `make_yamnet_pipeline(mode_provider: Callable[[], Mode], config: DetectionConfig = DetectionConfig()) -> DetectionPipeline` (YAMNet via `ensure_yamnet(Path("models"))`, `start` fixe au 2026-01-01 00:00 UTC pour des résultats reproductibles) ;
  - commandes : `python -m marmotte.detection.bench prepare ENTRÉE --label L --source URL --author A --license LIC [--segments "0:12.5,20:31"] [--tags room,music]` (convertit en FLAC mono 16 kHz dans `bench/clips/`, ajoute l'entrée au manifeste et la ligne de crédit) et `python -m marmotte.detection.bench run [--manifest CHEMIN] [--local]` (affiche le rapport, code de sortie 1 si les objectifs ne sont pas tenus ; `--local` ajoute `bench/local/manifest.toml`, ignoré par Git, pour les essais à partir de vidéos).

- [ ] **Step 1: Écrire les tests qui échouent**

```python
def test_long_cry_detected_within_budget_is_not_missed():
    assert missed_long_cries([(0.0, 12.0)], [13.5], shift_s=10.0) == (1, 0)

def test_long_cry_detected_too_late_is_missed():
    assert missed_long_cries([(0.0, 12.0)], [19.0], shift_s=10.0) == (1, 1)

def test_short_cry_is_not_counted_as_long():
    assert missed_long_cries([(0.0, 5.0)], [], shift_s=10.0) == (0, 0)

def test_false_alert_rate_is_scaled_to_two_hours():
    assert false_alerts_per_2h(1, 3600.0) == 2.0

def test_manifest_rejects_non_free_license(tmp_path):
    with pytest.raises(ValueError):
        load_manifest(manifest_with(license="CC-BY-NC-4.0"))

def test_report_meets_targets_only_with_zero_missed_and_at_most_one_fa():
    assert BenchReport(10, 0, 1, 7200.0, 1.0, {}).meets_targets()
    assert not BenchReport(10, 1, 0, 7200.0, 0.0, {}).meets_targets()
```

- [ ] **Step 2: Vérifier qu'ils échouent** — Run: `uv run pytest marmotte/detection/tests/test_bench.py -v` — Expected: FAIL.
- [ ] **Step 3: Implémenter** selon les interfaces. `run_bench` : pour chaque son de bébé, un flux = 10 s de fond calme (un son étiqueté `room`, à son niveau d'origine) + le son + 5 s de fond calme, rejoué dans un pipeline neuf en mode `sieste` (le décalage de 10 s couvre l'adaptation du bruit de fond, comme le compte à rebours de 30 s dans la réalité) ; pour les fonds, une seule longue séquence d'au moins **7 200 s**, formée des sons `background` tirés dans un ordre aléatoire (graine 42) avec un gain aléatoire entre -6 et +6 dB.
- [ ] **Step 4: Vérifier** — Run: `uv run pytest marmotte/detection/tests/test_bench.py -v` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(detection): add bench manifest, preparation and metrics"`

---

### Task 7: Constituer le jeu de sons du banc

**Files:**
- Modify: `backend/bench/manifest.toml`, `backend/bench/CREDITS.md`
- Create: `backend/bench/clips/*.flac`

- [ ] **Step 1: Chercher les sons** sur Freesound (<https://freesound.org/>) avec le filtre de licence **CC0** ou **Attribution** (jamais « Noncommercial »), et vérifier la licence **de chaque son** sur sa page. Objectifs minimaux :
  - **pleurs** : 30 sons, dont au moins **15 pleurs continus de plus de 8 secondes** ;
  - **gémissements, babillages, rires de bébé, cris** : 10 sons chacun ;
  - **fonds** : 40 sons, au moins une heure au total, variés : pièce calme (`room`, au moins 3), conversation, télévision, musique, fête, cuisine, toux et éternuements d'adulte, chat et chien. **Aucun autre bébé ni enfant qui pleure** dans les fonds.
- [ ] **Step 2: Préparer chaque son** avec `python -m marmotte.detection.bench prepare …`, en relevant à l'écoute (ex. avec Audacity) les segments de pleur `début:fin` des sons de bébé.
- [ ] **Step 3: Vérifier le jeu**

Run: `uv run python -c "from marmotte.detection.bench.manifest import load_manifest; c = load_manifest(Path('bench/manifest.toml')); print(len(c))" && du -sh bench/clips`
Expected: au moins 110 sons chargés sans erreur de licence ; **moins de 60 Mo** au total.

- [ ] **Step 4: Commit** — `git commit -m "test(detection): add free-licensed bench clips with credits"`

---

### Task 8: Régler les seuils et brancher le banc dans la CI

**Files:**
- Modify: `backend/marmotte/detection/pipeline.py` (`DetectionConfig` par défaut), `backend/marmotte/detection/decision.py` (`THRESHOLDS`), `backend/marmotte/detection/classifier.py` (`YAMNET_NAMES`), `.github/workflows/ci.yml`
- Create: `backend/marmotte/detection/tests/test_bench_targets.py`

- [ ] **Step 1: Écrire le test du banc**

```python
@pytest.mark.bench
def test_bench_meets_d81_targets():
    report = run_bench(load_manifest(BENCH_MANIFEST), make_yamnet_pipeline)
    assert report.missed_long_cries == 0
    assert report.false_alerts_per_2h <= 1.0
```

- [ ] **Step 2: Lancer le banc** — Run: `cd backend && uv run python -m marmotte.detection.bench run` — Expected: un rapport (pleurs longs, manqués, fausses alertes par 2 h, rappel par catégorie). Probablement en échec au premier essai.
- [ ] **Step 3: Régler** `gate_margin_db`, `n`, `k`, `THRESHOLDS[MEDIUM]`, `scream_margin_db` et `pause_s` jusqu'à tenir les objectifs, en restant dans le budget de 8 s. Évaluer aussi l'ajout de `"Crying, sobbing"` à `YAMNET_NAMES[CRY]` (lot 0) : le garder si les pleurs manqués baissent sans ajouter de fausses alertes. Noter les valeurs retenues et le rapport final dans `docs/plans/resultats-tests-prealables.md`, section « Banc de détection ».
- [ ] **Step 4: Règle d'arrêt** : si aucun réglage ne tient les objectifs, arrêt et retour vers l'auteur avec le rapport : la piste prévue est d'essayer EfficientAT derrière la même interface `Classifier` (D62).
- [ ] **Step 5: Vérifier** — Run: `uv run pytest -m "model or bench" -v` — Expected: PASS.
- [ ] **Step 6: Ajouter le job `detection` à la CI** : déclenché quand `backend/marmotte/detection/**`, `backend/bench/**` ou `backend/models/**` changent ; cache du modèle par empreinte de `backend/models/models.toml` ; `uv run python -c "from marmotte.detection.model_files import ensure_yamnet; ensure_yamnet(Path('models'))"` puis `uv run pytest -m "model or bench"`. Un échec bloque la fusion (P67).
- [ ] **Step 7: Commit** — `git commit -m "ci(detection): gate merges on bench targets"`
