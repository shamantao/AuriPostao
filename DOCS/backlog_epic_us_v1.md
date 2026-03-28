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

## Principe directeur (workflow pipeline)
Un workflow est l ossature metier et doit contenir les blocs suivants:
- une ou plusieurs sources,
- un ou plusieurs canaux,
- un titre et une description,
- une planification,
- un modele de traitement (quand livre dans les EPIC IA).

Regles transverses obligatoires:
- Toute configuration metier est rattachee a `workflow_id` (jamais etat global d ecran uniquement).
- Toute vue IHM d ingestion, validation, generation ou publication s ouvre dans le contexte d un workflow.
- Toute API de previsualisation ou de test accepte un `workflow_id` ou lit une configuration deja persistee par `workflow_id`.
- Toute US Interface qui manipule des donnees metier doit avoir sa contrepartie de persistance (DB/API) dans le meme EPIC ou en prerequis explicite.

Mode de pilotage:
- Le markdown backlog fait foi comme source de verite.
- Les issues GitHub sont optionnelles et servent de support de suivi, pas de specification principale.
- La reference d architecture et de decoupage reste le PRD sections 2.3 et 2.4.

## Convention de versionnement (SemVer)

Source de verite unique: `src-tauri/Cargo.toml` champ `version`.
La version est gravee dans le binaire a la compilation via `env!("CARGO_PKG_VERSION")`.
Ne pas modifier la version dans les fichiers de config toml — ils ne contiennent plus ce champ.

Règle de bump à appliquer en fin d EPIC, avant commit de cloture:

| Événement                              | Bump        | Exemple         |
|----------------------------------------|-------------|-----------------|
| EPIC complète livrable fonctionnel     | Mineur +1   | 0.1.0 → 0.2.0   |
| Correctif isolé (bug, tech debt)       | Patch +1    | 0.2.0 → 0.2.1   |
| Rupture d interface ou migration DB    | Majeur +1   | 0.2.0 → 1.0.0   |

Checklist de cloture d un EPIC:
1. Bumper `version` dans `src-tauri/Cargo.toml`
2. Ajouter une section `## [x.y.z]` dans `DOCS/CHANGELOG.md`
3. Commiter avec message: `chore: release vX.Y.Z — close EPIC-N`
4. Créer le tag Git: `git tag vX.Y.Z && git push origin vX.Y.Z`
5. Créer la Release GitHub sur ce tag

## EPIC-0 - Foundation projet via tao-init
Statut: ✅ Done

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
Statut: ✅ Done

Objectif testable:
Un utilisateur peut creer, editer, activer/desactiver et supprimer un workflow depuis l IHM, avec persistance SQLite des attributs coeur du pipeline.

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

- US-1.5 (Socle+Interface) - Associer un workflow a un ou plusieurs canaux
  - En tant qu utilisateur, je veux definir les canaux cibles par workflow.
  - Acceptance:
    1. Mapping workflow-canaux persiste en DB.
    2. API lecture/ecriture du mapping par workflow.
    3. IHM permet de voir/editer les canaux d un workflow.

Scenario test humain EPIC-1:
1. Configurer au moins un canal dummy.
2. Creer un workflow.
3. L editer puis le desactiver puis le supprimer.
4. Recharger app et verifier persistance des changements.

## EPIC-2 - Ingestion texte multi-sources
Statut: ✅ Done

Objectif testable:
Depuis l IHM, les sources sont configurees et persistees par workflow, puis testees via un apercu exploitable.

US:
- US-2.0 (Socle) - Modele de sources rattachees au workflow
  - En tant que moteur, je veux persister les sources d un workflow pour executer un pipeline stable.
  - Acceptance:
    1. Schema DB versionne pour lier `workflow_id` a une ou plusieurs sources (fichier/dossier + options).
    2. API CRUD des sources d un workflow.
    3. Suppression d un workflow supprime ses sources associees.

- US-2.1 (Socle) - Connecteur fichiers texte par workflow
  - En tant que moteur, je veux lire .txt et .md en lot depuis les sources configurees d un workflow.
  - Acceptance:
    1. Lecture multi-fichiers reussie.
    2. Encodage UTF-8 gere + fallback.
    3. Fichiers non texte ignores avec log explicite.

- US-2.2 (Socle) - Ingestion dossier recursive par workflow
  - En tant que moteur, je veux ingerer un dossier d un workflow avec option recursion.
  - Acceptance:
    1. Mode dossier simple et dossier recursive disponibles.
    2. Filtrage extensions texte uniquement.
    3. Limite de taille par fichier configurable.

- US-2.3 (Interface) - Ecran selection sources d un workflow
  - En tant qu utilisateur, je veux selectionner fichiers/dossiers pour un workflow et voir le resume persiste.
  - Acceptance:
    1. Picker fichiers et picker dossier disponibles.
    2. Toggle inclure sous-dossiers.
    3. Apercu: nb fichiers, taille totale, exemples de contenu tronques.
    4. Sources rattachees au workflow courant et rechargees au retour sur ce workflow.

- US-2.4 (Interface) - Validation pre-run d un workflow
  - En tant qu utilisateur, je veux valider que les sources de mon workflow sont correctes avant de lancer.
  - Acceptance:
    1. Message d erreur si aucune source valide.
    2. Alerte si taille depasse seuil.
    3. Bouton tester ingestion avec resultat immediat, lie au workflow courant.

Scenario test humain EPIC-2:
1. Ouvrir un workflow existant.
2. Ajouter 3 fichiers + 1 dossier avec sous-dossiers.
3. Quitter puis rouvrir ce workflow et verifier la persistance des sources.
4. Lancer test ingestion.
5. Verifier apercu et erreurs lisibles.

## EPIC-3 - Generation IA et criteres de parole
Statut: ✅ Done

Objectif testable:
Un workflow genere un Journal prive et un Post public conformes au critere de parole choisi, avec configuration persistee par workflow (provider IA, modele, style, contraintes), depuis l IHM.

Objectif PRD (rappel):
- Couvrir explicitement les blocs Workflow "Moteur IA" + "Critere de parole" (PRD sections 2.3 et 3.0 a 3.2).
- Produire deux sorties standardisees: Journal (prive) et Post (public).
- Garantir un test utilisateur de bout en bout dans le contexte d un workflow.

Respect PRD (criteres de conformite pour implementation):
1. Toute config IA est rattachee a `workflow_id` (jamais etat global d ecran seul).
2. Le preview generation lit prioritairement la config persistee du workflow.
3. Les erreurs provider/modeles sont classees (transiente/permanente) et visibles en IHM.
4. Le scenario de test humain verifie persistance apres fermeture/reouverture du workflow.

Cohérence et prerequis:
1. Cohérence amont: EPIC-1/2 fournissent deja l ossature workflow-centric et la persistance par workflow.
2. Cohérence aval: EPIC-4 (planification/controle) et EPIC-5+ (publication) dependent directement des sorties EPIC-3.
3. Risque principal a contenir: ne pas introduire de configuration IA globale hors workflow.

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

## EPIC-4 - Planification et controle de workflow
Statut: 🚧 En cours

Blocs workflow couverts (PRD §2.3) : W4 (Planification — slots + fuseau + rattrapage) + W6 (Regles de controle — confidentialite + validation + retry)

Objectif testable:
Depuis l IHM, un utilisateur peut configurer la planification et les regles de controle d un workflow (type de schedule, horaire, fuseau, rattrapage, validation avant envoi) directement dans le Studio. Le moteur execute les workflows selon cette planification, detecte les mots interdits, gere les brouillons en attente de validation et les abandonne automatiquement au slot suivant si non valides.

Regles de conformite PRD:
- Toute configuration de planification est persistee par workflow_id (jamais etat global).
- La section "Planification" s ouvre dans le contexte du workflow courant dans le Studio.
- Le scenario de test verifie la persistance apres fermeture/reouverture du workflow.
- Tous les libelles de l interface sont en francais.

US:
- ### US-4.1 (Socle) - Modele planification par workflow
  - En tant que moteur, je veux persister la configuration de planification d un workflow pour programmer les executions.
  - Bloc : W4
  - Acceptance:
    1. Tables DB versionnees pour stocker, par workflow_id : le type de schedule (aucun/ponctuel/quotidien/hebdomadaire/mensuel), les creneaux horaires (HH:MM), le fuseau horaire, le flag rattrapage au demarrage, et l activation de la validation humaine avant envoi.
    2. Endpoints API GET et PUT /workflows/{id}/schedule operationnels, avec validation de schema.
    3. La suppression d un workflow supprime sa configuration de planification associee.

- ### US-4.2 (Interface) - Configuration planification dans le Studio
  - En tant qu utilisateur, je veux configurer la planification et les regles de controle de mon workflow directement depuis le Studio, dans le contexte du workflow ouvert.
  - Blocs : W4, W6
  - Prerequis : US-4.1
  - Acceptance:
    1. Une section "Planification" est presente dans l onglet Studio, affichee dans le contexte du workflow courant.
    2. L utilisateur peut selectionner le type de schedule (Aucun, Ponctuel, Quotidien, Hebdomadaire, Mensuel) et saisir l heure du creneau (HH:MM).
    3. Un selecteur de fuseau horaire est disponible (valeur par defaut : fuseau local du systeme).
    4. Une case a cocher "Valider avant envoi" permet d activer la validation humaine pour ce workflow (PRD §3.3).
    5. Une case a cocher "Rattrapage au demarrage" permet d activer le rattrapage de slots manques (PRD §3.3).
    6. La configuration est sauvegardee par workflow_id et rechargee fidelement a la reouverture du workflow.

- ### US-4.3 (Socle) - Filtrage confidentialite
  - En tant que moteur, je veux bloquer les contenus contenant des mots interdits avant toute publication.
  - Bloc : W6
  - Acceptance:
    1. Liste globale de mots interdits configurable via API (GET/PUT /confidentiality/forbidden-words).
    2. Surcharge par workflow possible : ajout et suppression de mots par rapport a la liste globale (GET/PUT /workflows/{id}/forbidden-words).
    3. Detection par correspondance mot entier (word-boundary, insensible a la casse) appliquee avant publication.
    4. Statut du run passe a "bloque_confidentialite" si un mot interdit est detecte ; la liste des mots detectes est conservee dans le brouillon.

- ### US-4.4 (Socle) - Scheduler d execution et abandon automatique
  - En tant que moteur, je veux executer les workflows selon leur planification persistee et gerer l etat des brouillons jusqu a leur abandon automatique.
  - Blocs : W4, W6
  - Prerequis : US-4.1, US-4.3
  - Acceptance:
    1. Les slots sont calcules correctement selon le type de schedule et le fuseau horaire configure (one-shot, daily, weekly, monthly).
    2. Rattrapage au demarrage operationnel si le flag est active et qu un slot a ete manque.
    3. Aucune execution en doublon sur un meme slot (idempotence : workflow_id + slot_iso).
    4. Un brouillon en attente de validation qui n est pas approuve avant l arrivee du slot suivant passe automatiquement au statut "abandonne".
    5. L historique de tous les brouillons (approuves, refuses, abandonnes, bloques) est conserve en DB.

- ### US-4.5 (Interface) - Console moderation et planning
  - En tant qu utilisateur, je veux visualiser les prochains creneaux de mon workflow et valider ou refuser les brouillons en attente depuis une interface dediee.
  - Blocs : W4, W6
  - Prerequis : US-4.2, US-4.4
  - Acceptance:
    1. Un onglet "Planning" est accessible dans l application, affichant les prochains creneaux du workflow selectionne.
    2. La file de brouillons presente le statut en francais : "En attente", "Approuve", "Refuse", "Abandonne", "Bloque (confidentialite)".
    3. Les actions "Approuver" et "Refuser" sont disponibles uniquement pour les brouillons au statut "En attente".
    4. Un bouton "Abandonner les obsoletes" avec indicateur de nombre permet de forcer le passage en "Abandonne" des brouillons dont le slot est depasse.
    5. La selection d un workflow dans le Studio met automatiquement a jour le contexte de l onglet Planning.
    6. Tous les libelles, boutons, statuts et messages de l interface sont en francais.

#### Scenario test humain EPIC-4:
1. Ouvrir un workflow existant dans le Studio.
2. Dans la section "Planification", selectionner "Quotidien", saisir l heure "08:00", choisir le fuseau local, cocher "Valider avant envoi" et "Rattrapage au demarrage". Sauvegarder.
3. Fermer puis rouvrir le workflow : verifier que la planification est rechargee fidelement (persistance).
4. Depuis les parametres de confidentialite, ajouter un mot interdit global.
5. Lancer une generation manuelle depuis le Studio avec un contenu contenant ce mot interdit.
6. Ouvrir l onglet Planning et verifier que le brouillon apparait avec le statut "Bloque (confidentialite)".
7. Lancer une generation sans mot interdit. Verifier que le brouillon apparait avec le statut "En attente".
8. Approuver le brouillon depuis la console : verifier qu il passe au statut "Approuve".
9. Generer un nouveau brouillon sans le valider, puis declencher le slot suivant (ou simuler avec abandon manuel) : verifier que le brouillon precedent passe en "Abandonne".

## EPIC-5 - Publication canal 1: Email
Statut: 🔲 A venir

Blocs workflow couverts (PRD §2.3) : W5 (Canaux — Email)
Prerequis : EPIC-4

Objectif testable:
Depuis l IHM, un workflow peut publier son contenu valide par email via SMTP. La configuration du compte SMTP est persistee et securisee (jamais de credentials en clair). L envoi respecte la politique de retry et d idempotence du PRD. Les statuts d envoi sont visibles par workflow.

Regles de conformite PRD:
- Les identifiants SMTP ne sont jamais stockes en clair (§2.2 : keychain OS, fallback SQLite chiffre).
- La configuration du canal email est associee au workflow (workflow_id, §2.3 W5).
- Toute tentative d envoi cree un Run ID et un Attempt ID (§6.1).
- Retry avec backoff exponentiel 30s / 2min / 10min, 3 tentatives max (§6.2).
- Cle d idempotence : workflow_id + canal + scheduled_slot + hash_contenu (§6.3).
- Tous les libelles de l interface sont en francais.

US:
- ### US-5.1 (Socle) - Stockage securise des comptes SMTP
  - En tant que moteur, je veux persister la configuration SMTP avec secrets proteges pour eviter toute fuite de credentials.
  - Bloc : W5, §2.2, §9
  - Acceptance:
    1. Table DB versionnee pour les comptes SMTP : serveur, port, mode TLS (none/STARTTLS/TLS), identifiant, reference credential (jamais le mot de passe en clair — keychain OS ou SQLite chiffre en fallback).
    2. Endpoints API GET/POST/PUT/DELETE /smtp-accounts operationnels.
    3. Le deverrouillage du coffre est demande a la premiere action necessitant un credential, pas au demarrage de l application (§9.1).
    4. La suppression d un compte SMTP est bloquee s il est associe a un workflow actif.

- ### US-5.2 (Socle) - Connecteur SMTP avec retry et idempotence
  - En tant que moteur, je veux envoyer un email depuis un workflow valide avec fiabilite, retry et deduplication.
  - Bloc : W5, W6 (retry/idempotence)
  - Prerequis : US-5.1
  - Acceptance:
    1. Envoi SMTP operationnel avec authentification et TLS selon la configuration du compte.
    2. Chaque envoi cree un Run ID unique et un Attempt ID par tentative (§6.1).
    3. Les erreurs sont classees transientes (timeout, rate limit, indisponibilite reseau) ou permanentes (auth invalide, adresse destinataire inconnue) (§6.1).
    4. Retry automatique sur erreurs transientes uniquement : backoff 30s / 2min / 10min, 3 tentatives max ; au-dela : statut "echec" + action utilisateur requise (§6.2).
    5. Idempotence : si une publication "succes" existe deja avec la cle workflow_id + canal + scheduled_slot + hash_contenu, le doublon est bloque (§6.3).
    6. Le statut final de chaque tentative est stocke en DB.

- ### US-5.3 (Interface) - Configuration compte SMTP et association workflow
  - En tant qu utilisateur, je veux configurer mon compte SMTP, le tester et l associer a un workflow depuis le Studio.
  - Bloc : W5
  - Prerequis : US-5.1
  - Acceptance:
    1. Ecran de configuration du compte SMTP : serveur, port, mode TLS, identifiant, mot de passe (stocke dans le coffre, non affiche apres saisie initiale).
    2. Bouton "Tester la connexion" avec retour immediat : succes ou message d erreur exploitable.
    3. Dans le contexte d un workflow ouvert dans le Studio, l utilisateur peut associer un compte SMTP et saisir un ou plusieurs emails destinataires (PRD §3.3 : "Envoyer copie par email ? Un ou plusieurs possible").
    4. La configuration email du workflow (compte associe + destinataires) est sauvegardee par workflow_id et rechargee fidelement a la reouverture du workflow.

- ### US-5.4 (Interface) - Suivi des envois et republication
  - En tant qu utilisateur, je veux suivre l historique des envois de mon workflow et republier si necessaire.
  - Bloc : W5
  - Prerequis : US-5.2, US-5.3
  - Acceptance:
    1. Historique des tentatives d envoi visible par workflow : date, destinataires, statut ("Succes" / "Erreur temporaire" / "Echec" / "En cours").
    2. Le detail de l erreur est affiche en clair pour les echecs permanents.
    3. Bouton "Republier" disponible pour les runs en echec ; il genere une nouvelle cle d idempotence (republication volontaire, §6.3).
    4. Tous les libelles, statuts et messages sont en francais.

#### Scenario test humain EPIC-5:
1. Configurer un compte SMTP valide. Cliquer "Tester la connexion" : verifier le retour succes.
2. Ouvrir un workflow dans le Studio. Associer le compte SMTP et saisir deux adresses email destinataires. Sauvegarder.
3. Fermer puis rouvrir le workflow : verifier que les destinataires et le compte SMTP sont recharges fidelement (persistance).
4. Approuver un brouillon depuis la console Planning. Verifier que l email est envoye et apparait dans l historique avec le statut "Succes".
5. Simuler une erreur transiente (serveur indisponible) : verifier que le retry est tente et que les Attempt IDs sont incrementes en DB.
6. Tenter l envoi d un doublon (meme slot, meme contenu) : verifier qu il est bloque par l idempotence.

## EPIC-6 - Publication canal 2: Telegram
Statut: 🔲 A venir

Blocs workflow couverts (PRD §2.3) : W5 (Canaux — Telegram)
Prerequis : EPIC-4

Objectif testable:
Depuis l IHM, un workflow peut publier son contenu valide sur un canal ou groupe Telegram via Bot API. La configuration du bot (token + chat_id) est persistee et securisee. L envoi respecte la politique de retry et d idempotence du PRD. Les statuts de publication sont visibles par workflow.

Regles de conformite PRD:
- Le token bot Telegram n est jamais stocke en clair (§2.2 : keychain OS, fallback SQLite chiffre).
- La configuration du canal Telegram est associee au workflow (workflow_id, §2.3 W5).
- Toute tentative de publication cree un Run ID et un Attempt ID (§6.1).
- Retry avec backoff exponentiel 30s / 2min / 10min, 3 tentatives max (§6.2).
- Cle d idempotence : workflow_id + canal + scheduled_slot + hash_contenu (§6.3).
- Tous les libelles de l interface sont en francais.

US:
- ### US-6.1 (Socle) - Stockage securise des comptes Telegram
  - En tant que moteur, je veux persister la configuration bot Telegram avec secrets proteges.
  - Bloc : W5, §2.2
  - Acceptance:
    1. Table DB versionnee pour les comptes Telegram : nom du bot, token reference (jamais en clair — keychain OS ou SQLite chiffre), chat_id cible.
    2. Endpoints API GET/POST/PUT/DELETE /telegram-accounts operationnels.
    3. Le deverrouillage du coffre est demande a la premiere action necessitant un credential, pas au demarrage (§9.1).
    4. La suppression d un compte Telegram est bloquee s il est associe a un workflow actif.

- ### US-6.2 (Socle) - Connecteur Telegram Bot API avec retry et idempotence
  - En tant que moteur, je veux publier un message Telegram depuis un workflow valide avec fiabilite et deduplication.
  - Bloc : W5, W6 (retry/idempotence)
  - Prerequis : US-6.1
  - Acceptance:
    1. Publication texte operationnelle via Telegram Bot API (sendMessage) vers un canal ou un groupe.
    2. Chaque publication cree un Run ID unique et un Attempt ID par tentative (§6.1).
    3. Les erreurs sont classees transientes (timeout, rate limit) ou permanentes (token invalide, chat introuvable, bot non administrateur) (§6.1).
    4. Retry automatique sur erreurs transientes : backoff 30s / 2min / 10min, 3 tentatives max ; au-dela : statut "echec" (§6.2).
    5. Idempotence : doublon bloque si une publication "succes" existe deja avec la cle workflow_id + canal + scheduled_slot + hash_contenu (§6.3).
    6. Le statut final et le message_id Telegram retournes par l API sont stockes en DB.

- ### US-6.3 (Interface) - Configuration compte Telegram et association workflow
  - En tant qu utilisateur, je veux configurer mon bot Telegram, verifier le canal cible et l associer a un workflow depuis le Studio.
  - Bloc : W5
  - Prerequis : US-6.1
  - Acceptance:
    1. Ecran de configuration : nom du bot, token (stocke dans le coffre, masque apres saisie), chat_id.
    2. Bouton "Verifier le canal" : envoie un message de test sur le canal et confirme la reception ou affiche l erreur en clair.
    3. Dans le contexte d un workflow ouvert dans le Studio, l utilisateur peut associer un compte Telegram au workflow. La configuration est sauvegardee par workflow_id.
    4. Rechargement fidele de la configuration a la reouverture du workflow (persistance).

- ### US-6.4 (Interface) - Suivi des publications Telegram et republication
  - En tant qu utilisateur, je veux suivre l historique des publications Telegram de mon workflow et republier si necessaire.
  - Bloc : W5
  - Prerequis : US-6.2, US-6.3
  - Acceptance:
    1. Historique des tentatives de publication visible par workflow : date, chat_id, statut ("Succes" / "Erreur temporaire" / "Echec"), message_id Telegram si disponible.
    2. Detail de l erreur affiche pour les echecs permanents.
    3. Bouton "Republier" disponible pour les runs en echec ; genere une nouvelle cle d idempotence (§6.3).
    4. Tous les libelles et statuts sont en francais.

#### Scenario test humain EPIC-6:
1. Configurer un compte bot Telegram (token + chat_id). Cliquer "Verifier le canal" : verifier le message de test recu sur le canal.
2. Ouvrir un workflow dans le Studio. Associer le compte Telegram. Sauvegarder. Fermer puis rouvrir : verifier la persistance.
3. Approuver un brouillon depuis la console Planning. Verifier que le message apparait sur le canal Telegram et dans l historique avec statut "Succes" et le message_id.
4. Simuler une erreur transiente : verifier que le retry est tente avec les Attempt IDs incrementes en DB.
5. Tenter l envoi d un doublon (meme slot, meme contenu) : verifier qu il est bloque par l idempotence.

## EPIC-7 - Publication canal 3: Mastodon
Statut: 🔲 A specifier

Blocs workflow couverts (PRD §2.3) : W5 (Canaux — Mastodon)
Prerequis : EPIC-9

Objectif testable:
Depuis l IHM, un workflow peut publier son contenu sur Mastodon via API REST. La configuration du compte (instance + token) est securisee, la publication respecte la politique de retry et d idempotence, et les statuts de publication sont visibles par workflow.

(US et scenario a specifier lors de la planification de cet EPIC)

## EPIC-8 - Publication canal 4: Bluesky
Statut: 🔲 A specifier

Blocs workflow couverts (PRD §2.3) : W5 (Canaux — Bluesky)
Prerequis : EPIC-9

Objectif testable:
Depuis l IHM, un workflow peut publier son contenu sur Bluesky via AT Protocol. La configuration du compte (identifiants) est securisee, la publication respecte la politique de retry et d idempotence, et les statuts de publication sont visibles par workflow.

(US et scenario a specifier lors de la planification de cet EPIC)

## EPIC-9 - Observabilite, metriques et pilotage
Statut: 🔲 A venir

Blocs workflow couverts (PRD §2.3) : transverse (W1 a W5)
Note de pilotage : EPIC-9 est livre apres EPIC-6 et avant EPIC-7/EPIC-8. L observabilite couvre tous les canaux deja livres au moment de son implementation.

Objectif testable:
Depuis l IHM, un utilisateur peut observer les performances et la fiabilite de ses workflows via une vue diagnostic locale : durees de chaque etape du pipeline, taux de succes/echec par canal, compteurs de retries. Toutes les donnees sont stockees localement en SQLite et exportables en CSV. Aucune donnee ne quitte la machine locale.

Regles de conformite PRD:
- Les metriques sont collectees par run, sans agentification cloud (§7 : local-first, §1 : souverainete).
- Les donnees sont stockees en SQLite et visualisables dans une vue de diagnostic simple (§7).
- L instrumentation ne doit pas bloquer le pipeline de publication (collecter sans ralentir).
- Tous les libelles de l interface sont en francais.

US:
- ### US-9.1 (Socle) - Instrumentation et persistance des metriques de run
  - En tant que moteur, je veux mesurer et persister les metriques de chaque etape d un run de workflow.
  - Acceptance:
    1. Pour chaque run de workflow, les donnees suivantes sont stockees en DB (PRD §7) :
       - Duree d ingestion des sources.
       - Duree de generation IA (prompt -> Journal + Post).
       - Duree de publication par canal (avec Run ID et Attempt ID existants).
       - Nombre de retries par canal.
       - Statut final par canal (succes / echec transiente / echec permanent).
       - Consommation memoire de l application (hors LLM) relevee sur les ecrans critiques.
    2. Schema DB versionne pour la table runs_metrics, rattachee a workflow_id et run_id.
    3. Endpoints API GET /workflows/{id}/metrics et GET /runs/{run_id}/metrics operationnels.
    4. Une erreur de collecte de metrique est loggee mais ne bloque pas le pipeline.

- ### US-9.2 (Interface) - Tableau de bord diagnostic par workflow
  - En tant qu utilisateur, je veux visualiser les metriques de mes workflows dans une vue diagnostic locale simple.
  - Prerequis : US-9.1
  - Acceptance:
    1. Section ou onglet "Diagnostic" accessible depuis l application.
    2. Cartes KPI par workflow : nombre de runs sur la periode, taux de succes global, duree moyenne de generation IA, nombre total de retries.
    3. Filtres disponibles : par canal et par periode (7 jours / 30 jours / tout).
    4. Detail par run au clic : liste des etapes avec durees, statuts et messages d erreur.
    5. Bouton "Exporter en CSV" : genere un fichier local avec toutes les metriques du workflow sur la periode selectionnee.
    6. Tous les libelles, filtres, statuts et actions sont en francais.

#### Scenario test humain EPIC-9:
1. Executer au moins trois runs sur un workflow configure avec canal Email et canal Telegram (succes et echecs intentionnels).
2. Ouvrir la section "Diagnostic". Verifier que les metriques de chaque run sont presentes et coherentes (durees, statuts, retries).
3. Appliquer le filtre "7 jours" : verifier que les runs plus anciens sont exclus.
4. Filtrer par canal Email : verifier que seules les tentatives email apparaissent.
5. Cliquer sur un run : verifier le detail etape par etape avec durees et statuts.
6. Exporter en CSV : ouvrir le fichier et verifier la presence de toutes les colonnes (workflow_id, run_id, etape, duree, statut, erreur, canal).

## Ordre recommande de livraison
1. EPIC-0
2. EPIC-1
3. EPIC-2
4. EPIC-3
5. EPIC-4
6. EPIC-5 (Email)
7. EPIC-6 (Telegram)
8. EPIC-9 (Observabilite — avant les canaux restants)
9. EPIC-7 (Mastodon)
10. EPIC-8 (Bluesky)

## Definition of Done globale V1
- Chaque EPIC est demoable en IHM par un humain non developpeur.
- Chaque EPIC a au moins un test manuel scriptable + tests auto associes.
- Aucune EPIC ne livre un backend sans ecran Tauri testable associe.
- Les canaux sont livres incrementalement, un par US, sans big-bang multicanal.
