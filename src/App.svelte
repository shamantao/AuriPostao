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

  let health: ApiHealthStatus | null = null;
  let bootstrap: BootstrapStatus | null = null;
  let loading = false;

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
  .ok   { color: #0a7d2d; }
  .ko   { color: #b12020; }
  .warn { color: #a06000; }
  button {
    margin-top: 0.5rem;
    padding: 0.5rem 1.2rem;
    font-size: 0.95rem;
    cursor: pointer;
  }
</style>
