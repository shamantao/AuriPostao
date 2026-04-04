<!-- GenerationBlock.svelte — Block 6: AI config, voice criteria & generation -->
<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import { onMount } from "svelte";
  import type { AiConfig, VoiceCriteria, GenerationResult, GenerationHistoryEntry } from "./types";
  import { invokeError, formatGenerationError } from "./utils";

  export let selectedWorkflowId: number | null;
  export let isCreatingWorkflow: boolean;

  let aiProvider = "ollama";
  let aiBaseUrl = "http://localhost:11434";
  let aiModel = "mistral";
  let aiTimeout = 60;
  let voicePreset = "professional_concise";
  let voiceCustomInstructions = "";
  let voiceMinLength = 50;
  let voiceMaxLength = 300;
  let generationLoading = false;
  let generationError = "";
  let generationInfo = "";
  let generationResult: GenerationResult | null = null;
  let generationHistory: GenerationHistoryEntry[] = [];
  let genConfigSaving = false;
  let genConfigSaved = false;
  let genElapsed = 0;
  let _genTimer: ReturnType<typeof setInterval> | null = null;

  async function loadGenerationConfig() {
    if (selectedWorkflowId == null) return;
    try {
      const ac = await invoke<AiConfig>("workflow_ai_config_get", { workflowId: selectedWorkflowId });
      aiProvider = ac.provider;
      aiBaseUrl = ac.base_url;
      aiModel = ac.model;
      aiTimeout = ac.timeout_seconds;
    } catch (_e) { /* keep defaults */ }
    try {
      const vc = await invoke<VoiceCriteria>("workflow_voice_criteria_get", { workflowId: selectedWorkflowId });
      voicePreset = vc.preset;
      voiceCustomInstructions = vc.custom_instructions;
      voiceMinLength = vc.min_length;
      voiceMaxLength = vc.max_length;
    } catch (_e) { /* keep defaults */ }
  }

  async function saveGenerationConfig() {
    if (selectedWorkflowId == null) return;
    genConfigSaving = true;
    genConfigSaved = false;
    generationError = "";
    try {
      await invoke("workflow_ai_config_set", {
        workflowId: selectedWorkflowId,
        payload: { provider: aiProvider, base_url: aiBaseUrl, model: aiModel, timeout_seconds: aiTimeout },
      });
      await invoke("workflow_voice_criteria_set", {
        workflowId: selectedWorkflowId,
        payload: { preset: voicePreset, custom_instructions: voiceCustomInstructions, min_length: voiceMinLength, max_length: voiceMaxLength },
      });
      genConfigSaved = true;
      setTimeout(() => { genConfigSaved = false; }, 3000);
    } catch (e) {
      generationError = invokeError(e);
    } finally {
      genConfigSaving = false;
    }
  }

  function onProviderChange() {
    const DEFAULTS: Record<string, string> = {
      ollama: "http://localhost:11434",
      openai_compat: "http://localhost:8200/v1",
    };
    if (!aiBaseUrl || Object.values(DEFAULTS).includes(aiBaseUrl))
      aiBaseUrl = DEFAULTS[aiProvider] ?? aiBaseUrl;
  }

  async function runGeneration() {
    if (selectedWorkflowId == null) return;
    generationLoading = true;
    generationError = "";
    generationInfo = "";
    genElapsed = 0;
    _genTimer = setInterval(() => { genElapsed += 1; }, 1000);
    try {
      const result = await invoke<GenerationResult>("workflow_generate", { workflowId: selectedWorkflowId });
      if (!result.error_type) {
        generationResult = result;
        generationHistory = [
          { timestamp: new Date().toLocaleTimeString(), journal: result.journal, post: result.post, provider: result.provider, model: result.model },
          ...generationHistory,
        ].slice(0, 3);
        const draftNote = result.draft_id != null
          ? result.draft_status === "pending_approval"
            ? ` Brouillon #${result.draft_id} en attente de validation — voir l'onglet Planning.`
            : ` Brouillon #${result.draft_id} approuvé automatiquement.`
          : "";
        generationInfo = `Génération terminée en ${genElapsed}s.${draftNote}`;
      } else if (result.error_type === "blocked_confidentiality") {
        const words = result.error_message?.replace("blocked: ", "") ?? "";
        generationError = `Contenu bloqué — mots interdits : ${words}.${
          result.draft_id != null ? ` Brouillon #${result.draft_id} sauvegardé comme bloqué.` : ""
        } Voir l'onglet Planning.`;
      } else {
        generationError = formatGenerationError(result.error_type, result.error_message, aiModel, aiBaseUrl, aiTimeout);
      }
    } catch (e) {
      generationError = invokeError(e);
    } finally {
      if (_genTimer) { clearInterval(_genTimer); _genTimer = null; }
      generationLoading = false;
    }
  }

  onMount(() => { void loadGenerationConfig(); });
</script>

<div class="preview-box generation-block">
  <h3>Bloc 6. Génération</h3>

  {#if isCreatingWorkflow}
    <p class="warn">Sauvegardez d'abord le workflow pour activer la génération.</p>
  {:else}
    <h4>Fournisseur IA</h4>
    <div class="gen-config-grid">
      <label>
        Fournisseur
        <select bind:value={aiProvider} on:change={onProviderChange}>
          <option value="ollama">Ollama (local)</option>
          <option value="openai_compat">OpenAI-compatible</option>
        </select>
      </label>
      <label>
        Base URL
        <input bind:value={aiBaseUrl} placeholder="http://localhost:11434" />
      </label>
      <label>
        Model
        <input bind:value={aiModel}
          placeholder={aiProvider === "ollama" ? "mistral, qwen3-vl:2b..." : "gpt-4o-mini, mistral..."} />
      </label>
      <label>
        Timeout (s)
        <input type="number" min="5" max="600" step="5" bind:value={aiTimeout} />
      </label>
    </div>

    <h4>Critères de voix</h4>
    <div class="gen-config-grid">
      <label>
        Style prédéfini
        <select bind:value={voicePreset}>
          <option value="professional_concise">Professional — Concise</option>
          <option value="professional_detailed">Professional — Detailed</option>
          <option value="casual">Casual</option>
          <option value="storytelling">Storytelling</option>
          <option value="technical">Technical</option>
          <option value="custom">Custom</option>
        </select>
      </label>
      <label>
        Longueur min (mots)
        <input type="number" min="1" step="10" bind:value={voiceMinLength} />
      </label>
      <label>
        Longueur max (mots)
        <input type="number" min="2" step="10" bind:value={voiceMaxLength} />
      </label>
    </div>

    {#if voicePreset === "custom"}
      <label style="display:grid; gap:0.28rem; margin-top:0.4rem; font-size:0.92rem;">
        Instructions personnalisées
        <textarea bind:value={voiceCustomInstructions} rows="3" placeholder="Écrivez sur un ton conversationnel..." />
      </label>
    {/if}

    <div class="actions" style="margin-top:0.6rem;">
      <button type="button" class="secondary" on:click={saveGenerationConfig} disabled={genConfigSaving}>
        {genConfigSaving ? "Enregistrement..." : "Enregistrer la configuration"}
      </button>
      {#if genConfigSaved}<span class="ok" style="font-size:0.88rem; align-self:center;">Configuration enregistrée.</span>{/if}
    </div>

    <div class="gen-divider"></div>

    <div class="actions">
      <button type="button" on:click={runGeneration} disabled={generationLoading}>
        {generationLoading ? `Génération... ${genElapsed}s` : "Générer"}
      </button>
      {#if generationResult && !generationLoading}
        <button type="button" class="secondary" on:click={runGeneration} disabled={generationLoading}>
          Régénérer
        </button>
      {/if}
    </div>
    <p class="muted">
      {generationLoading
        ? "L'application est active — la génération fonctionne en arrière-plan."
        : "La génération peut prendre 30–120 s selon la taille du modèle et le matériel."}
    </p>

    {#if generationError}<p class="ko">{generationError}</p>{/if}
    {#if generationInfo}<p class="ok">{generationInfo}</p>{/if}

    {#if generationResult}
      <div class="preview-dual">
        <div class="preview-dual-pane">
          <h4>Entrée journal</h4>
          <pre>{generationResult.journal ?? ""}</pre>
        </div>
        <div class="preview-dual-pane">
          <h4>Post social</h4>
          <pre>{generationResult.post ?? ""}</pre>
        </div>
      </div>
      <p class="muted gen-meta">Généré par {generationResult.provider} / {generationResult.model}</p>
    {/if}

    {#if generationHistory.length > 0}
      <h4>Générations récentes ({generationHistory.length})</h4>
      <ul class="gen-history">
        {#each generationHistory as entry, i}
          <li>
            <p class="muted gen-history-meta">#{generationHistory.length - i} — {entry.timestamp} — {entry.provider}/{entry.model}</p>
            <div class="preview-dual preview-dual-sm">
              <div class="preview-dual-pane"><pre>{entry.journal ?? ""}</pre></div>
              <div class="preview-dual-pane"><pre>{entry.post ?? ""}</pre></div>
            </div>
          </li>
        {/each}
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
  .generation-block { margin-top: 1rem; }
  .gen-divider { border-top: 1px solid #33405b; margin: 0.8rem 0; }
  .gen-meta { font-size: 0.8rem; margin-top: 0.4rem; }
  .gen-history { list-style: none; margin: 0.5rem 0 0; padding: 0; display: grid; gap: 0.8rem; }
  .gen-history li { border: 1px solid #33405b; border-radius: 8px; padding: 0.6rem; background: rgba(10, 14, 22, 0.35); }
  .gen-history-meta { margin: 0 0 0.4rem; font-size: 0.82rem; }
</style>
