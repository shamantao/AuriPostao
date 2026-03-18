# Backlog V1 - AuriPostao

Date: 2026-03-18
Source: PRD AuriPostao (v0.2 enrichi)
Approche: Vertical slice par EPIC (socle + interface Tauri testable a chaque EPIC)

## Regles de backlog
- Chaque EPIC a un objectif precis et testable.
- Chaque EPIC contient au minimum:
  - une US socle (backend/API/DB),
  - une US interface Tauri,
  - un scenario de test humain de bout en bout.
- Les canaux de publication sont livres un par un, chacun dans sa propre US.
- EPIC-0 est obligatoire et basee sur tao-init.

## EPIC-0 - Foundation projet via tao-init
Objectif testable:
Le projet AuriPostao est genere, structure et executable localement avec les conventions tao-init, les checks baseline verts, une base Tauri + API Python connectee, et un espace GitHub pret pour piloter le delivery par US.

US:
- US-0.1 (Socle) - Generer le projet depuis tao-init
  - En tant que developpeur, je veux initialiser AuriPostao via tao-init pour obtenir un squelette standard.
  - Acceptance:
    1. Le projet est genere avec stack tauri-rust + moteur Python.
    2. Les fichiers de baseline docs, scripts et config sont presents.
    3. Aucune trace de placeholder template residuel.

- US-0.2 (Socle) - Wiring Tauri vers API Python locale
  - En tant que developpeur, je veux que Tauri puisse appeler une API Python locale pour separer IHM et moteur.
  - Acceptance:
    1. Lancement local demarre UI et API sans cloud.
    2. Endpoint health repond OK.
    3. L app affiche etat API connectee/deconnectee.

- US-0.3 (Interface) - Ecran bootstrap technique
  - En tant qu utilisateur, je veux un ecran de statut systeme pour verifier que l app est prete.
  - Acceptance:
    1. L ecran montre version app, etat API, chemin DB SQLite.
    2. Un bouton relance le healthcheck et affiche resultat.

- US-0.4 (Qualite) - Baseline checks et gates locaux
  - En tant que developpeur, je veux executer les checks baseline et les hooks locaux pour eviter les commits casses.
  - Acceptance:
    1. scripts test-integrity, test-dependencies, check-secrets, healthcheck passent.
    2. pre-commit lance lint + tests unitaires rapides.
    3. pre-push lance unitaires complets + integration legere.

- US-0.5 (Delivery) - Creer le repository GitHub
  - En tant que product owner, je veux un repository GitHub initialise pour centraliser code, backlog et collaboration.
  - Acceptance:
    1. Repository distant cree et nomme AuriPostao.
    2. Branches de base initialisees (main + convention de branches de travail).
    3. Protection minimale de main definie (PR requise, checks obligatoires quand disponibles).

- US-0.6 (Delivery) - Initialiser le backlog GitHub en issues US
  - En tant que chef de projet, je veux une issue par US avec template d acceptance pour piloter le delivery AI/humain.
  - Acceptance:
    1. Une issue GitHub est creee pour chaque US des EPIC 0 a 9.
    2. Chaque issue suit un template commun (contexte, scope, acceptance, hors-scope, tests).
    3. Les issues sont etiquetees au minimum avec epic et type (socle ou interface).

Scenario test humain EPIC-0:
1. Cloner repo et lancer app.
2. Ouvrir ecran bootstrap.
3. Verifier API OK et DB detectee.
4. Lancer check local; observer statut vert.
5. Verifier le repository GitHub et la presence des issues US creees avec le template standard.

Template issue US (a reutiliser dans GitHub):
Titre: [EPIC-X][US-X.Y][Socle|Interface] <intitule court>

Sections:
1. Contexte
- probleme et valeur utilisateur.

2. Scope
- ce qui est inclus dans cette US.

3. Hors-scope
- ce qui n est pas traite dans cette US.

4. Acceptance Criteria
1. critere testable 1
2. critere testable 2
3. critere testable 3

5. Tests
- test manuel: etapes + resultat attendu
- tests auto: unitaires/integration/e2e concernes

6. Definition of Done
- code merge
- tests verts
- documentation mise a jour

## EPIC-1 - Workflows CRUD et modele metier
Objectif testable:
Un utilisateur peut creer, editer, dupliquer, activer/desactiver et supprimer un workflow depuis l IHM, avec persistance SQLite.

US:
- US-1.1 (Socle) - Modele Workflow et schema SQLite
  - En tant que moteur, je veux stocker workflows, versions et etats pour execution fiable.
  - Acceptance:
    1. Tables workflows, workflow_revisions, workflow_status creees.
    2. Migration initiale versionnee.
    3. Contrainte unicite nom workflow par utilisateur local.

- US-1.2 (Socle) - API CRUD Workflows
  - En tant que frontend, je veux une API CRUD pour manipuler les workflows.
  - Acceptance:
    1. Endpoints create/read/update/delete operationnels.
    2. Validation schema sur champs obligatoires.
    3. Erreurs renvoyees avec code et message exploitables.

- US-1.3 (Interface) - Ecran liste + formulaire workflow
  - En tant qu utilisateur, je veux gerer mes workflows dans une interface simple.
  - Acceptance:
    1. Liste des workflows avec statut actif/inactif.
    2. Formulaire creation/edition.
    3. Action suppression avec confirmation.

- US-1.4 (Interface) - Guard rail canaux
  - En tant qu utilisateur, je veux etre bloque tant qu aucun canal n est configure.
  - Acceptance:
    1. Bouton creer workflow desactive sans canal valide.
    2. Message clair et lien vers configuration canaux.

Scenario test humain EPIC-1:
1. Configurer au moins un canal dummy.
2. Creer un workflow.
3. L editer puis le desactiver puis le supprimer.
4. Recharger app et verifier persistance des changements.

## EPIC-2 - Ingestion texte multi-sources
Objectif testable:
Depuis l IHM, un workflow peut ingerer plusieurs fichiers texte et/ou un dossier avec sous-dossiers, puis afficher un apercu exploitable.

US:
- US-2.1 (Socle) - Connecteur fichiers texte
  - En tant que moteur, je veux lire .txt et .md en lot avec gestion d erreurs.
  - Acceptance:
    1. Lecture multi-fichiers reussie.
    2. Encodage UTF-8 gere + fallback.
    3. Fichiers non texte ignores avec log explicite.

- US-2.2 (Socle) - Ingestion dossier recursive
  - En tant que moteur, je veux ingerer un dossier avec option recursion.
  - Acceptance:
    1. Mode dossier simple et dossier recursive disponibles.
    2. Filtrage extensions texte uniquement.
    3. Limite de taille par fichier configurable.

- US-2.3 (Interface) - Ecran selection sources
  - En tant qu utilisateur, je veux selectionner fichiers/dossiers et voir le resume des sources.
  - Acceptance:
    1. Picker fichiers et picker dossier disponibles.
    2. Toggle inclure sous-dossiers.
    3. Apercu: nb fichiers, taille totale, exemples de contenu tronques.

- US-2.4 (Interface) - Validation pre-run
  - En tant qu utilisateur, je veux valider que la source est correcte avant de lancer.
  - Acceptance:
    1. Message d erreur si aucune source valide.
    2. Alerte si taille depasse seuil.
    3. Bouton tester ingestion avec resultat immediat.

Scenario test humain EPIC-2:
1. Ouvrir un workflow existant.
2. Ajouter 3 fichiers + 1 dossier avec sous-dossiers.
3. Lancer test ingestion.
4. Verifier apercu et erreurs lisibles.

## EPIC-3 - Generation IA et criteres de parole
Objectif testable:
Un workflow genere un Journal prive et un Post public conformes au critere de parole choisi, depuis l IHM.

US:
- US-3.1 (Socle) - Adaptateur IA local
  - En tant que moteur, je veux appeler Ollama/MCP/OpenAI-compatible via une interface unique.
  - Acceptance:
    1. Provider configurable par workflow.
    2. Timeout et erreurs classes transiente/permanente.
    3. Journal et Post produits dans un format standard.

- US-3.2 (Socle) - Criteres de parole
  - En tant que moteur, je veux appliquer modele style et contraintes de longueur.
  - Acceptance:
    1. 5 presets disponibles.
    2. Mode personnalise accepte des regles libres.
    3. Sortie respecte longueur min/max.

- US-3.3 (Interface) - Ecran generation et preview
  - En tant qu utilisateur, je veux choisir le style et previsualiser Journal/Post.
  - Acceptance:
    1. Selecteur de style + personnalise.
    2. Bouton generer et zone preview double (prive/public).
    3. Bouton regenerer avec conservation historique court.

Scenario test humain EPIC-3:
1. Choisir style Professionnel concis.
2. Lancer generation.
3. Verifier Journal prive + Post public.
4. Modifier style et regenerer pour comparer.

## EPIC-4 - Confidentialite, validation humaine et planification
Objectif testable:
Un workflow planifie peut etre controle par filtres de confidentialite et validation humaine, avec abandon automatique au slot suivant.

US:
- US-4.1 (Socle) - Filtrage confidentialite
  - En tant que moteur, je veux bloquer ou marquer les contenus contenant des mots interdits.
  - Acceptance:
    1. Liste interdite globale + surcharge workflow.
    2. Detection avant publication.
    3. Statut run blocked_confidentiality.

- US-4.2 (Socle) - Scheduler riche
  - En tant que moteur, je veux gerer one-shot, quotidien, hebdo, mensuel, multi-creneaux.
  - Acceptance:
    1. Slots calcules correctement selon fuseau local.
    2. Rattrapage au redemarrage disponible.
    3. Aucune execution en doublon sur meme slot.

- US-4.3 (Socle) - Validation humaine et abandon
  - En tant que moteur, je veux attendre validation et abandonner le brouillon si slot suivant atteint.
  - Acceptance:
    1. Etat pending_approval puis abandoned si timeout par slot suivant.
    2. Passage automatique au slot suivant.
    3. Historique des brouillons abandonnes conserve.

- US-4.4 (Interface) - Console planning et moderation
  - En tant qu utilisateur, je veux voir la file des runs et valider/refuser les brouillons.
  - Acceptance:
    1. Vue calendrier simplifiee des slots.
    2. Queue des brouillons en attente avec actions Valider/Refuser.
    3. Badges statut: pending, abandoned, blocked, ready.

Scenario test humain EPIC-4:
1. Configurer un workflow horaire.
2. Activer validation humaine.
3. Ne rien valider jusqu au slot suivant.
4. Verifier que le brouillon precedent passe en abandoned puis que le suivant est traite.

## EPIC-5 - Publication canal 1: Email
Objectif testable:
Depuis l IHM, un workflow publie via SMTP avec statuts et retries visibles.

US:
- US-5.1 (Socle) - Connecteur SMTP
  - Acceptance:
    1. Auth SMTP et TLS geres.
    2. Retry transiente selon politique.
    3. Statut final par tentative stocke.

- US-5.2 (Interface) - Configuration Email + test
  - Acceptance:
    1. Ecran config serveur/email destinataire.
    2. Bouton tester connexion et bouton envoyer test.
    3. Affichage erreurs exploitables.

Scenario test humain EPIC-5:
1. Configurer SMTP.
2. Envoyer message test.
3. Verifier reception + statut success dans IHM.

## EPIC-6 - Publication canal 2: Telegram
Objectif testable:
Depuis l IHM, un workflow publie sur Telegram (canal ou groupe) avec suivi de statut.

US:
- US-6.1 (Socle) - Connecteur Telegram Bot API
  - Acceptance:
    1. Token bot + chat id valides.
    2. Retry transiente applique.
    3. Erreurs permanentes identifiees (auth/chat invalide).

- US-6.2 (Interface) - Configuration Telegram + test
  - Acceptance:
    1. Ecran config token/chat id.
    2. Bouton verifier chat et envoyer message test.
    3. Journal des envois visible.

Scenario test humain EPIC-6:
1. Configurer bot Telegram.
2. Envoyer test.
3. Verifier message dans canal/groupe + statut IHM.

## EPIC-7 - Publication canal 3: Mastodon
Objectif testable:
Depuis l IHM, un workflow publie sur Mastodon avec connectivite instance et statut de publication.

US:
- US-7.1 (Socle) - Connecteur Mastodon REST API
  - Acceptance:
    1. Gestion instance URL + token.
    2. Publication texte operationnelle.
    3. Gestion rate-limit et erreurs auth.

- US-7.2 (Interface) - Configuration Mastodon + test
  - Acceptance:
    1. Ecran config instance + token.
    2. Bouton tester instance et publier test.
    3. Retour id post et statut visible.

Scenario test humain EPIC-7:
1. Configurer compte Mastodon.
2. Publier test.
3. Verifier apparition du post + tracking IHM.

## EPIC-8 - Publication canal 4: Bluesky
Objectif testable:
Depuis l IHM, un workflow publie sur Bluesky avec statut et retry conformes.

US:
- US-8.1 (Socle) - Connecteur Bluesky AT Protocol
  - Acceptance:
    1. Auth compte Bluesky geree.
    2. Publication texte operationnelle.
    3. Retry transiente et erreurs permanentes tracees.

- US-8.2 (Interface) - Configuration Bluesky + test
  - Acceptance:
    1. Ecran config identifiants.
    2. Bouton test connexion et publier test.
    3. Statut et identifiant publication affiches.

Scenario test humain EPIC-8:
1. Configurer compte Bluesky.
2. Publier test.
3. Verifier publication + statut dans l application.

## EPIC-9 - Observabilite, metriques et pilotage
Objectif testable:
L utilisateur peut observer les performances et fiabilite de ses workflows depuis une vue diagnostic locale.

US:
- US-9.1 (Socle) - Instrumentation runs
  - Acceptance:
    1. Durees ingestion/generation/publication mesurees.
    2. Compteurs retries et taux succes/echec calcules.
    3. Donnees persistees en SQLite.

- US-9.2 (Interface) - Tableau de bord diagnostic
  - Acceptance:
    1. Cartes KPI par workflow.
    2. Filtres par canal/periode.
    3. Export CSV local.

Scenario test humain EPIC-9:
1. Executer plusieurs runs.
2. Ouvrir diagnostic.
3. Verifier coherence KPI et export.

## Ordre recommande de livraison
1. EPIC-0
2. EPIC-1
3. EPIC-2
4. EPIC-3
5. EPIC-4
6. EPIC-5 (Email)
7. EPIC-6 (Telegram)
8. EPIC-7 (Mastodon)
9. EPIC-8 (Bluesky)
10. EPIC-9

## Definition of Done globale V1
- Chaque EPIC est demoable en IHM par un humain non developpeur.
- Chaque EPIC a au moins un test manuel scriptable + tests auto associes.
- Aucune EPIC ne livre un backend sans ecran Tauri testable associe.
- Les canaux sont livres incrementalement, un par US, sans big-bang multicanal.
