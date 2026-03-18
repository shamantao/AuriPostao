<!-- App.svelte — Minimal front-end entry point -->
<!-- Generated from tao-init v1.0.0 (tauri-rust adapter) -->
<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";

  let status = "idle";

  async function healthcheck() {
    try {
      status = await invoke("healthcheck");
    } catch (e) {
      status = `Error: ${e}`;
    }
  }
</script>

<main>
  <h1>AuriPostao_tao_seed</h1>
  <p>Status: {status}</p>
  <button on:click={healthcheck}>Healthcheck</button>
</main>

<style>
  main {
    font-family: system-ui, sans-serif;
    max-width: 800px;
    margin: 2rem auto;
    padding: 1rem;
  }
</style>
