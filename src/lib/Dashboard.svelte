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
    if (health?.api_state === "connectee") return "connectée";
    if (health?.api_state === "deconnectee") return "déconnectée";
    return "inconnue";
  }

  async function setDummyChannel(enabled: boolean) {
    channelsError = "";
    try {
      channelStatus = await invoke<ChannelStatus>("channels_set_dummy", {
        payload: { enabled },
      });
      workflowsInfo = enabled ? "Canal dummy activé." : "Canal dummy désactivé.";
    } catch (e) {
      channelsError = invokeError(e);
    }
  }
</script>

<section class="grid-three">
  <article class="card metric">
    <h2>Connexions</h2>
    <p>API : <strong class={health?.api_state === "connectee" ? "ok" : "ko"}>{apiStateLabel()}</strong></p>
    <p class="muted">Endpoint : {health?.api_url ?? "http://127.0.0.1:8787"}</p>
    <p class="muted">Message : {health?.message ?? "-"}</p>
  </article>

  <article class="card metric">
    <h2>État du système</h2>
    <p>Service : <strong>{health?.service || "n/a"}</strong></p>
    <p>Version API : <strong>{health?.version || "n/a"}</strong></p>
    <p class="muted">UTC : {health?.time_utc || "n/a"}</p>
  </article>

  <article class="card metric">
    <h2>Base de données</h2>
    <p>Statut : <strong class={bootstrap?.db_exists ? "ok" : "warn"}>{bootstrap?.db_exists ? "détectée" : "manquante"}</strong></p>
    <p class="muted">Chemin : {bootstrap?.db_path ?? "..."}</p>
  </article>

  <article class="card metric">
    <h2>Workflows</h2>
    <p>Total : <strong>{workflows.length}</strong></p>
    <p>Actifs : <strong>{workflows.filter((w) => w.is_active).length}</strong></p>
    <p>Contexte ouvert : <strong>{selectedWorkflowName}</strong></p>
  </article>

  <article class="card metric">
    <h2>Canaux</h2>
    <p>Valides : <strong>{channelStatus?.valid_channels?.length ?? 0}</strong></p>
    <p class="muted">{channelStatus?.valid_channels?.join(", ") || "aucun"}</p>
    {#if workflowsInfo}<p class="ok">{workflowsInfo}</p>{/if}
    <div class="actions compact">
      <button type="button" on:click={() => setDummyChannel(true)}>Activer dummy</button>
      <button type="button" class="secondary" on:click={() => setDummyChannel(false)}>Désactiver</button>
    </div>
    {#if channelsError}<p class="ko">{channelsError}</p>{/if}
  </article>

  <article class="card metric">
    <h2>Contrôle</h2>
    <p class="muted">Actualise tous les états d'exécution et les métriques affichées.</p>
    <button on:click={onRefresh} disabled={loading}>
      {#if loading}Vérification...{:else}Actualiser le tableau de bord{/if}
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
