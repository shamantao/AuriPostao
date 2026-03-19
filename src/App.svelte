<!-- App.svelte — Ecran bootstrap technique (US-0.3) -->
<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import { onMount } from "svelte";

  type ApiHealthStatus = {
    api_state: "connectee" | "deconnectee";
    api_url: string;
    service?: string | null;
    version?: string | null;
    time_utc?: string | null;
    message: string;
  };

  type BootstrapStatus = {
    app_version: string;
    db_path: string;
    db_exists: boolean;
    mode: string;
  };

  type Workflow = {
    id: number;
    local_user: string;
    name: string;
    description: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
    channels: string[];
  };

  type WorkflowForm = {
    name: string;
    description: string;
    is_active: boolean;
    channels: string[];
  };

  type ChannelStatus = {
    has_valid_channel: boolean;
    valid_channels: string[];
    config_url: string;
  };

  type IngestionAcceptedFile = {
    path: string;
    size_bytes: number;
    encoding: string;
    preview: string;
  };

  type IngestionMessage = {
    path: string;
    reason: string;
  };

  type IngestionPreview = {
    accepted_files: IngestionAcceptedFile[];
    ignored_files: IngestionMessage[];
    errors: IngestionMessage[];
    summary: {
      accepted: number;
      ignored: number;
      errors: number;
      total_candidates: number;
      total_size_bytes: number;
    };
  };

  type WorkflowSourcesConfig = {
    file_paths: string[];
    directory_path: string | null;
    recursive: boolean;
    max_file_size_bytes: number;
  };

  let health: ApiHealthStatus | null = null;
  let bootstrap: BootstrapStatus | null = null;
  let workflows: Workflow[] = [];
  let workflowsLoading = false;
  let workflowsError = "";
  let workflowsInfo = "";
  let editingId: number | null = null;
  let pendingDeleteId: number | null = null;
  let channelStatus: ChannelStatus | null = null;
  let channelsLoading = false;
  let channelsError = "";
  let sourceWorkflowId: number | null = null;
  let sourceFiles: string[] = [];
  let sourceDirectory = "";
  let includeSubdirs = true;
  let maxFileSizeBytes = 1_000_000;
  let ingestionLoading = false;
  let ingestionError = "";
  let ingestionInfo = "";
  let ingestionWarning = "";
  let ingestionPreview: IngestionPreview | null = null;
  let form: WorkflowForm = {
    name: "",
    description: "",
    is_active: true,
    channels: [],
  };
  let loading = false;

  function invokeError(e: unknown): string {
    if (typeof e === "string") {
      return e;
    }
    return `Erreur Tauri: ${String(e)}`;
  }

  function formatBytes(value: number): string {
    if (value < 1024) {
      return `${value} B`;
    }
    if (value < 1024 * 1024) {
      return `${(value / 1024).toFixed(1)} KB`;
    }
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  }

  function dedupePaths(paths: string[]): string[] {
    return [...new Set(paths)];
  }

  function selectedWorkflowLabel(): string {
    if (sourceWorkflowId == null) {
      return "(aucun workflow selectionne)";
    }
    const wf = workflows.find((w) => w.id === sourceWorkflowId);
    return wf ? `${wf.name} (#${wf.id})` : `#${sourceWorkflowId}`;
  }

  function resetForm() {
    editingId = null;
    form = {
      name: "",
      description: "",
      is_active: true,
      channels: [],
    };
  }

  async function loadWorkflows() {
    workflowsLoading = true;
    workflowsError = "";
    workflowsInfo = "";
    try {
      workflows = await invoke<Workflow[]>("workflows_list");
    } catch (e) {
      workflowsError = invokeError(e);
    } finally {
      workflowsLoading = false;
    }
  }

  async function loadChannelStatus() {
    channelsLoading = true;
    channelsError = "";
    try {
      channelStatus = await invoke<ChannelStatus>("channels_status");
    } catch (e) {
      channelsError = invokeError(e);
      channelStatus = null;
    } finally {
      channelsLoading = false;
    }
  }

  async function setDummyChannel(enabled: boolean) {
    channelsError = "";
    try {
      channelStatus = await invoke<ChannelStatus>("channels_set_dummy", {
        payload: { enabled },
      });
      if (enabled) {
        workflowsInfo = "Canal dummy configure: creation workflow debloquee.";
      } else {
        workflowsInfo = "Canal dummy desactive.";
      }
    } catch (e) {
      channelsError = invokeError(e);
    }
  }

  async function runChecks() {
    loading = true;
    try {
      [health, bootstrap] = await Promise.all([
        invoke<ApiHealthStatus>("healthcheck"),
        invoke<BootstrapStatus>("bootstrap_status"),
      ]);
    } catch (e) {
      health = {
        api_state: "deconnectee",
        api_url: "http://127.0.0.1:8787",
        message: `Erreur Tauri: ${String(e)}`,
      };
    } finally {
      loading = false;
    }
    await Promise.all([loadWorkflows(), loadChannelStatus()]);
    if (sourceWorkflowId != null && !workflows.some((w) => w.id === sourceWorkflowId)) {
      clearAllSources();
      sourceWorkflowId = null;
    }
  }

  async function selectWorkflowForSources(workflowId: number) {
    sourceWorkflowId = workflowId;
    ingestionPreview = null;
    ingestionError = "";
    ingestionWarning = "";
    ingestionInfo = "";

    try {
      const cfg = await invoke<WorkflowSourcesConfig>("workflow_sources_get", {
        workflowId,
      });
      sourceFiles = cfg.file_paths ?? [];
      sourceDirectory = cfg.directory_path ?? "";
      includeSubdirs = cfg.recursive;
      maxFileSizeBytes = cfg.max_file_size_bytes;
      ingestionInfo = "Sources du workflow chargees.";
    } catch (e) {
      ingestionError = invokeError(e);
      sourceFiles = [];
      sourceDirectory = "";
      includeSubdirs = true;
      maxFileSizeBytes = 1_000_000;
    }
  }

  async function saveWorkflowSources() {
    if (sourceWorkflowId == null) {
      ingestionError = "Selectionne un workflow pour rattacher les sources.";
      return;
    }
    ingestionError = "";
    try {
      const cfg = await invoke<WorkflowSourcesConfig>("workflow_sources_set", {
        workflowId: sourceWorkflowId,
        payload: {
          file_paths: sourceFiles,
          directory_path: sourceDirectory || null,
          recursive: includeSubdirs,
          max_file_size_bytes: maxFileSizeBytes,
        },
      });
      sourceFiles = cfg.file_paths ?? [];
      sourceDirectory = cfg.directory_path ?? "";
      includeSubdirs = cfg.recursive;
      maxFileSizeBytes = cfg.max_file_size_bytes;
      ingestionInfo = "Sources enregistrees pour ce workflow.";
    } catch (e) {
      ingestionError = invokeError(e);
    }
  }

  async function submitWorkflow() {
    workflowsError = "";
    workflowsInfo = "";
    if (!form.name.trim()) {
      workflowsError = "validation_error: name is required";
      return;
    }

    if (form.channels.length === 0) {
      workflowsError = "validation_error: selectionner au moins un canal";
      return;
    }

    if (editingId == null && !channelStatus?.has_valid_channel) {
      workflowsError = "no_valid_channel: configure au moins un canal valide avant de creer un workflow";
      return;
    }

    try {
      if (editingId == null) {
        await invoke<Workflow>("workflows_create", {
          payload: {
            name: form.name,
            description: form.description,
            is_active: form.is_active,
            channels: form.channels,
          },
        });
      } else {
        await invoke<Workflow>("workflows_update", {
          workflowId: editingId,
          payload: {
            name: form.name,
            description: form.description,
            is_active: form.is_active,
          },
        });
        await invoke<string[]>("workflow_channels_set", {
          workflowId: editingId,
          channels: form.channels,
        });
      }

      workflowsInfo = editingId == null ? "Workflow cree." : "Workflow mis a jour.";
      resetForm();
      await loadWorkflows();
    } catch (e) {
      workflowsError = invokeError(e);
    }
  }

  function startEdit(w: Workflow) {
    editingId = w.id;
    form = {
      name: w.name,
      description: w.description,
      is_active: w.is_active,
      channels: [...w.channels],
    };
  }

  async function removeWorkflow(w: Workflow) {
    workflowsError = "";
    workflowsInfo = "";
    try {
      await invoke<boolean>("workflows_delete", { workflowId: w.id });
      workflowsInfo = "Workflow supprime.";
      pendingDeleteId = null;
      if (editingId === w.id) {
        resetForm();
      }
      await loadWorkflows();
    } catch (e) {
      workflowsError = invokeError(e);
    }
  }

  async function pickFiles() {
    ingestionError = "";
    ingestionWarning = "";
    try {
      const picked = await invoke<string[]>("pick_text_files");
      if (picked.length === 0) {
        ingestionInfo = "Aucun fichier selectionne.";
        return;
      }
      sourceFiles = dedupePaths([...sourceFiles, ...picked]);
      ingestionInfo = `${sourceFiles.length} fichier(s) selectionne(s).`;
    } catch (e) {
      ingestionError = invokeError(e);
    }
  }

  async function pickDirectory() {
    ingestionError = "";
    ingestionWarning = "";
    try {
      const picked = await invoke<string | null>("pick_directory");
      sourceDirectory = picked ?? "";
      if (sourceDirectory) {
        ingestionInfo = "Dossier selectionne.";
      }
    } catch (e) {
      ingestionError = invokeError(e);
    }
  }

  function removeSourceFile(path: string) {
    ingestionWarning = "";
    sourceFiles = sourceFiles.filter((p) => p !== path);
    if (sourceFiles.length === 0) {
      ingestionInfo = "Aucun fichier selectionne.";
    } else {
      ingestionInfo = `${sourceFiles.length} fichier(s) selectionne(s).`;
    }
  }

  function clearSourceDirectory() {
    ingestionWarning = "";
    sourceDirectory = "";
  }

  function clearAllSources() {
    sourceFiles = [];
    sourceDirectory = "";
    ingestionPreview = null;
    ingestionWarning = "";
    ingestionInfo = "Sources reinitialisees.";
  }

  async function runIngestionPreview() {
    ingestionError = "";
    ingestionInfo = "";
    ingestionWarning = "";
    ingestionPreview = null;

    if (sourceWorkflowId == null) {
      ingestionError = "Selectionne d abord un workflow pour le test d ingestion.";
      return;
    }

    if (sourceFiles.length === 0 && !sourceDirectory) {
      ingestionError = "Aucune source selectionnee.";
      return;
    }

    ingestionLoading = true;
    try {
      await invoke<WorkflowSourcesConfig>("workflow_sources_set", {
        workflowId: sourceWorkflowId,
        payload: {
          file_paths: sourceFiles,
          directory_path: sourceDirectory || null,
          recursive: includeSubdirs,
          max_file_size_bytes: maxFileSizeBytes,
        },
      });

      ingestionPreview = await invoke<IngestionPreview>("workflow_ingestion_preview", {
        workflowId: sourceWorkflowId,
      });

      const tooLargeFiles = ingestionPreview.ignored_files.filter(
        (item) => item.reason === "file_too_large"
      );
      if (tooLargeFiles.length > 0) {
        ingestionWarning =
          `${tooLargeFiles.length} fichier(s) depassent le seuil de taille ` +
          `(${formatBytes(maxFileSizeBytes)} max par fichier).`;
      }

      if (ingestionPreview.summary.accepted === 0) {
        ingestionError =
          "Aucune source valide detectee. Ajoute au moins un fichier texte (.txt/.md) lisible sous le seuil de taille.";
      } else {
        ingestionInfo = "Apercu ingestion genere pour le workflow selectionne.";
      }
    } catch (e) {
      ingestionError = invokeError(e);
    } finally {
      ingestionLoading = false;
    }
  }

  onMount(() => {
    void runChecks();
  });
</script>

<main>
  <h1>AuriPostao <span class="version">{bootstrap?.app_version ?? "…"}</span></h1>
  <p class="mode">Mode: {bootstrap?.mode ?? "…"}</p>

  <section>
    <h2>Etat API</h2>
    <p>
      Statut:
      <strong class={health?.api_state === "connectee" ? "ok" : "ko"}>
        {health?.api_state ?? "inconnu"}
      </strong>
    </p>
    <p>Endpoint: {health?.api_url ?? "http://127.0.0.1:8787"}</p>
    <p>Message: {health?.message ?? "—"}</p>
    {#if health?.service}<p>Service: {health.service}</p>{/if}
    {#if health?.version}<p>Version API: {health.version}</p>{/if}
    {#if health?.time_utc}<p>Horodatage: {health.time_utc}</p>{/if}
  </section>

  <section>
    <h2>Base de donnees</h2>
    <p>
      Chemin: <code>{bootstrap?.db_path ?? "…"}</code>
    </p>
    <p>
      Etat:
      <strong class={bootstrap?.db_exists ? "ok" : "warn"}>
        {bootstrap == null ? "…" : bootstrap.db_exists ? "detectee" : "absente (sera creee au premier run)"}
      </strong>
    </p>
  </section>

  <section>
    <h2>Workflows</h2>

    {#if !channelStatus?.has_valid_channel}
      <p class="warn">
        Aucun canal valide configure. La creation de workflow est bloquee.
        <a href={channelStatus?.config_url ?? "#channels-config"}>Configurer les canaux</a>
      </p>
    {/if}

    <form class="workflow-form" on:submit|preventDefault={submitWorkflow}>
      <label>
        Nom (obligatoire)
        <input bind:value={form.name} placeholder="Nom du workflow" maxlength="120" required />
      </label>

      <label>
        Description
        <textarea bind:value={form.description} rows="3" placeholder="Description libre" />
      </label>

      <label class="checkbox">
        <input type="checkbox" bind:checked={form.is_active} />
        Workflow actif
      </label>

      <label>
        Canaux cibles (au moins un requis)
        {#if channelStatus?.valid_channels?.length}
          <div class="channel-checkboxes">
            {#each channelStatus.valid_channels as ch}
              <label class="checkbox">
                <input type="checkbox" bind:group={form.channels} value={ch} />
                {ch}
              </label>
            {/each}
          </div>
        {:else}
          <span class="warn">Aucun canal valide disponible</span>
        {/if}
      </label>

      <div class="actions">
        <button type="submit" disabled={editingId == null && !channelStatus?.has_valid_channel}>
          {editingId == null ? "Creer" : "Enregistrer"}
        </button>
        {#if editingId != null}
          <button type="button" class="secondary" on:click={resetForm}>Annuler edition</button>
        {/if}
      </div>
    </form>

    {#if workflowsError}<p class="ko">{workflowsError}</p>{/if}
    {#if workflowsInfo}<p class="ok">{workflowsInfo}</p>{/if}

    {#if workflowsLoading}
      <p>Chargement des workflows…</p>
    {:else if workflows.length === 0}
      <p>Aucun workflow pour l instant.</p>
    {:else}
      <ul class="workflow-list">
        {#each workflows as w}
          <li>
            <div>
              <p class="wf-name">{w.name}</p>
              <p>{w.description || "(sans description)"}</p>
              <p>
                Statut:
                <strong class={w.is_active ? "ok" : "warn"}>{w.is_active ? "actif" : "inactif"}</strong>
              </p>
              <p class="wf-channels">
                Canaux: {w.channels?.length ? w.channels.join(", ") : "(aucun)"}
              </p>
            </div>
            <div class="actions">
              <button type="button" class="secondary" on:click={() => startEdit(w)}>Editer</button>
              <button type="button" class="secondary" on:click={() => selectWorkflowForSources(w.id)}>
                Sources
              </button>
              {#if pendingDeleteId === w.id}
                <button type="button" class="danger" on:click={() => removeWorkflow(w)}>Confirmer</button>
                <button type="button" class="secondary" on:click={() => (pendingDeleteId = null)}>Annuler</button>
              {:else}
                <button type="button" class="danger" on:click={() => (pendingDeleteId = w.id)}>Supprimer</button>
              {/if}
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  </section>

  <section id="channels-config">
    <h2>Configuration canaux</h2>
    <p>Canaux valides: {channelStatus?.valid_channels?.join(", ") || "aucun"}</p>
    {#if channelsLoading}
      <p>Verification canaux…</p>
    {:else}
      <div class="actions">
        <button type="button" on:click={() => setDummyChannel(true)}>Activer canal dummy</button>
        <button type="button" class="secondary" on:click={() => setDummyChannel(false)}>
          Desactiver canal dummy
        </button>
      </div>
    {/if}
    {#if channelsError}<p class="ko">{channelsError}</p>{/if}
  </section>

  <section id="sources-config">
    <h2>Selection des sources</h2>
    <p>Workflow cible: <strong>{selectedWorkflowLabel()}</strong></p>
    <div class="actions">
      <button type="button" on:click={pickFiles}>Picker fichiers texte</button>
      <button type="button" class="secondary" on:click={pickDirectory}>Picker dossier</button>
      <button type="button" class="secondary" on:click={saveWorkflowSources} disabled={sourceWorkflowId == null}>
        Enregistrer sources
      </button>
      <button type="button" class="secondary" on:click={clearAllSources}>Reinitialiser sources</button>
    </div>

    <p>Fichiers selectionnes: {sourceFiles.length}</p>
    {#if sourceFiles.length > 0}
      <ul class="source-list">
        {#each sourceFiles as filePath}
          <li class="source-row">
            <span>{filePath}</span>
            <button type="button" class="secondary mini" on:click={() => removeSourceFile(filePath)}>
              Retirer
            </button>
          </li>
        {/each}
      </ul>
    {/if}

    <p>Dossier selectionne: {sourceDirectory || "(aucun)"}</p>
    {#if sourceDirectory}
      <button type="button" class="secondary mini" on:click={clearSourceDirectory}>Retirer dossier</button>
    {/if}

    <label class="checkbox">
      <input type="checkbox" bind:checked={includeSubdirs} />
      Inclure sous-dossiers (mode recursif)
    </label>

    <label>
      Limite taille par fichier (bytes)
      <input type="number" min="1" step="1" bind:value={maxFileSizeBytes} />
    </label>

    <div class="actions">
      <button type="button" on:click={runIngestionPreview} disabled={ingestionLoading}>
        {#if ingestionLoading}Ingestion...{:else}Tester ingestion{/if}
      </button>
    </div>

    {#if ingestionError}<p class="ko">{ingestionError}</p>{/if}
    {#if ingestionWarning}<p class="warn">{ingestionWarning}</p>{/if}
    {#if ingestionInfo}<p class="ok">{ingestionInfo}</p>{/if}

    {#if ingestionPreview}
      <div class="preview-box">
        <p>
          Resume: {ingestionPreview.summary.accepted} accepte(s), {ingestionPreview.summary.ignored} ignore(s),
          {ingestionPreview.summary.errors} erreur(s), {ingestionPreview.summary.total_candidates} candidat(s),
          taille totale {formatBytes(ingestionPreview.summary.total_size_bytes)}
        </p>

        {#if ingestionPreview.accepted_files.length > 0}
          <h3>Exemples de contenu</h3>
          <ul class="source-list">
            {#each ingestionPreview.accepted_files.slice(0, 5) as file}
              <li>
                <p><strong>{file.path}</strong> ({formatBytes(file.size_bytes)}, {file.encoding})</p>
                <pre>{file.preview}</pre>
              </li>
            {/each}
          </ul>
        {/if}

        {#if ingestionPreview.ignored_files.length > 0}
          <h3>Fichiers ignores</h3>
          <ul class="source-list">
            {#each ingestionPreview.ignored_files as item}
              <li>{item.path} - {item.reason}</li>
            {/each}
          </ul>
        {/if}

        {#if ingestionPreview.errors.length > 0}
          <h3>Erreurs</h3>
          <ul class="source-list">
            {#each ingestionPreview.errors as item}
              <li>{item.path} - {item.reason}</li>
            {/each}
          </ul>
        {/if}
      </div>
    {/if}
  </section>

  <button on:click={runChecks} disabled={loading}>
    {#if loading}Verification en cours…{:else}Relancer le healthcheck{/if}
  </button>
</main>

<style>
  main {
    font-family: system-ui, sans-serif;
    max-width: 720px;
    margin: 2rem auto;
    padding: 1.5rem;
  }
  h1 {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
  }
  .version {
    font-size: 0.9rem;
    font-weight: normal;
    color: #666;
  }
  .mode {
    color: #555;
    font-size: 0.85rem;
    margin-top: -0.75rem;
  }
  section {
    margin: 1.5rem 0;
    padding: 1rem;
    border: 1px solid #ddd;
    border-radius: 6px;
  }
  .workflow-form {
    display: grid;
    gap: 0.75rem;
  }
  .workflow-form label {
    display: grid;
    gap: 0.35rem;
    font-size: 0.92rem;
  }
  .workflow-form input,
  .workflow-form textarea {
    padding: 0.45rem;
    border: 1px solid #c7c7c7;
    border-radius: 4px;
    font: inherit;
  }
  .checkbox {
    display: flex !important;
    align-items: center;
    gap: 0.5rem;
  }
  .workflow-list {
    list-style: none;
    padding: 0;
    margin: 1rem 0 0;
    display: grid;
    gap: 0.75rem;
  }
  .workflow-list li {
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 0.75rem;
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
  }
  .wf-name {
    font-weight: 700;
    margin: 0;
  }
  .wf-channels {
    font-size: 0.85rem;
    color: #555;
    margin: 0.25rem 0 0;
  }
  .channel-checkboxes {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.25rem;
  }
  .source-list {
    margin: 0.5rem 0;
    padding-left: 1.2rem;
  }
  .source-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }
  .preview-box {
    margin-top: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 0.75rem;
    background: #fafafa;
  }
  pre {
    white-space: pre-wrap;
    word-break: break-word;
    background: #f4f4f4;
    border-radius: 4px;
    padding: 0.5rem;
    margin: 0.35rem 0 0;
  }
  .actions {
    display: flex;
    align-items: start;
    gap: 0.5rem;
  }
  h2 {
    margin-top: 0;
    font-size: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #444;
  }
  code {
    background: #f4f4f4;
    padding: 0.1em 0.4em;
    border-radius: 3px;
    font-size: 0.9em;
  }
  a {
    color: #0645ad;
  }
  .ok   { color: #0a7d2d; }
  .ko   { color: #b12020; }
  .warn { color: #a06000; }
  .secondary {
    background: #efefef;
  }
  .danger {
    background: #f7d8d8;
    border-color: #da8a8a;
  }
  button {
    margin-top: 0.5rem;
    padding: 0.5rem 1.2rem;
    font-size: 0.95rem;
    cursor: pointer;
  }
  .mini {
    padding: 0.25rem 0.6rem;
    font-size: 0.8rem;
    margin-top: 0;
  }
</style>
