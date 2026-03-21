# CHANGELOG

## [0.3.0] - 2026-03-21

### Added (EPIC-3 — Génération IA et critères de parole)
- US-3.1 Adaptateur IA local : interface unique pour Ollama/OpenAI-compatible, timeout 600 s, classification erreurs transiente/permanente
- US-3.2 Critères de parole : 5 presets (Professionnel concis, etc.) + mode personnalisé, contraintes longueur min/max
- US-3.3 Écran génération et preview : sélecteur de style, bouton Générer avec timer elapsed, double preview Journal privé / Post public, historique court, conservation workflow-centric
- Retry automatique 3× avec back-off (5 s / 10 s) sur erreurs 5xx/timeout du provider IA
- Correction bug double `/v1` dans l'URL OpenAI-compatible (`/v1/v1/chat/completions` → `/v1/chat/completions`)
- Commande Tauri `workflow_generate` convertie en `async fn` (reqwest async) — élimine le freeze de l'UI pendant la génération
- UX : auto-remplissage de la base URL selon le provider sélectionné, hints d'erreur contextuels
- 2 tests unitaires `OpenAICompatUrlNormalizationTests` (couverture normalisation URL)

### Fixed
- Crash au démarrage `Config("missing field 'version'")` : `AppSection.version` passe en `#[serde(default)]`

### Changed
- Version crate renommée `auripostao` (was `auripostao_tao_seed`), version `0.3.0`
- `package.json` aligné sur `0.3.0`

---

## [Unreleased]

### Added
- Initial project generated from tao-init v1.0.0
- Config module (`tao-core-config` or equivalent)
- Path manager module (`tao-core-paths` or equivalent)
- Logger module (`tao-core-logger` or equivalent)
- EPIC-2 socle ingestion: endpoint `POST /ingestion/preview` (multi-fichiers, dossier recursive/non-recursive, filtre `.txt/.md`, limite de taille, fallback UTF-8 -> latin-1)
- Bridge Tauri `ingestion_preview` et pickers natifs `pick_text_files` / `pick_directory`
- Ecran initial de selection de sources avec apercu d ingestion (resume, exemples de contenu, ignores, erreurs)
- US-2.0 workflow-centric: persistance des sources par `workflow_id` + endpoints `/workflows/{id}/sources` et `/workflows/{id}/ingestion/preview`
- PRD enrichi avec un schema de reference Workflow-Centric (pipeline) et des regles de decoupage EPIC/US pour prevenir les ecarts de conception
- UI restructuree en 3 onglets: Workflow Studio, Dashboard, Settings
- Workflow Studio en mode document-centrique (metadata, channels, sources, scheduler slot reserve, pre-run validation)
- Dashboard runtime avec etats connexions/systeme/db + metriques workflow/canaux
- Theme dark unifie et responsive (desktop/mobile)
- Basculage MVP de l interface en anglais

### Changed
- Affichage de l etat API en dashboard: `connected` / `disconnected` (au lieu de valeurs internes)
- Backlog: EPIC-0, EPIC-1, EPIC-2 marques Done; EPIC-3 recadre selon PRD (objectif, respect, coherence)

---

<!-- Follow Keep a Changelog: https://keepachangelog.com -->
<!-- Versions: [MAJOR.MINOR.PATCH] — follow semantic versioning -->
