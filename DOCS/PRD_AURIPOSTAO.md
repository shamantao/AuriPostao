# PRD — AuriPostao
**Nom du Projet :** AuriPostao
**Entité :** Aurica Circular / 樂循永續
**Auteur :** Philippe 江樂田
**Licence :** AGPL (Affero General Public License)
**Statut :** Draft v0.2 (Correction Vision & Stack)

---

## 1. Vision du Produit
AuriPostao est une application légère, auto-hébergée et sous licence AGPL, conçue pour générer et programmer/publier automatiquement un contenu court sur les réseaux sociaux décentralisés et/ou par email, à partir de sources personnelles, en utilisant exclusivement un modèle de langage local (LLM) via MCP Server, openai-compatible ou Ollama.

**Valeurs clés :**
- **Souveraineté :** 100% local, aucune donnée ne transite par un cloud tiers.
- **Éthique :** Licence AGPL pour garantir que les améliorations restent libres.
- **Sobriété :** Optimisé pour l'IA locale, économisant 90% de CO2 vs les API cloud.

---

## 2. Architecture & Stack Technique
- **Core Logic :** Python 3.14+ (Gestion des workflows, parsing des sources, APIs sociales).
- **Interface (GUI) :** **Tauri** (Framework Rust pour des apps desktop ultra-légères utilisant le moteur web natif de l'OS).
- **IA Engine :** Connexion flexible via :
    - **Ollama** (Local)
    - **MCP Server** (Model Context Protocol)
    - **OpenAI-compatible API** (LocalAI, vLLM, etc.)
- **Base de données :** SQLite (Local) pour l'historique et les logs.

### 2.1 — Architecture d'exécution (Décision MVP)
- **Tauri = IHM uniquement** (pas de logique métier critique).
- **Moteur applicatif = API Python locale** (loopback `127.0.0.1`, non exposée publiquement).
- **Le moteur Python gère :** orchestration des workflows, génération IA, planification, publication, retries, idempotence, métriques.
- **Tauri gère :** saisie, prévisualisation, édition, validation manuelle et pilotage des exécutions.

### 2.2 — Stockage et secrets (Décision MVP)
- **SQLite comme stockage principal** pour la portabilité (workflows, exécutions, brouillons, file d'envoi, logs).
- **Secrets :**
    - priorité au **keychain OS** quand disponible,
    - fallback SQLite chiffré si keychain indisponible,
    - jamais de secret en clair dans la config ou les logs.

---

## 3. Fonctionnalités V1 (MVP)

Nommer et enregistrer un workflow de publication. Plusieurs workflows sont possibles.

### 3.0 — Définition d'un workflow (Décision MVP)
Un workflow est composé de 6 blocs obligatoires :
1. **Source** (MVP : une ou plusieurs sources texte)
2. **Moteur IA** (provider + modèle)
3. **Critère de parole** (style de sortie)
4. **Mode d'exécution** (immédiate ou programmée)
5. **Canal de sortie** (un ou plusieurs)
6. **Règles de contrôle** (confidentialité, validation humaine, retry)

Modèles de critère de parole V1 :
- **Neutre informatif**
- **Amical conversationnel**
- **Professionnel concis**
- **Storytelling court**
- **Éducatif structuré**
- **Personnalisé** (champ libre : ton, longueur, contraintes)

### 3.1 — Ingestion de Sources
- V1 : ingestion **texte uniquement**.
- Sélection d'un ou plusieurs fichiers texte locaux (`.txt`, `.md`).
- Sélection d'un répertoire, avec inclusion optionnelle des sous-répertoires.
- Exclusions explicites V1 : images, audio, PDF, ICS, connecteurs externes.

### 3.2 — Génération IA
- Template de prompt personnalisable.
- Filtrage de confidentialité (mots-clés interdits).
- Génération d'un résumé "Journal" (privé) et d'un "Post" (public).
- Critère de parole appliqué à chaque workflow (modèle prédéfini ou personnalisé).

### 3.3 — Planification & Workflow
- Définition d'une programmation de publication avec scheduler riche.
- Scheduler V1 : immédiat, one-shot planifié, quotidien, hebdomadaire, mensuel, créneaux multiples.
- Système de "rattrapage" : si le PC est éteint à 08:00, propose la publication au démarrage.
- CheckBox: 
    - "Valider avant envoi" dans l'interface Tauri.
    - "Envoyer copie par email ?" avec champ email. Un ou plusieurs possible

### 3.4 — Canaux de Sortie (V1)
- **Email :** Envoi via SMTP (rapport quotidien).
- **Telegram :** Publication via Bot API (Canal ou Groupe).
- **Mastodon :** Publication via API REST.
- **Bluesky :** Publication via AT Protocol.
- **Règle métier :** l'utilisateur doit configurer au moins un canal valide avant de pouvoir créer un workflow.
- **Publication multicanal :** un workflow peut cibler plusieurs canaux dans une même exécution.

---

## 4. Roadmap Étendue

### V2 (Connectivité & Protocoles)
- **Nostr :** Intégration du protocole pour une publication incensurable.
- **Signal :** Intégration via `signal-cli` (nécessite un setup local spécifique).
- **Sources avancées :** Scan de dossiers, intégration  Logseq/Notion/Obsidian.
- **Audio :** Transcription Whisper locale pour dicter son journal.

### V3 (Écosystème Aurica)
- **Multi-Workflows :** Gérer plusieurs identités (Perso, Aurica, Coaching).
- **Analytics Locaux :** Suivi de l'engagement sans trackers tiers.
- **Traduction :** Module de traduction FR -> ZH (Mandarin) via modèle local spécialisé.

---

## 5. Principes de l'Interface (Tauri)
- **Légèreté :** L'app doit consommer moins de 100Mo de RAM (hors LLM).
- **Simplicité :** Un tableau de bord affichant le post du jour généré, un bouton "Éditer" et un bouton "Publier".
- **Configuration :** Écran pour saisir les clés d'API (stockées localement dans le keychain de l'OS ou en SQLite en MVP) et l'URL du serveur Ollama/MCP.
- **Onboarding :** écran de configuration des canaux obligatoire au premier lancement.
- **Garde-fou UX :** création de workflow désactivée tant qu'aucun canal n'est configuré et validé.

---

## 6. Fiabilité, Retry et Idempotence (MVP)

### 6.1 — Politique d'erreur
- Chaque exécution de workflow crée un **Run ID** unique.
- Chaque tentative de publication crée un **Attempt ID**.
- Les erreurs sont classées :
    - **Transientes** (timeout, rate limit, indisponibilité réseau)
    - **Permanentes** (auth invalide, canal mal configuré)

### 6.2 — Politique de retry
- Retry automatique uniquement pour erreurs transientes.
- Backoff exponentiel (exemple : 30s, 2m, 10m), avec plafond configurable de tentatives.
- Au-delà du plafond : statut `failed` + action utilisateur requise.
- Valeurs par défaut V1 : 3 tentatives maximum (30s, 2m, 10m).

### 6.3 — Politique d'idempotence
- Clé d'idempotence calculée avant envoi : `workflow_id + canal + scheduled_slot + hash_contenu`.
- Si une publication `success` existe déjà avec la même clé, le doublon est bloqué.
- L'idempotence est liée au **slot planifié du workflow** (pas à la journée), pour autoriser des fréquences élevées (ex: horaire).
- Une republication volontaire doit générer une nouvelle clé (action explicite utilisateur).

### 6.4 — Validation humaine et abandon automatique
- Si "Valider avant envoi" est activé, la publication attend une validation explicite.
- Si la validation n'arrive pas avant le prochain slot du même workflow :
    - le brouillon courant passe au statut `abandoned`,
    - le moteur traite le slot suivant.
- S'il n'existe pas de slot suivant, l'exécution s'arrête proprement.

### 6.5 — Pipeline et orchestration
- La cadence maximale réelle dépend du temps de génération IA et des capacités machine.
- Le scheduler doit gérer une file d'exécution pour éviter le chevauchement incohérent des runs d'un même workflow.

---

## 7. Métriques et Performance (MVP)
- Principe : mesurer d'abord, optimiser ensuite.
- Métriques collectées par run :
    - durée ingestion,
    - durée génération IA,
    - durée publication par canal,
    - nombre de retries,
    - taux de succès/échec par canal,
    - consommation mémoire app (hors LLM) sur écrans critiques.
- Les métriques sont stockées localement (SQLite) et visualisables dans une vue de diagnostic simple.

---

## 8. Stratégie de Tests et Gates de Release
- Les scripts `tao-init` fournissent la baseline qualité, mais **ne remplacent pas** les tests métier.
- Minimum obligatoire V1 :
    - tests unitaires Python (moteur),
    - tests d'intégration connecteurs (mocks/stubs),
    - tests E2E définis par EPIC selon le risque.
- Exécution locale automatique avant commit : hooks Git (pre-commit et/ou pre-push) pour lancer au minimum lint + tests unitaires rapides.
- Gate avant release :
    - checks baseline `tao-init`,
    - suite de tests verte,
    - exécution CI GitHub (PR/push),
    - blocage de tag/release si pipeline en échec.

---

## 9. Politique de Récupération des Secrets (MVP)
- Le chiffrement des secrets ne doit pas dépendre d'un email utilisateur.
- Option standard recommandée :
    - clé maître dérivée d'une passphrase locale,
    - clé de récupération (recovery key) générée une seule fois et stockée hors application par l'utilisateur.
- Si passphrase et recovery key sont perdues : impossibilité de déchiffrement, reset des secrets requis (comportement explicite).
- Un changement d'email ne doit avoir aucun impact cryptographique.

### 9.1 — Expérience d'authentification (MVP)
- La passphrase ne signifie pas une authentification complète de l'application au démarrage.
- L'application peut s'ouvrir sans passphrase, mais l'accès aux secrets est verrouillé tant que le coffre n'est pas déverrouillé.
- Le déverrouillage est demandé au premier usage d'une action nécessitant un secret (ex: test SMTP, publication).
- Option UX V1 : mémoriser le déverrouillage pour la session en cours uniquement.

---

## 10. Hors Scope V1
- Publication sur Facebook/Instagram/LinkedIn (APIs restrictives).
- Hébergement cloud (L'app est strictement "Local-First").
- Génération d'images ou de vidéos.