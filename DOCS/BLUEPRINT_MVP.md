# Blueprint MVP — AuriPostao Quick Win Local

**Statut :** Draft v1.0  
**Date :** 2026-03-28  
**Contexte :** Approche "assemblage de briques" pour honorer la vision produit sans développer d'application from-scratch.

---

## Vision conservée (§1 PRD)

> Générer et programmer/publier automatiquement un contenu court sur des réseaux sociaux décentralisés et/ou par email, à partir de sources personnelles, en utilisant exclusivement un LLM local. Validation humaine ou automatique, avec planification, en plusieurs langues.

---

## Stack choisie

| Brique | Outil | Licence | Rôle |
|--------|-------|---------|------|
| Orchestration + scheduler + pipeline | **n8n** (self-hosted) | Fair-code (source-available, self-host gratuit) | Cœur de tout |
| LLM local | **Ollama** | MIT | Génération IA 100% locale |
| Publication Telegram | n8n — node natif | — | Canal IM |
| Publication Email | n8n — node SMTP natif | — | Canal email |
| Publication Mastodon | n8n — HTTP Request (2 champs) | — | Canal décentralisé |
| Publication Bluesky | n8n — HTTP Request (AT Protocol) | — | Canal décentralisé |
| Validation humaine | n8n — Wait node + webhook | — | Approbation avant envoi |
| Persistance workflow | n8n — SQLite intégré | — | Stockage local |
| Secrets | n8n — Credentials store (AES-256) | — | Tokens API chiffrés |

**Pourquoi n8n seul (sans Postiz, sans Activepieces) ?**  
- Un seul outil à installer, un seul Docker à lancer.
- Nœud Ollama natif — intégration LLM local en drag & drop.
- Couvre tous les canaux V1 soit nativement, soit via HTTP Request trivial.
- SQLite disponible en mode mono-user (pas de PostgreSQL + Redis requis).
- Interface web sur `localhost:5678` — accessible, pas de GUI desktop Tauri nécessaire pour le MVP.

---

## Architecture du pipeline

```
┌──────────────────────────────────────────────────────────────┐
│  TRIGGER                                                      │
│  ScheduleTrigger (cron : quotidien, hebdo, créneaux libres)  │
└──────────────────┬───────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────┐
│  INGESTION                                                    │
│  Read Binary File / Read Files From Folder                   │
│  → Parse texte (.txt, .md) → concaténation sources          │
└──────────────────┬───────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────┐
│  GÉNÉRATION IA (LLM local)                                   │
│  Ollama node                                                 │
│  → Prompt paramétrable (langue, ton/critère de parole)      │
│  → Sortie 1 : Journal (privé, court résumé)                 │
│  → Sortie 2 : Post public (selon critère + canal cible)     │
└──────────────────┬───────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────┐
│  CONTRÔLE — IF node                                          │
│  validation_humaine == true ?                                │
└──────┬───────────────────────────┬───────────────────────────┘
       │ OUI                       │ NON
┌──────▼───────────┐    ┌──────────▼──────────────────────────┐
│  Wait node       │    │  Publication directe                │
│  (webhook token) │    └──────────┬──────────────────────────┘
│  → email/Telegram│               │
│    avec lien     │               │
│    Approuver /   │               │
│    Rejeter       │               │
└──────┬───────────┘               │
       │ approbation reçue         │
       └──────────┬────────────────┘
                  │
┌─────────────────▼────────────────────────────────────────────┐
│  PUBLICATION MULTICANALE (nœuds en parallèle)               │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐ │
│  │ Telegram    │  │ SMTP Email  │  │ HTTP Request         │ │
│  │ (node natif)│  │ (node natif)│  │ Mastodon + Bluesky   │ │
│  └─────────────┘  └─────────────┘  └──────────────────────┘ │
└─────────────────┬────────────────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────────────────┐
│  LOG + IDEMPOTENCE                                           │
│  → Écriture SQLite (via HTTP Request sur l'API n8n ou Code  │
│    node) : run_id, canal, statut, timestamp, hash_contenu   │
│  → Vérification doublon avant envoi (IF node en amont)      │
└──────────────────────────────────────────────────────────────┘
```

---

## Installation — Jour 1 (< 30 min)

### Prérequis
- Docker Desktop (déjà présent sur macOS)
- Ollama (déjà présent ou `brew install ollama`)

### Lancer n8n

```bash
docker volume create n8n_data

docker run -d \
  --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e N8N_RUNNERS_ENABLED=true \
  --restart unless-stopped \
  docker.n8n.io/n8nio/n8n
```

Accès : [http://localhost:5678](http://localhost:5678)

### Lancer Ollama avec un modèle local

```bash
ollama serve            # si pas déjà en service
ollama pull qwen2.5     # ou llama3.2, mistral, etc.
```

### Configurer le credential Ollama dans n8n

Dans n8n → Credentials → New → **Ollama API**  
URL : `http://host.docker.internal:11434`

---

## Configuration des canaux

### Telegram (node natif)
1. Créer un bot via [@BotFather](https://t.me/BotFather) → récupérer le token.
2. n8n → Credentials → New → **Telegram API** → coller le token.
3. Dans le nœud Telegram : action *Send Message*, champ Chat ID = ID de ton canal/groupe.

### Email SMTP (node natif)
1. n8n → Credentials → New → **SMTP** → hôte, port, login, mot de passe.
2. Nœud *Send Email* : From, To, Subject, Body (texte généré).

### Mastodon (HTTP Request, 2 champs)
```
Method : POST
URL    : https://<ton-instance.social>/api/v1/statuses
Headers: Authorization: Bearer <ACCESS_TOKEN>
Body   : { "status": "{{ $json.post_text }}" }
```
Token obtenu dans Settings → Development → New Application sur ton instance.

### Bluesky (HTTP Request, AT Protocol)
```
# Session (à faire une fois ou via credential + refresh)
POST https://bsky.social/xrpc/com.atproto.server.createSession
Body: { "identifier": "handle.bsky.social", "password": "app-password" }
# → récupérer accessJwt

# Publication
POST https://bsky.social/xrpc/com.atproto.repo.createRecord
Headers: Authorization: Bearer <accessJwt>
Body:
{
  "repo": "handle.bsky.social",
  "collection": "app.bsky.feed.post",
  "record": {
    "$type": "app.bsky.feed.post",
    "text": "{{ $json.post_text }}",
    "createdAt": "{{ $now.toISO() }}"
  }
}
```
Utiliser un nœud *Set* pour stocker le JWT en variable de workflow, ou un sub-workflow d'authentification périodique.

---

## Template de prompt Ollama

```
Langue cible : {{ $json.langue }}   // fr | en | zh-TW
Ton souhaité : {{ $json.critere }}  // ex: "Professionnel concis"

Source :
"""
{{ $json.source_text }}
"""

Tâche 1 — Journal (privé) :
Résume en 2-3 phrases ce texte source de façon factuelle.

Tâche 2 — Post public :
À partir du même texte source, rédige un post court pour réseaux sociaux.
Contraintes :
- Maximum 280 caractères (Twitter-compatible)
- Ton : {{ $json.critere }}
- Langue : {{ $json.langue }}
- Aucun mot de la liste interdite : {{ $json.mots_interdits }}

Retourne UNIQUEMENT ce JSON :
{
  "journal": "...",
  "post": "..."
}
```

---

## Scheduler — Exemples de crons n8n

| Fréquence | Expression cron |
|-----------|-----------------|
| Tous les jours à 08:00 | `0 8 * * *` |
| Lundi + Jeudi à 09:00 | `0 9 * * 1,4` |
| Toutes les heures (9h–18h) | `0 9-18 * * 1-5` |
| Immédiat (test manuel) | Trigger manuel |

Le *Schedule Trigger* de n8n supporte le cron natif + timezone.

---

## Validation humaine — Workflow

1. Le nœud **Wait** génère une URL de résumé unique (`$execution.resumeUrl`).
2. Un nœud **Telegram** (ou **SMTP**) envoie ce message :
   ```
   Post généré pour {{ $json.canal }} :
   « {{ $json.post }} »
   
   → Approuver : {{ $execution.resumeUrl }}?action=approve
   → Rejeter   : {{ $execution.resumeUrl }}?action=reject
   ```
3. Le workflow reprend sur clic du lien.
4. Nœud **IF** sur le paramètre `action` : `approve` → publication, `reject` → log + arrêt.
5. **Timeout** : configurer le Wait node avec expiration → nœud d'abandon si pas de réponse.

---

## Idempotence (simple)

Avant publication, ajouter un nœud **Code** (JS, 5 lignes) :

```js
// Calcule une clé d'idempotence
const key = [
  $input.item.json.workflow_id,
  $input.item.json.canal,
  $input.item.json.scheduled_slot,
  require('crypto').createHash('sha256')
    .update($input.item.json.post)
    .digest('hex').slice(0, 16)
].join('|');

return [{ json: { ...$input.item.json, idempotency_key: key } }];
```

Puis un nœud **IF** qui vérifie si cette clé existe déjà dans la base SQLite n8n (via HTTP sur l'API interne ou un fichier JSON local).

---

## Mapping — Vision §1 → Briques

| Exigence Vision | Couverture | Brique |
|-----------------|------------|--------|
| Sources personnelles texte | ✅ natif | n8n Read File / Read Folder |
| LLM local exclusivement | ✅ natif | n8n Ollama node |
| Publication RS décentralisés | ✅ via HTTP | Mastodon + Bluesky HTTP Request |
| Publication email | ✅ natif | n8n SMTP node |
| Publication Telegram | ✅ natif | n8n Telegram node |
| Planification riche | ✅ natif | n8n Schedule Trigger (cron + tz) |
| Validation humaine | ✅ natif | n8n Wait node + webhook |
| Publication automatique | ✅ natif | Exécution directe si validation = off |
| Multi-langue (fr/en/zh-TW) | ✅ prompt | Paramètre dans template Ollama |
| Souveraineté 100% locale | ✅ | n8n sur localhost + Ollama local |
| Critère de parole | ✅ prompt | Paramètre `critere` dans template |
| Retry automatique | ✅ natif | n8n — Error Trigger + retry policy |
| Secrets chiffrés | ✅ natif | n8n Credentials (AES-256 local) |

---

## Gaps acceptés pour ce MVP

| Gap vs PRD original | Impact | Décision |
|---------------------|--------|----------|
| Pas d'interface desktop Tauri | Faible | UI web localhost:5678 suffisante pour MVP |
| Pas de keychain OS natif | Faible | n8n credentials store = AES-256 local, acceptable |
| Idempotence par slot exact | Moyen | Approchée via clé sha256 (Code node 5 lignes) |
| Abandon automatique "prochain slot" | Moyen | Timeout Wait node + log — comportement équivalent |
| Filtrage confidentialité (mots interdits) | Faible | Injecté dans le prompt, pas de filtre pré-génération |

---

## Roadmap quick-wins

| Étape | Contenu | Durée estimée |
|-------|---------|---------------|
| **Jour 1** | n8n + Ollama en local, premier workflow : fichier texte → post généré dans les logs | 2-3h |
| **Jour 2** | Publication réelle sur 1 canal (Telegram ou Mastodon), scheduler quotidien | 1-2h |
| **Jour 3** | Ajout Email + Bluesky, validation humaine via lien Telegram | 2-3h |
| **Semaine 2** | Multi-langue, critère de parole paramétrable, idempotence, retry | 1-2 jours |
| **Semaine 3+** | Polissage, sous-workflow de gestion des canaux, tableau de bord n8n | selon besoin |

---

## Ressources utiles

- n8n self-hosted docs : https://docs.n8n.io/hosting/installation/docker/
- n8n Ollama node : https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.lmollama/
- Mastodon API statuses : https://docs.joinmastodon.org/methods/statuses/
- Bluesky AT Protocol create record : https://docs.bsky.app/docs/api/com-atproto-repo-create-record
- n8n Wait node : https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/
- n8n community workflows (Ollama + social) : https://n8n.io/workflows/?search=ollama
