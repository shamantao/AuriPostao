<!-- Dashboard.svelte — System status, metrics, channel toggle -->
<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import type { ApiHealthStatus, BootstrapStatus, Workflow, ChannelStatus } from "./types";
  import { invokeError } from "./utils";

  export let health: ApiHealthStatus | null;
  export let bootstrap: BootstrapStatus | null;
  export let workflows: Workflow[];
  export let channelStatus: ChannelStatus | null;
  export let loading: boolean;
  export let selectedWorkflowName: string;
  export let onRefresh: () => void;

  let channelsError = "";
  let workflowsInfo = "";

  function apiStateLabel(): string {
    if (health?.api_state === "connectee") return "connected";
    if (health?.api_state === "deconnectee") return "disconnected";
    return "unknown";
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
</script>

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
    <p>Opened context: <strong>{selectedWorkflowName}</strong></p>
  </article>

  <article class="card metric">
    <h2>Channels</h2>
    <p>Valid: <strong>{channelStatus?.valid_channels?.length ?? 0}</strong></p>
    <p class="muted">{channelStatus?.valid_channels?.join(", ") || "none"}</p>
    {#if workflowsInfo}<p class="ok">{workflowsInfo}</p>{/if}
    <div class="actions compact">
      <button type="button" on:click={() => setDummyChannel(true)}>Enable dummy</button>
      <button type="button" class="secondary" on:click={() => setDummyChannel(false)}>Disable</button>
    </div>
    {#if channelsError}<p class="ko">{channelsError}</p>{/if}
  </article>

  <article class="card metric">
    <h2>Control</h2>
    <p class="muted">Refreshes all runtime states and displayed metrics.</p>
    <button on:click={onRefresh} disabled={loading}>
      {#if loading}Checking...{:else}Refresh dashboard{/if}
    </button>
  </article>
</section>

<style>
  .grid-three {
    display: grid;
    grid-template-columns: repeat(3, minmax(220px, 1fr));
    gap: 1rem;
  }
  .metric p { margin: 0.3rem 0; }
</style>
