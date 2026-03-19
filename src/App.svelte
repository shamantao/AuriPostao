<!-- App.svelte — Minimal front-end entry point -->
<!-- Generated from tao-init v1.0.0 (tauri-rust adapter) -->
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

  let status: ApiHealthStatus | null = null;
  let loading = false;

  async function healthcheck() {
    loading = true;
    try {
      status = await invoke<ApiHealthStatus>("healthcheck");
    } catch (e) {
      status = {
        api_state: "deconnectee",
        api_url: "http://127.0.0.1:8787",
        message: `Erreur Tauri: ${String(e)}`,
      };
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    void healthcheck();
  });
</script>

<main>
  <h1>AuriPostao</h1>
  <p>
    Etat API:
    <strong class={status?.api_state === "connectee" ? "ok" : "ko"}>
      {status?.api_state ?? "inconnu"}
    </strong>
  </p>
  <p>Endpoint: {status?.api_url ?? "http://127.0.0.1:8787"}</p>
  <p>Message: {status?.message ?? "Aucun test lance"}</p>
  {#if status?.service}
    <p>Service: {status.service}</p>
  {/if}
  {#if status?.version}
    <p>Version API: {status.version}</p>
  {/if}
  {#if status?.time_utc}
    <p>Horodatage API: {status.time_utc}</p>
  {/if}
  <button on:click={healthcheck} disabled={loading}>
    {#if loading}Verification...{:else}Relancer le healthcheck{/if}
  </button>
</main>

<style>
  main {
    font-family: system-ui, sans-serif;
    max-width: 800px;
    margin: 2rem auto;
    padding: 1rem;
  }
  .ok {
    color: #0a7d2d;
  }
  .ko {
    color: #b12020;
  }
</style>
