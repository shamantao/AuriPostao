<!-- Settings.svelte — Read-only configuration view -->
<script lang="ts">
  import { defaultTomlText } from "./utils";
</script>

<section class="card">
  <h2>Settings</h2>
  <p class="muted">
    Read-only view of the default configuration. Settings CRUD is intentionally postponed.
  </p>
  <pre class="toml-block">{defaultTomlText}</pre>
</section>

<style>
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
</style>
