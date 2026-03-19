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
  };

  type WorkflowForm = {
    name: string;
    description: string;
    is_active: boolean;
  };

  type ChannelStatus = {
    has_valid_channel: boolean;
    valid_channels: string[];
    config_url: string;
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
  let form: WorkflowForm = {
    name: "",
    description: "",
    is_active: true,
  };
  let loading = false;

  function invokeError(e: unknown): string {
    if (typeof e === "string") {
      return e;
    }
    return `Erreur Tauri: ${String(e)}`;
  }

  function resetForm() {
    editingId = null;
    form = {
      name: "",
      description: "",
      is_active: true,
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
  }

  async function submitWorkflow() {
    workflowsError = "";
    workflowsInfo = "";
    if (!form.name.trim()) {
      workflowsError = "validation_error: name is required";
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
            </div>
            <div class="actions">
              <button type="button" class="secondary" on:click={() => startEdit(w)}>Editer</button>
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
</style>
