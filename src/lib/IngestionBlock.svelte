<!-- IngestionBlock.svelte — Block 5: Pre-run ingestion validation -->
<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import type { IngestionPreview, WorkflowSourcesConfig } from "./types";
  import { invokeError, formatBytes } from "./utils";

  export let selectedWorkflowId: number | null;
  export let isCreatingWorkflow: boolean;
  export let sourceFiles: string[];
  export let sourceDirectory: string;
  export let includeSubdirs: boolean;
  export let maxFileSizeBytes: number;

  let ingestionLoading = false;
  let ingestionError = "";
  let ingestionInfo = "";
  let ingestionWarning = "";
  let ingestionPreview: IngestionPreview | null = null;

  export function reset() {
    ingestionPreview = null;
    ingestionError = "";
    ingestionInfo = "";
    ingestionWarning = "";
  }

  async function runIngestionPreview() {
    ingestionError = "";
    ingestionWarning = "";
    ingestionInfo = "";
    ingestionPreview = null;

    if (isCreatingWorkflow || selectedWorkflowId == null) {
      ingestionError = "Sauvegardez d'abord le workflow avant de tester l'ingestion.";
      return;
    }
    if (sourceFiles.length === 0 && !sourceDirectory) {
      ingestionError = "Aucune source configurée dans ce workflow.";
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
      if (tooLargeFiles.length > 0)
        ingestionWarning = `${tooLargeFiles.length} fichier(s) dépassent la taille limite (${formatBytes(maxFileSizeBytes)} max par fichier).`;
      if (ingestionPreview.summary.accepted === 0)
        ingestionError += "\nAucune source valide détectée. Ajoutez au moins un fichier texte lisible (.txt/.md) sous la taille limite.";
      else
        ingestionInfo = "Aperçu d'ingestion généré pour ce workflow.";
    } catch (e) {
      ingestionError = invokeError(e);
    } finally {
      ingestionLoading = false;
    }
  }
</script>

<div class="preview-box">
  <h3>Bloc 5. Validation pré-exécution</h3>
  <div class="actions">
    <button type="button" on:click={runIngestionPreview} disabled={ingestionLoading}>
      {#if ingestionLoading}Ingestion en cours...{:else}Tester l'ingestion{/if}
    </button>
  </div>

  {#if ingestionError}<p class="ko">{ingestionError}</p>{/if}
  {#if ingestionWarning}<p class="warn">{ingestionWarning}</p>{/if}
  {#if ingestionInfo}<p class="ok">{ingestionInfo}</p>{/if}

  {#if ingestionPreview}
    <p>
      Résumé : {ingestionPreview.summary.accepted} accepté(s), {ingestionPreview.summary.ignored} ignoré(s),
      {ingestionPreview.summary.errors} erreur(s), {ingestionPreview.summary.total_candidates} candidat(s),
      taille totale {formatBytes(ingestionPreview.summary.total_size_bytes)}
    </p>
    {#if ingestionPreview.accepted_files.length > 0}
      <h4>Échantillons de contenu</h4>
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
      <h4>Fichiers ignorés</h4>
      <ul class="source-list">
        {#each ingestionPreview.ignored_files as item}<li>{item.path} - {item.reason}</li>{/each}
      </ul>
    {/if}
    {#if ingestionPreview.errors.length > 0}
      <h4>Erreurs</h4>
      <ul class="source-list">
        {#each ingestionPreview.errors as item}<li>{item.path} - {item.reason}</li>{/each}
      </ul>
    {/if}
  {/if}
</div>

<style>
  .preview-box {
    margin-top: 1rem;
    border: 1px solid #33405b;
    border-radius: 10px;
    padding: 0.8rem;
    background: rgba(10, 14, 22, 0.55);
  }
  .source-list { margin: 0.4rem 0; padding-left: 1.15rem; display: grid; gap: 0.35rem; }
</style>
