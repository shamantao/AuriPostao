<!-- App.svelte — Shell with navigation and tab routing -->
<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import { onMount } from "svelte";
  import type { ApiHealthStatus, BootstrapStatus, Workflow, ChannelStatus, AppTab } from "./lib/types";
  import WorkflowStudio from "./lib/WorkflowStudio.svelte";
  import PlanningConsole from "./lib/PlanningConsole.svelte";
  import Dashboard from "./lib/Dashboard.svelte";
  import Settings from "./lib/Settings.svelte";

  let activeTab: AppTab = "studio";
  let health: ApiHealthStatus | null = null;
  let bootstrap: BootstrapStatus | null = null;
  let workflows: Workflow[] = [];
  let channelStatus: ChannelStatus | null = null;
  let selectedWorkflowId: number | null = null;
  let isCreatingWorkflow = false;
  let planningWorkflowId: number | null = null;
  let loading = false;

  function selectedWorkflowName(): string {
    if (selectedWorkflowId == null) return "none";
    return workflows.find((w) => w.id === selectedWorkflowId)?.name ?? "none";
  }

  async function runChecks() {
    loading = true;
    try {
      [health, bootstrap] = await Promise.all([
        invoke<ApiHealthStatus>("healthcheck"),
        invoke<BootstrapStatus>("bootstrap_status"),
      ]);
    } catch (e) {
      health = { api_state: "deconnectee", api_url: "http://127.0.0.1:8787", message: `Erreur Tauri: ${String(e)}` };
    } finally {
      loading = false;
    }
    try { workflows = await invoke<Workflow[]>("workflows_list"); } catch (_e) { /* empty */ }
    try { channelStatus = await invoke<ChannelStatus>("channels_status"); } catch (_e) { channelStatus = null; }
    if (selectedWorkflowId != null && !workflows.some((w) => w.id === selectedWorkflowId)) {
      selectedWorkflowId = null;
      isCreatingWorkflow = false;
    }
  }

  onMount(() => { void runChecks(); });
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
    <button class:active={activeTab === "planning"} on:click={() => (activeTab = "planning")}>Planning</button>
    <button class:active={activeTab === "dashboard"} on:click={() => (activeTab = "dashboard")}>Dashboard</button>
    <button class:active={activeTab === "settings"} on:click={() => (activeTab = "settings")}>Settings</button>
  </nav>

  {#if activeTab === "studio"}
    <WorkflowStudio bind:workflows {channelStatus} bind:selectedWorkflowId bind:isCreatingWorkflow bind:planningWorkflowId />
  {/if}

  {#if activeTab === "planning"}
    <PlanningConsole {workflows} bind:planningWorkflowId />
  {/if}

  {#if activeTab === "dashboard"}
    <Dashboard {health} {bootstrap} {workflows} {channelStatus} {loading} selectedWorkflowName={selectedWorkflowName()} onRefresh={runChecks} />
  {/if}

  {#if activeTab === "settings"}
    <Settings />
  {/if}
</main>

<style>
  .app-shell {
    max-width: 1220px;
    margin: 0 auto;
    padding: 1.4rem;
    color: var(--text-main);
    font-family: "Avenir Next", "Segoe UI", sans-serif;
  }
  .topbar { display: flex; justify-content: space-between; align-items: start; gap: 1rem; margin-bottom: 1rem; }
  h1 { margin: 0; display: flex; gap: 0.5rem; align-items: baseline; font-size: 1.55rem; letter-spacing: 0.01em; }
  .version { font-size: 0.88rem; color: var(--text-muted); font-weight: 500; }
  .subtitle { margin: 0.2rem 0 0; color: var(--text-muted); font-size: 0.92rem; }
  .badge { border: 1px solid var(--border); padding: 0.35rem 0.7rem; border-radius: 999px; color: var(--accent); background: rgba(78, 161, 255, 0.08); white-space: nowrap; font-size: 0.85rem; }
  .tabs { display: flex; gap: 0.55rem; margin: 1.1rem 0; }
  .tabs button { border: 1px solid var(--border); background: rgba(30, 39, 56, 0.8); color: var(--text-main); border-radius: 10px; padding: 0.58rem 0.95rem; cursor: pointer; font-size: 0.92rem; }
  .tabs button.active { background: linear-gradient(135deg, rgba(102, 214, 196, 0.22), rgba(78, 161, 255, 0.22)); border-color: var(--accent); }
  @media (max-width: 980px) {
    .topbar { flex-direction: column; align-items: start; }
    .tabs { width: 100%; overflow-x: auto; padding-bottom: 0.25rem; }
    .tabs button { white-space: nowrap; }
    .app-shell { padding: 1rem 0.8rem 1.2rem; }
  }
</style>
