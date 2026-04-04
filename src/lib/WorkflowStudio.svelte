<!-- WorkflowStudio.svelte — Studio tab: Workflow Explorer + Document -->
<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import type { Workflow, WorkflowForm, ChannelStatus, WorkflowSourcesConfig, ScheduleDto } from "./types";
  import { invokeError, dedupePaths } from "./utils";
  import IngestionBlock from "./IngestionBlock.svelte";
  import GenerationBlock from "./GenerationBlock.svelte";

  export let workflows: Workflow[];
  export let channelStatus: ChannelStatus | null;
  export let selectedWorkflowId: number | null;
  export let isCreatingWorkflow: boolean;
  export let planningWorkflowId: number | null;

  let form: WorkflowForm = { name: "", description: "", is_active: true, channels: [] };
  let pendingDeleteId: number | null = null;
  let workflowsError = "";
  let workflowsInfo = "";
  let sourceFiles: string[] = [];
  let sourceDirectory = "";
  let includeSubdirs = true;
  let maxFileSizeBytes = 1_000_000;
  let sourcesInfo = "";
  let sourcesError = "";

  let scheduleType = "none";
  let scheduleTimes: string[] = ["08:00"];
  let scheduleTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  let scheduleCatchup = false;
  let scheduleRequireApproval = false;
  let scheduleRunAt = "";
  let scheduleLoading = false;
  let scheduleSaved = false;
  let scheduleError = "";

  let ingestionRef: IngestionBlock;

  function selectedWorkflow(): Workflow | null {
    if (selectedWorkflowId == null) return null;
    return workflows.find((w) => w.id === selectedWorkflowId) ?? null;
  }

  function selectedWorkflowLabel(): string {
    if (isCreatingWorkflow) return "New workflow (draft)";
    const current = selectedWorkflow();
    return current ? `${current.name} (#${current.id})` : "(no workflow selected)";
  }

  function resetDocumentState() {
    form = { name: "", description: "", is_active: true, channels: [] };
    sourceFiles = []; sourceDirectory = ""; includeSubdirs = true; maxFileSizeBytes = 1_000_000;
    sourcesInfo = ""; sourcesError = "";
    scheduleType = "none"; scheduleTimes = ["08:00"];
    scheduleTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    scheduleCatchup = false; scheduleRequireApproval = false; scheduleRunAt = "";
    scheduleSaved = false; scheduleError = "";
    ingestionRef?.reset();
  }

  function beginCreateWorkflow() {
    isCreatingWorkflow = true;
    selectedWorkflowId = null;
    resetDocumentState();
    workflowsInfo = "Nouveau document de workflow initialisé.";
  }

  async function openWorkflowDocument(workflow: Workflow) {
    isCreatingWorkflow = false;
    selectedWorkflowId = workflow.id;
    planningWorkflowId = workflow.id;
    workflowsInfo = ""; sourcesInfo = ""; sourcesError = "";

    form = { name: workflow.name, description: workflow.description, is_active: workflow.is_active, channels: [...workflow.channels] };

    try {
      const cfg = await invoke<WorkflowSourcesConfig>("workflow_sources_get", { workflowId: workflow.id });
      sourceFiles = cfg.file_paths ?? [];
      sourceDirectory = cfg.directory_path ?? "";
      includeSubdirs = cfg.recursive;
      maxFileSizeBytes = cfg.max_file_size_bytes;
      sourcesInfo = "Document de workflow chargé.";
    } catch (e) {
      sourcesError = invokeError(e);
      sourceFiles = []; sourceDirectory = ""; includeSubdirs = true; maxFileSizeBytes = 1_000_000;
    }

    await loadScheduleConfig();
  }

  async function submitWorkflowDocument() {
    workflowsError = ""; workflowsInfo = "";
    if (!form.name.trim()) { workflowsError = "Erreur : le titre est obligatoire."; return; }
    if (form.channels.length === 0) { workflowsError = "Erreur : sélectionnez au moins un canal."; return; }
    if (isCreatingWorkflow && !channelStatus?.has_valid_channel) {
      workflowsError = "Aucun canal valide : configurez un canal avant de créer un workflow."; return;
    }
    try {
      let workflowId = selectedWorkflowId;
      if (isCreatingWorkflow) {
        const created = await invoke<Workflow>("workflows_create", {
          payload: { name: form.name, description: form.description, is_active: form.is_active, channels: form.channels },
        });
        workflowId = created.id;
        selectedWorkflowId = created.id;
        isCreatingWorkflow = false;
      } else if (selectedWorkflowId != null) {
        await invoke<Workflow>("workflows_update", {
          workflowId: selectedWorkflowId,
          payload: { name: form.name, description: form.description, is_active: form.is_active },
        });
        await invoke<string[]>("workflow_channels_set", { workflowId: selectedWorkflowId, channels: form.channels });
      } else { workflowsError = "Sélectionnez un workflow ou créez un nouveau document."; return; }

      await invoke<WorkflowSourcesConfig>("workflow_sources_set", {
        workflowId,
        payload: { file_paths: sourceFiles, directory_path: sourceDirectory || null, recursive: includeSubdirs, max_file_size_bytes: maxFileSizeBytes },
      });
      workflowsInfo = "Document de workflow sauvegardé.";
      workflows = await invoke<Workflow[]>("workflows_list");
      const target = workflows.find((w) => w.id === workflowId);
      if (target) await openWorkflowDocument(target);
    } catch (e) { workflowsError = invokeError(e); }
  }

  async function removeWorkflow(w: Workflow) {
    workflowsError = ""; workflowsInfo = "";
    try {
      await invoke<boolean>("workflows_delete", { workflowId: w.id });
      workflowsInfo = "Workflow supprimé.";
      pendingDeleteId = null;
      if (selectedWorkflowId === w.id) { selectedWorkflowId = null; isCreatingWorkflow = false; resetDocumentState(); }
      workflows = await invoke<Workflow[]>("workflows_list");
    } catch (e) { workflowsError = invokeError(e); }
  }

  async function pickFiles() {
    sourcesError = "";
    try {
      const picked = await invoke<string[]>("pick_text_files");
      if (picked.length === 0) { sourcesInfo = "Aucun fichier sélectionné."; return; }
      sourceFiles = dedupePaths([...sourceFiles, ...picked]);
      sourcesInfo = `${sourceFiles.length} fichier(s) dans ce document.`;
    } catch (e) { sourcesError = invokeError(e); }
  }

  async function pickDirectory() {
    sourcesError = "";
    try {
      const picked = await invoke<string | null>("pick_directory");
      sourceDirectory = picked ?? "";
      if (sourceDirectory) sourcesInfo = "Dossier sélectionné pour ce document.";
    } catch (e) { sourcesError = invokeError(e); }
  }

  function removeSourceFile(path: string) {
    sourceFiles = sourceFiles.filter((p) => p !== path);
    sourcesInfo = sourceFiles.length > 0 ? `${sourceFiles.length} fichier(s) dans ce document.` : "Aucun fichier.";
  }

  function clearSourceDirectory() { sourceDirectory = ""; }

  function clearAllSources() {
    sourceFiles = []; sourceDirectory = "";
    ingestionRef?.reset();
    sourcesInfo = "Sources du document réinitialisées.";
  }

  async function loadScheduleConfig() {
    if (selectedWorkflowId == null) return;
    try {
      const sc = await invoke<ScheduleDto>("workflow_schedule_get", { workflowId: selectedWorkflowId });
      scheduleType = sc.schedule_type;
      scheduleTimes = sc.times.length > 0 ? [...sc.times] : ["08:00"];
      scheduleTimezone = sc.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
      scheduleCatchup = sc.catchup_enabled;
      scheduleRequireApproval = sc.require_approval;
      scheduleRunAt = sc.run_at ?? "";
    } catch (_e) { /* keep defaults */ }
  }

  async function saveScheduleConfig() {
    if (selectedWorkflowId == null) return;
    scheduleLoading = true; scheduleSaved = false; scheduleError = "";
    try {
      await invoke("workflow_schedule_set", {
        workflowId: selectedWorkflowId,
        payload: {
          schedule_type: scheduleType, timezone: scheduleTimezone, run_at: scheduleRunAt || null,
          times: scheduleTimes.filter((t) => t.trim()), weekdays: [], monthdays: [],
          catchup_enabled: scheduleCatchup, require_approval: scheduleRequireApproval,
        },
      });
      scheduleSaved = true;
      setTimeout(() => { scheduleSaved = false; }, 3000);
    } catch (e) { scheduleError = invokeError(e); }
    finally { scheduleLoading = false; }
  }
</script>

<section class="grid-two">
  <article class="card">
    <h2>Explorateur de workflows</h2>
    <p class="muted">Choisissez un workflow existant ou créez un nouveau document complet.</p>
    <div class="actions">
      <button type="button" on:click={beginCreateWorkflow} disabled={!channelStatus?.has_valid_channel}>Nouveau workflow</button>
    </div>
    {#if !channelStatus?.has_valid_channel}
      <p class="warn">Aucun canal valide configuré. Activez-en un dans Paramètres.</p>
    {/if}
    {#if workflows.length === 0}
      <p>Aucun workflow disponible.</p>
    {:else}
      <ul class="workflow-list">
        {#each workflows as w}
          <li class:selected={selectedWorkflowId === w.id && !isCreatingWorkflow}>
            <div>
              <p class="wf-name">{w.name}</p>
              <p class="muted">{w.description || "Sans description"}</p>
              <p class="wf-meta">Canaux : {w.channels?.length ? w.channels.join(", ") : "aucun"}</p>
            </div>
            <div class="actions compact">
              <button type="button" class="secondary" on:click={() => openWorkflowDocument(w)}>Ouvrir</button>
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
  </article>

  <article class="card">
    <h2>Document de workflow</h2>
    <p class="muted">Contexte : {selectedWorkflowLabel()}</p>

    {#if workflowsError}<p class="ko">{workflowsError}</p>{/if}
    {#if workflowsInfo}<p class="ok">{workflowsInfo}</p>{/if}

    {#if !(isCreatingWorkflow || selectedWorkflowId != null)}
      <p class="warn">Sélectionnez un workflow pour activer les blocs du document.</p>
    {:else}
      <form class="workflow-form" on:submit|preventDefault={submitWorkflowDocument}>
        <h3>Bloc 1. Métadonnées</h3>
        <label>
          Titre
          <input bind:value={form.name} placeholder="Titre du workflow" maxlength="120" required />
        </label>
        <label>
          Description
          <textarea bind:value={form.description} rows="3" placeholder="Description" />
        </label>
        <label class="checkbox">
          <input type="checkbox" bind:checked={form.is_active} />
          Workflow actif
        </label>

        <h3>Bloc 2. Canaux</h3>
        {#if channelStatus?.valid_channels?.length}
          <div class="channel-checkboxes">
            {#each channelStatus.valid_channels as ch}
              <label class="checkbox"><input type="checkbox" bind:group={form.channels} value={ch} /> {ch}</label>
            {/each}
          </div>
        {:else}
          <p class="warn">Aucun canal valide disponible.</p>
        {/if}

        <h3>Bloc 3. Sources</h3>
        <div class="actions">
          <button type="button" on:click={pickFiles}>Ajouter des fichiers texte</button>
          <button type="button" class="secondary" on:click={pickDirectory}>Choisir un dossier</button>
          <button type="button" class="secondary" on:click={clearAllSources}>Réinitialiser</button>
        </div>
        {#if sourcesError}<p class="ko">{sourcesError}</p>{/if}
        {#if sourcesInfo}<p class="ok">{sourcesInfo}</p>{/if}
        <p>Fichiers sélectionnés : {sourceFiles.length}</p>
        {#if sourceFiles.length > 0}
          <ul class="source-list">
            {#each sourceFiles as filePath}
              <li class="source-row">
                <span>{filePath}</span>
                <button type="button" class="secondary mini" on:click={() => removeSourceFile(filePath)}>Retirer</button>
              </li>
            {/each}
          </ul>
        {/if}
        <p>Dossier : {sourceDirectory || "aucun"}</p>
        {#if sourceDirectory}
          <button type="button" class="secondary mini" on:click={clearSourceDirectory}>Retirer le dossier</button>
        {/if}
        <label class="checkbox">
          <input type="checkbox" bind:checked={includeSubdirs} /> Inclure les sous-dossiers
        </label>
        <label>
          Taille max par fichier (octets)
          <input type="number" min="1" step="1" bind:value={maxFileSizeBytes} />
        </label>

        <h3>Bloc 4. Planification</h3>
        {#if isCreatingWorkflow}
          <p class="muted">Sauvegardez le workflow pour configurer la planification.</p>
        {:else}
          <div class="gen-config-grid">
            <label>
              Type de planification
              <select bind:value={scheduleType}>
                <option value="none">Aucun</option>
                <option value="one_shot">Ponctuel</option>
                <option value="daily">Quotidien</option>
                <option value="weekly">Hebdomadaire</option>
                <option value="monthly">Mensuel</option>
              </select>
            </label>
            {#if scheduleType !== "none" && scheduleType !== "one_shot"}
              <label>Heure du créneau (HH:MM) <input type="time" bind:value={scheduleTimes[0]} /></label>
            {/if}
            {#if scheduleType === "one_shot"}
              <label>Date et heure <input type="datetime-local" bind:value={scheduleRunAt} /></label>
            {/if}
            <label>Fuseau horaire <input bind:value={scheduleTimezone} placeholder="Europe/Paris" /></label>
          </div>
          <label class="checkbox"><input type="checkbox" bind:checked={scheduleRequireApproval} /> Valider avant envoi</label>
          <label class="checkbox"><input type="checkbox" bind:checked={scheduleCatchup} /> Rattrapage au démarrage</label>
          {#if scheduleError}<p class="ko">{scheduleError}</p>{/if}
          <div class="actions" style="margin-top:0.5rem;">
            <button type="button" class="secondary" on:click={saveScheduleConfig} disabled={scheduleLoading}>
              {scheduleLoading ? "Sauvegarde..." : "Sauvegarder la planification"}
            </button>
            {#if scheduleSaved}<span class="ok" style="font-size:0.88rem; align-self:center;">Planification sauvegardée.</span>{/if}
          </div>
        {/if}

        <div class="actions">
          <button type="submit">Sauvegarder le document de workflow</button>
          {#if isCreatingWorkflow}
            <button type="button" class="secondary" on:click={resetDocumentState}>Effacer le brouillon</button>
          {/if}
        </div>
      </form>

      {#key selectedWorkflowId}
        <IngestionBlock bind:this={ingestionRef}
          {selectedWorkflowId} {isCreatingWorkflow} {sourceFiles} {sourceDirectory} {includeSubdirs} {maxFileSizeBytes} />
        <GenerationBlock {selectedWorkflowId} {isCreatingWorkflow} />
      {/key}
    {/if}
  </article>
</section>

<style>
  .grid-two { display: grid; grid-template-columns: 360px 1fr; gap: 1rem; }
  .workflow-form { display: grid; gap: 0.65rem; }
  .workflow-form label { display: grid; gap: 0.28rem; font-size: 0.92rem; }
  .channel-checkboxes { display: flex; flex-wrap: wrap; gap: 0.45rem 0.8rem; }
  .workflow-list { list-style: none; margin: 0.8rem 0 0; padding: 0; display: grid; gap: 0.65rem; }
  .workflow-list li { border: 1px solid #33405b; border-radius: 10px; padding: 0.7rem; background: rgba(10, 14, 22, 0.42); display: grid; gap: 0.55rem; min-width: 0; }
  .workflow-list li.selected { border-color: var(--accent); box-shadow: 0 0 0 1px rgba(102, 214, 196, 0.25) inset; }
  .wf-name { margin: 0; font-weight: 700; word-break: break-word; }
  .wf-meta { margin: 0.25rem 0 0; color: var(--text-muted); font-size: 0.85rem; }
  .source-list { margin: 0.4rem 0; padding-left: 1.15rem; display: grid; gap: 0.35rem; }
  .source-row { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; min-width: 0; }
  .source-row span { overflow-wrap: anywhere; word-break: break-word; min-width: 0; flex: 1; }
  @media (max-width: 980px) { .grid-two { grid-template-columns: 1fr; } }
</style>
