# CHANGELOG

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

---

<!-- Follow Keep a Changelog: https://keepachangelog.com -->
<!-- Versions: [MAJOR.MINOR.PATCH] — follow semantic versioning -->
