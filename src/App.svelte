<!-- App.svelte — Workflow Studio / Dashboard / Settings -->
<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import { onMount } from "svelte";

  type AppTab = "studio" | "dashboard" | "settings";

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

  const defaultTomlText = `# AuriPostao - Default Configuration
# Template version: 1.0.0
#
# Layer priority (highest wins):
#   default (this file) -> user (~/.config/auripostao/user.toml)
#   -> config/config.toml (local machine, git-ignored)
#   -> runtime (env vars APP__ prefix)
#
# For local overrides (paths, secrets): copy values into config/config.toml (git-ignored).

[app]
name       = "AuriPostao"
version    = "0.1.0"
mode       = "debug"   # debug | normal
language   = "fr"

[config]
schema_version       = 1
enable_layered_merge = true
strict_mode          = false

[path_manager]
allowed_roots = []
temp_dir    = ".tmp"
logs_dir    = "logs"
reports_dir = "reports"
collision_strategy = "increment"   # increment | suffix | short_hash
normalize_unicode  = false
trim_whitespace    = true

[logger]
level          = "info"   # trace | debug | info | warn | error
console_pretty = true
file_json      = true
rotation_enabled = true
max_file_mb      = 20
max_files        = 5
include_context_ids = true

[reporting]
enabled        = true
json_report    = true
csv_report     = true
include_failed = true`;

  let activeTab: AppTab = "studio";

  let health: ApiHealthStatus | null = null;
  let bootstrap: BootstrapStatus | null = null;
  let workflows: Workflow[] = [];
  let workflowsLoading = false;
  let workflowsError = "";
  let workflowsInfo = "";
  let pendingDeleteId: number | null = null;

  let channelStatus: ChannelStatus | null = null;
  let channelsLoading = false;
  let channelsError = "";

  let selectedWorkflowId: number | null = null;
  let isCreatingWorkflow = false;

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

  function resetDocumentState() {
    form = {
      name: "",
      description: "",
      is_active: true,
      channels: [],
    };
    sourceFiles = [];
    sourceDirectory = "";
    includeSubdirs = true;
    maxFileSizeBytes = 1_000_000;
    ingestionPreview = null;
    ingestionError = "";
    ingestionInfo = "";
    ingestionWarning = "";
  }

  function selectedWorkflowLabel(): string {
    if (isCreatingWorkflow) {
      return "New workflow (draft)";
    }
    const current = selectedWorkflow();
    if (!current) {
      return "(no workflow selected)";
    }
    return `${current.name} (#${current.id})`;
  }

  function selectedWorkflow(): Workflow | null {
    if (selectedWorkflowId == null) {
      return null;
    }
    return workflows.find((w) => w.id === selectedWorkflowId) ?? null;
  }

  function apiStateLabel(): string {
    if (health?.api_state === "connectee") {
      return "connected";
    }
    if (health?.api_state === "deconnectee") {
      return "disconnected";
    }
    return "unknown";
  }

  async function loadWorkflows() {
    workflowsLoading = true;
    workflowsError = "";
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
      workflowsInfo = enabled ? "Dummy channel enabled." : "Dummy channel disabled.";
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

    if (selectedWorkflowId != null && !workflows.some((w) => w.id === selectedWorkflowId)) {
      selectedWorkflowId = null;
      isCreatingWorkflow = false;
      resetDocumentState();
    }
  }

  function beginCreateWorkflow() {
    isCreatingWorkflow = true;
    selectedWorkflowId = null;
    resetDocumentState();
    workflowsInfo = "New workflow document initialized.";
  }

  async function openWorkflowDocument(workflow: Workflow) {
    isCreatingWorkflow = false;
    selectedWorkflowId = workflow.id;
    workflowsInfo = "";

    form = {
      name: workflow.name,
      description: workflow.description,
      is_active: workflow.is_active,
      channels: [...workflow.channels],
    };

    ingestionPreview = null;
    ingestionError = "";
    ingestionInfo = "";
    ingestionWarning = "";

    try {
      const cfg = await invoke<WorkflowSourcesConfig>("workflow_sources_get", {
        workflowId: workflow.id,
      });
      sourceFiles = cfg.file_paths ?? [];
      sourceDirectory = cfg.directory_path ?? "";
      includeSubdirs = cfg.recursive;
      maxFileSizeBytes = cfg.max_file_size_bytes;
      ingestionInfo = "Workflow document loaded.";
    } catch (e) {
      ingestionError = invokeError(e);
      sourceFiles = [];
      sourceDirectory = "";
      includeSubdirs = true;
      maxFileSizeBytes = 1_000_000;
    }
  }

  async function submitWorkflowDocument() {
    workflowsError = "";
    workflowsInfo = "";

    if (!form.name.trim()) {
      workflowsError = "validation_error: name is required";
      return;
    }
    if (form.channels.length === 0) {
      workflowsError = "validation_error: select at least one channel";
      return;
    }
    if (isCreatingWorkflow && !channelStatus?.has_valid_channel) {
      workflowsError = "no_valid_channel: configure at least one valid channel before creating a workflow";
      return;
    }

    try {
      let workflowId = selectedWorkflowId;

      if (isCreatingWorkflow) {
        const created = await invoke<Workflow>("workflows_create", {
          payload: {
            name: form.name,
            description: form.description,
            is_active: form.is_active,
            channels: form.channels,
          },
        });
        workflowId = created.id;
        selectedWorkflowId = created.id;
        isCreatingWorkflow = false;
      } else if (selectedWorkflowId != null) {
        await invoke<Workflow>("workflows_update", {
          workflowId: selectedWorkflowId,
          payload: {
            name: form.name,
            description: form.description,
            is_active: form.is_active,
          },
        });
        await invoke<string[]>("workflow_channels_set", {
          workflowId: selectedWorkflowId,
          channels: form.channels,
        });
      } else {
        workflowsError = "Select a workflow or create a new document.";
        return;
      }

      await invoke<WorkflowSourcesConfig>("workflow_sources_set", {
        workflowId,
        payload: {
          file_paths: sourceFiles,
          directory_path: sourceDirectory || null,
          recursive: includeSubdirs,
          max_file_size_bytes: maxFileSizeBytes,
        },
      });

      workflowsInfo = "Workflow document saved.";
      await loadWorkflows();
      const target = workflows.find((w) => w.id === workflowId);
      if (target) {
        await openWorkflowDocument(target);
      }
    } catch (e) {
      workflowsError = invokeError(e);
    }
  }

  async function removeWorkflow(w: Workflow) {
    workflowsError = "";
    workflowsInfo = "";
    try {
      await invoke<boolean>("workflows_delete", { workflowId: w.id });
      workflowsInfo = "Workflow deleted.";
      pendingDeleteId = null;

      if (selectedWorkflowId === w.id) {
        selectedWorkflowId = null;
        isCreatingWorkflow = false;
        resetDocumentState();
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
        ingestionInfo = "No file selected.";
        return;
      }
      sourceFiles = dedupePaths([...sourceFiles, ...picked]);
      ingestionInfo = `${sourceFiles.length} file(s) in this document.`;
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
        ingestionInfo = "Directory selected for this document.";
      }
    } catch (e) {
      ingestionError = invokeError(e);
    }
  }

  function removeSourceFile(path: string) {
    sourceFiles = sourceFiles.filter((p) => p !== path);
    ingestionInfo = sourceFiles.length > 0 ? `${sourceFiles.length} file(s) in this document.` : "No file.";
  }

  function clearSourceDirectory() {
    sourceDirectory = "";
  }

  function clearAllSources() {
    sourceFiles = [];
    sourceDirectory = "";
    ingestionPreview = null;
    ingestionWarning = "";
    ingestionInfo = "Document sources reset.";
  }

  async function runIngestionPreview() {
    ingestionError = "";
    ingestionWarning = "";
    ingestionInfo = "";
    ingestionPreview = null;

    if (isCreatingWorkflow || selectedWorkflowId == null) {
      ingestionError = "Save the workflow first before testing ingestion.";
      return;
    }
    if (sourceFiles.length === 0 && !sourceDirectory) {
      ingestionError = "No source selected in this workflow.";
      return;
    }

    ingestionLoading = true;
    try {
      await invoke<WorkflowSourcesConfig>("workflow_sources_set", {
        workflowId: selectedWorkflowId,
        payload: {
          file_paths: sourceFiles,
          directory_path: sourceDirectory || null,
          recursive: includeSubdirs,
          max_file_size_bytes: maxFileSizeBytes,
        },
      });

      ingestionPreview = await invoke<IngestionPreview>("workflow_ingestion_preview", {
        workflowId: selectedWorkflowId,
      });

      const tooLargeFiles = ingestionPreview.ignored_files.filter((x) => x.reason === "file_too_large");
      if (tooLargeFiles.length > 0) {
        ingestionWarning =
          `${tooLargeFiles.length} file(s) exceed the size threshold ` +
          `(${formatBytes(maxFileSizeBytes)} max per file).`;
      }

      if (ingestionPreview.summary.accepted === 0) {
        ingestionError =
          "No valid source detected. Add at least one readable text file (.txt/.md) under the size threshold.";
      } else {
        ingestionInfo = "Ingestion preview generated for this workflow.";
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

<main class="app-shell">
  <header class="topbar">
    <div>
      <h1>AuriPostao <span class="version">{bootstrap?.app_version ?? "..."}</span></h1>
      <p class="subtitle">Post-production editor for workflow documents</p>
    </div>
    <div class="badge">Mode {bootstrap?.mode ?? "..."}</div>
  </header>

  <nav class="tabs" aria-label="Navigation principale">
    <button class:active={activeTab === "studio"} on:click={() => (activeTab = "studio")}>Workflow Studio</button>
    <button class:active={activeTab === "dashboard"} on:click={() => (activeTab = "dashboard")}>Dashboard</button>
    <button class:active={activeTab === "settings"} on:click={() => (activeTab = "settings")}>Settings</button>
  </nav>

  {#if activeTab === "studio"}
    <section class="grid-two">
      <article class="card">
        <h2>Workflow Explorer</h2>
        <p class="muted">Choose an existing workflow or create a new complete document.</p>

        <div class="actions">
          <button type="button" on:click={beginCreateWorkflow} disabled={!channelStatus?.has_valid_channel}>
            New workflow
          </button>
        </div>

        {#if !channelStatus?.has_valid_channel}
          <p class="warn">No valid channel configured. Enable one in Settings.</p>
        {/if}

        {#if workflowsLoading}
          <p>Loading workflows...</p>
        {:else if workflows.length === 0}
          <p>No workflow available.</p>
        {:else}
          <ul class="workflow-list">
            {#each workflows as w}
              <li class:selected={selectedWorkflowId === w.id && !isCreatingWorkflow}>
                <div>
                  <p class="wf-name">{w.name}</p>
                  <p class="muted">{w.description || "No description"}</p>
                  <p class="wf-meta">Channels: {w.channels?.length ? w.channels.join(", ") : "none"}</p>
                </div>
                <div class="actions compact">
                  <button type="button" class="secondary" on:click={() => openWorkflowDocument(w)}>Open</button>
                  {#if pendingDeleteId === w.id}
                    <button type="button" class="danger" on:click={() => removeWorkflow(w)}>Confirm</button>
                    <button type="button" class="secondary" on:click={() => (pendingDeleteId = null)}>Cancel</button>
                  {:else}
                    <button type="button" class="danger" on:click={() => (pendingDeleteId = w.id)}>Delete</button>
                  {/if}
                </div>
              </li>
            {/each}
          </ul>
        {/if}
      </article>

      <article class="card">
        <h2>Workflow Document</h2>
        <p class="muted">Context: {selectedWorkflowLabel()}</p>

        {#if workflowsError}<p class="ko">{workflowsError}</p>{/if}
        {#if workflowsInfo}<p class="ok">{workflowsInfo}</p>{/if}

        {#if !(isCreatingWorkflow || selectedWorkflowId != null)}
          <p class="warn">Select a workflow to activate document blocks.</p>
        {:else}
          <form class="workflow-form" on:submit|preventDefault={submitWorkflowDocument}>
            <h3>Block 1. Metadata</h3>
            <label>
              Title
              <input bind:value={form.name} placeholder="Workflow title" maxlength="120" required />
            </label>
            <label>
              Description
              <textarea bind:value={form.description} rows="3" placeholder="Description" />
            </label>
            <label class="checkbox">
              <input type="checkbox" bind:checked={form.is_active} />
              Active workflow
            </label>

            <h3>Block 2. Channels</h3>
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
              <p class="warn">No valid channel available.</p>
            {/if}

            <h3>Block 3. Sources</h3>
            <div class="actions">
              <button type="button" on:click={pickFiles}>Add text files</button>
              <button type="button" class="secondary" on:click={pickDirectory}>Pick directory</button>
              <button type="button" class="secondary" on:click={clearAllSources}>Reset</button>
            </div>

            <p>Selected files: {sourceFiles.length}</p>
            {#if sourceFiles.length > 0}
              <ul class="source-list">
                {#each sourceFiles as filePath}
                  <li class="source-row">
                    <span>{filePath}</span>
                    <button type="button" class="secondary mini" on:click={() => removeSourceFile(filePath)}>Remove</button>
                  </li>
                {/each}
              </ul>
            {/if}

            <p>Directory: {sourceDirectory || "none"}</p>
            {#if sourceDirectory}
              <button type="button" class="secondary mini" on:click={clearSourceDirectory}>Remove directory</button>
            {/if}

            <label class="checkbox">
              <input type="checkbox" bind:checked={includeSubdirs} />
              Include subdirectories
            </label>
            <label>
              Max size per file (bytes)
              <input type="number" min="1" step="1" bind:value={maxFileSizeBytes} />
            </label>

            <h3>Block 4. Scheduler</h3>
            <p class="muted">Reserved slot. Scheduler configuration comes in the next user story.</p>

            <div class="actions">
              <button type="submit">Save workflow document</button>
              {#if isCreatingWorkflow}
                <button type="button" class="secondary" on:click={resetDocumentState}>Clear draft</button>
              {/if}
            </div>
          </form>

          <div class="preview-box">
            <h3>Block 5. Pre-run validation</h3>
            <div class="actions">
              <button type="button" on:click={runIngestionPreview} disabled={ingestionLoading}>
                {#if ingestionLoading}Ingesting...{:else}Test ingestion{/if}
              </button>
            </div>

            {#if ingestionError}<p class="ko">{ingestionError}</p>{/if}
            {#if ingestionWarning}<p class="warn">{ingestionWarning}</p>{/if}
            {#if ingestionInfo}<p class="ok">{ingestionInfo}</p>{/if}

            {#if ingestionPreview}
              <p>
                Summary: {ingestionPreview.summary.accepted} accepted, {ingestionPreview.summary.ignored} ignored,
                {ingestionPreview.summary.errors} error(s), {ingestionPreview.summary.total_candidates} candidate(s),
                total size {formatBytes(ingestionPreview.summary.total_size_bytes)}
              </p>

              {#if ingestionPreview.accepted_files.length > 0}
                <h4>Content samples</h4>
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
                <h4>Ignored files</h4>
                <ul class="source-list">
                  {#each ingestionPreview.ignored_files as item}
                    <li>{item.path} - {item.reason}</li>
                  {/each}
                </ul>
              {/if}

              {#if ingestionPreview.errors.length > 0}
                <h4>Errors</h4>
                <ul class="source-list">
                  {#each ingestionPreview.errors as item}
                    <li>{item.path} - {item.reason}</li>
                  {/each}
                </ul>
              {/if}
            {/if}
          </div>
        {/if}
      </article>
    </section>
  {/if}

  {#if activeTab === "dashboard"}
    <section class="grid-three">
      <article class="card metric">
        <h2>Connexions</h2>
        <p>API: <strong class={health?.api_state === "connectee" ? "ok" : "ko"}>{apiStateLabel()}</strong></p>
        <p class="muted">Endpoint: {health?.api_url ?? "http://127.0.0.1:8787"}</p>
        <p class="muted">Message: {health?.message ?? "-"}</p>
      </article>

      <article class="card metric">
        <h2>System State</h2>
        <p>Service: <strong>{health?.service || "n/a"}</strong></p>
        <p>Version API: <strong>{health?.version || "n/a"}</strong></p>
        <p class="muted">UTC: {health?.time_utc || "n/a"}</p>
      </article>

      <article class="card metric">
        <h2>Database</h2>
        <p>Status: <strong class={bootstrap?.db_exists ? "ok" : "warn"}>{bootstrap?.db_exists ? "detected" : "missing"}</strong></p>
        <p class="muted">Path: {bootstrap?.db_path ?? "..."}</p>
      </article>

      <article class="card metric">
        <h2>Workflows</h2>
        <p>Total: <strong>{workflows.length}</strong></p>
        <p>Active: <strong>{workflows.filter((w) => w.is_active).length}</strong></p>
        <p>Opened context: <strong>{selectedWorkflow()?.name || "none"}</strong></p>
      </article>

      <article class="card metric">
        <h2>Channels</h2>
        <p>Valid: <strong>{channelStatus?.valid_channels?.length ?? 0}</strong></p>
        <p class="muted">{channelStatus?.valid_channels?.join(", ") || "none"}</p>
        <div class="actions compact">
          <button type="button" on:click={() => setDummyChannel(true)} disabled={channelsLoading}>Enable dummy</button>
          <button type="button" class="secondary" on:click={() => setDummyChannel(false)} disabled={channelsLoading}>Disable</button>
        </div>
        {#if channelsError}<p class="ko">{channelsError}</p>{/if}
      </article>

      <article class="card metric">
        <h2>Control</h2>
        <p class="muted">Refreshes all runtime states and displayed metrics.</p>
        <button on:click={runChecks} disabled={loading}>
          {#if loading}Checking...{:else}Refresh dashboard{/if}
        </button>
      </article>
    </section>
  {/if}

  {#if activeTab === "settings"}
    <section class="card">
      <h2>Settings</h2>
      <p class="muted">
        Read-only view of the default configuration. Settings CRUD is intentionally postponed.
      </p>
      <pre class="toml-block">{defaultTomlText}</pre>
    </section>
  {/if}
</main>

<style>
  :global(body) {
    margin: 0;
    background: radial-gradient(circle at 20% 0%, #1d2433 0%, #111620 50%, #0c1018 100%);
    color: #e6ecff;
  }

  :global(*) {
    box-sizing: border-box;
  }

  .app-shell {
    --bg-card: rgba(18, 25, 37, 0.86);
    --border: #2b354a;
    --text-main: #e6ecff;
    --text-muted: #9fb0cf;
    --accent: #66d6c4;
    --accent-2: #4ea1ff;
    --ok: #2fd08c;
    --ko: #ff7f8a;
    --warn: #ffbe66;

    max-width: 1220px;
    margin: 0 auto;
    padding: 1.4rem;
    color: var(--text-main);
    font-family: "Avenir Next", "Segoe UI", sans-serif;
  }

  .topbar {
    display: flex;
    justify-content: space-between;
    align-items: start;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  h1 {
    margin: 0;
    display: flex;
    gap: 0.5rem;
    align-items: baseline;
    font-size: 1.55rem;
    letter-spacing: 0.01em;
  }

  .version {
    font-size: 0.88rem;
    color: var(--text-muted);
    font-weight: 500;
  }

  .subtitle {
    margin: 0.2rem 0 0;
    color: var(--text-muted);
    font-size: 0.92rem;
  }

  .badge {
    border: 1px solid var(--border);
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    color: var(--accent);
    background: rgba(78, 161, 255, 0.08);
    white-space: nowrap;
    font-size: 0.85rem;
  }

  .tabs {
    display: flex;
    gap: 0.55rem;
    margin: 1.1rem 0;
  }

  .tabs button {
    border: 1px solid var(--border);
    background: rgba(30, 39, 56, 0.8);
    color: var(--text-main);
    border-radius: 10px;
    padding: 0.58rem 0.95rem;
    cursor: pointer;
    font-size: 0.92rem;
  }

  .tabs button.active {
    background: linear-gradient(135deg, rgba(102, 214, 196, 0.22), rgba(78, 161, 255, 0.22));
    border-color: var(--accent);
  }

  .grid-two {
    display: grid;
    grid-template-columns: 360px 1fr;
    gap: 1rem;
  }

  .grid-three {
    display: grid;
    grid-template-columns: repeat(3, minmax(220px, 1fr));
    gap: 1rem;
  }

  .card {
    border: 1px solid var(--border);
    background: var(--bg-card);
    border-radius: 14px;
    padding: 1rem;
    backdrop-filter: blur(4px);
    min-width: 0;
  }

  .card p,
  .card li,
  .card span {
    overflow-wrap: anywhere;
    word-break: break-word;
  }

  .metric p {
    margin: 0.3rem 0;
  }

  h2 {
    margin: 0 0 0.55rem;
    font-size: 0.98rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--accent-2);
  }

  h3 {
    margin: 0.6rem 0 0.45rem;
    font-size: 0.94rem;
    color: #d8e2ff;
  }

  h4 {
    margin: 0.6rem 0 0.35rem;
    font-size: 0.9rem;
    color: #d8e2ff;
  }

  .muted {
    color: var(--text-muted);
  }

  .workflow-form {
    display: grid;
    gap: 0.65rem;
  }

  .workflow-form label {
    display: grid;
    gap: 0.28rem;
    font-size: 0.92rem;
  }

  input,
  textarea,
  button {
    font: inherit;
  }

  input,
  textarea {
    background: rgba(10, 14, 22, 0.82);
    color: var(--text-main);
    border: 1px solid #33405b;
    border-radius: 8px;
    padding: 0.48rem 0.55rem;
  }

  textarea {
    resize: vertical;
    min-height: 88px;
  }

  .checkbox {
    display: flex !important;
    align-items: center;
    gap: 0.55rem;
  }

  .channel-checkboxes {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem 0.8rem;
  }

  .workflow-list {
    list-style: none;
    margin: 0.8rem 0 0;
    padding: 0;
    display: grid;
    gap: 0.65rem;
  }

  .workflow-list li {
    border: 1px solid #33405b;
    border-radius: 10px;
    padding: 0.7rem;
    background: rgba(10, 14, 22, 0.42);
    display: grid;
    gap: 0.55rem;
    min-width: 0;
  }

  .workflow-list li.selected {
    border-color: var(--accent);
    box-shadow: 0 0 0 1px rgba(102, 214, 196, 0.25) inset;
  }

  .wf-name {
    margin: 0;
    font-weight: 700;
    word-break: break-word;
  }

  .wf-meta {
    margin: 0.25rem 0 0;
    color: var(--text-muted);
    font-size: 0.85rem;
  }

  .source-list {
    margin: 0.4rem 0;
    padding-left: 1.15rem;
    display: grid;
    gap: 0.35rem;
  }

  .source-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    min-width: 0;
  }

  .source-row span {
    overflow-wrap: anywhere;
    word-break: break-word;
    min-width: 0;
    flex: 1;
  }

  .preview-box {
    margin-top: 1rem;
    border: 1px solid #33405b;
    border-radius: 10px;
    padding: 0.8rem;
    background: rgba(10, 14, 22, 0.55);
  }

  .toml-block {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    border-radius: 10px;
    border: 1px solid #33405b;
    background: rgba(10, 14, 22, 0.7);
    padding: 0.8rem;
    color: #c8d7ff;
    max-height: 60vh;
    overflow: auto;
  }

  pre {
    white-space: pre-wrap;
    word-break: break-word;
    background: rgba(10, 14, 22, 0.7);
    border: 1px solid #33405b;
    color: #c8d7ff;
    border-radius: 8px;
    padding: 0.55rem;
    margin: 0.25rem 0 0;
  }

  .actions {
    display: flex;
    gap: 0.45rem;
    flex-wrap: wrap;
    align-items: flex-start;
  }

  .actions.compact {
    gap: 0.35rem;
  }

  button {
    border: 1px solid #395078;
    border-radius: 8px;
    background: linear-gradient(135deg, rgba(78, 161, 255, 0.25), rgba(53, 86, 173, 0.25));
    color: var(--text-main);
    padding: 0.44rem 0.82rem;
    cursor: pointer;
  }

  button:hover {
    filter: brightness(1.1);
  }

  button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .secondary {
    background: rgba(71, 87, 117, 0.36);
    border-color: #4b607f;
  }

  .danger {
    background: rgba(172, 67, 87, 0.25);
    border-color: #96515e;
  }

  .mini {
    padding: 0.25rem 0.55rem;
    font-size: 0.8rem;
  }

  .ok {
    color: var(--ok);
  }

  .ko {
    color: var(--ko);
  }

  .warn {
    color: var(--warn);
  }

  @media (max-width: 980px) {
    .grid-two {
      grid-template-columns: 1fr;
    }

    .grid-three {
      grid-template-columns: 1fr;
    }

    .topbar {
      flex-direction: column;
      align-items: start;
    }

    .tabs {
      width: 100%;
      overflow-x: auto;
      padding-bottom: 0.25rem;
    }

    .tabs button {
      white-space: nowrap;
    }

    .app-shell {
      padding: 1rem 0.8rem 1.2rem;
    }

    .card {
      padding: 0.85rem;
    }
  }
</style>
