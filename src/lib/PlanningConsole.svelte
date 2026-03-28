<!-- PlanningConsole.svelte — Planning & draft moderation tab -->
<script lang="ts">
  import { invoke } from "@tauri-apps/api/core";
  import { onMount } from "svelte";
  import type { Workflow, ScheduleDto, DraftDto, DraftListResponse } from "./types";
  import {
    invokeError, formatSlotDate, statusLabel, statusBadgeClass,
    slotScheduleTypeLabel, groupSlotsByDate,
  } from "./utils";

  export let workflows: Workflow[];
  export let planningWorkflowId: number | null;

  let planningLoading = false;
  let planningError = "";
  let planningSchedule: ScheduleDto | null = null;
  let planningNextSlots: string[] = [];
  let planningDrafts: DraftDto[] = [];
  let planningAbandonCount: number | null = null;
  let draftFilter: "all" | "pending" = "pending";

  $: filteredDrafts =
    draftFilter === "pending"
      ? planningDrafts.filter((d) => d.status === "pending_approval")
      : planningDrafts;

  async function loadPlanningData() {
    if (planningWorkflowId == null) return;
    planningLoading = true;
    planningError = "";
    planningAbandonCount = null;
    try {
      const [sched, slotsResp, draftsResp] = await Promise.all([
        invoke<ScheduleDto>("workflow_schedule_get", { workflowId: planningWorkflowId }),
        invoke<{ workflow_id: number; next_slots: string[] }>("workflow_schedule_next_slots", {
          workflowId: planningWorkflowId,
        }),
        invoke<DraftListResponse>("workflow_drafts_list", { workflowId: planningWorkflowId }),
      ]);
      planningSchedule = sched;
      planningNextSlots = slotsResp.next_slots;
      planningDrafts = draftsResp.items;
    } catch (e) {
      planningError = invokeError(e);
    } finally {
      planningLoading = false;
    }
  }

  async function approveDraft(draftId: number) {
    if (planningWorkflowId == null) return;
    planningError = "";
    try {
      await invoke("workflow_draft_approve", { workflowId: planningWorkflowId, draftId });
      await loadPlanningData();
    } catch (e) { planningError = invokeError(e); }
  }

  async function rejectDraft(draftId: number) {
    if (planningWorkflowId == null) return;
    planningError = "";
    try {
      await invoke("workflow_draft_reject", { workflowId: planningWorkflowId, draftId });
      await loadPlanningData();
    } catch (e) { planningError = invokeError(e); }
  }

  async function abandonStaleDrafts() {
    if (planningWorkflowId == null) return;
    planningLoading = true;
    planningAbandonCount = null;
    try {
      const result = await invoke<{ workflow_id: number; abandoned_count: number }>(
        "workflow_drafts_abandon_stale",
        { workflowId: planningWorkflowId },
      );
      planningAbandonCount = result.abandoned_count;
      await loadPlanningData();
    } catch (e) { planningError = invokeError(e); }
    finally { planningLoading = false; }
  }

  onMount(() => { void loadPlanningData(); });
</script>

<section class="card planning-console">
  <h2>Planning &amp; Modération</h2>
  <p class="muted">Vue des créneaux planifiés et file de validation des brouillons.</p>

  <div class="planning-toolbar">
    <label class="planning-select-label">
      Workflow
      <select
        bind:value={planningWorkflowId}
        on:change={() => { planningDrafts = []; planningNextSlots = []; planningSchedule = null; void loadPlanningData(); }}
      >
        <option value={null}>— Sélectionner un workflow —</option>
        {#each workflows as w}
          <option value={w.id}>{w.name}  ·  #{w.id}  ·  {w.is_active ? "actif" : "inactif"}</option>
        {/each}
      </select>
    </label>
    <button type="button" class="secondary" on:click={loadPlanningData} disabled={planningLoading || planningWorkflowId == null}>
      {planningLoading ? "Chargement..." : "↻ Actualiser"}
    </button>
  </div>

  {#if planningError}<p class="ko">{planningError}</p>{/if}

  {#if planningWorkflowId == null}
    <p class="muted planning-empty">Sélectionnez un workflow pour afficher son planning et ses brouillons.</p>
  {:else}
    <div class="planning-section">
      <h3 class="planning-section-title">
        ⏰ Créneaux à venir
        {#if planningSchedule}
          <span class="badge-status badge-info">{slotScheduleTypeLabel(planningSchedule.schedule_type)}</span>
          {#if planningSchedule.schedule_type !== "none"}
            <span class="badge-status badge-muted">{planningSchedule.timezone}</span>
          {/if}
        {/if}
      </h3>

      {#if !planningSchedule || planningSchedule.schedule_type === "none"}
        <p class="muted">Aucun scheduler configuré pour ce workflow.</p>
      {:else if planningNextSlots.length === 0}
        <p class="muted">Aucun créneau à venir (planification terminée ou non-définie).</p>
      {:else}
        <ul class="slots-calendar">
          {#each groupSlotsByDate(planningNextSlots) as group}
            <li class="slot-day">
              <span class="slot-day-label">{group.date}</span>
              <span class="slot-times">
                {#each group.times as t}<span class="slot-chip">{t}</span>{/each}
              </span>
            </li>
          {/each}
        </ul>
      {/if}
    </div>

    <div class="planning-section">
      <div class="draft-queue-header">
        <h3 class="planning-section-title" style="margin:0">📋 Brouillons ({planningDrafts.length})</h3>
        <div class="actions compact">
          <button type="button" class="secondary" on:click={abandonStaleDrafts} disabled={planningLoading}
            title="Marque comme abandonnés les brouillons en attente dont le slot suivant est passé">
            ⏳ Abandonner les obsolètes
          </button>
          {#if planningAbandonCount !== null}
            <span class="ok" style="font-size:0.86rem; align-self:center;">
              {planningAbandonCount} brouillon(s) abandonné(s).
            </span>
          {/if}
        </div>
      </div>

      <div class="draft-filter-tabs">
        <button type="button" class="filter-tab" class:active={draftFilter === "pending"}
          on:click={() => (draftFilter = "pending")}>
          En attente ({planningDrafts.filter((d) => d.status === "pending_approval").length})
        </button>
        <button type="button" class="filter-tab" class:active={draftFilter === "all"}
          on:click={() => (draftFilter = "all")}>
          Tous ({planningDrafts.length})
        </button>
      </div>

      {#if filteredDrafts.length === 0}
        <p class="muted">
          {draftFilter === "pending" ? "Aucun brouillon en attente de validation." : "Aucun brouillon pour ce workflow."}
        </p>
      {:else}
        <ul class="draft-list">
          {#each filteredDrafts as draft (draft.id)}
            <li class="draft-item">
              <div class="draft-item-header">
                <span class="badge-status {statusBadgeClass(draft.status)}">{statusLabel(draft.status)}</span>
                <span class="draft-id muted">#​{draft.id}</span>
                {#if draft.slot_iso}<span class="draft-slot muted">Slot : {formatSlotDate(draft.slot_iso)}</span>{/if}
                <span class="draft-date muted">{formatSlotDate(draft.created_at)}</span>
              </div>
              {#if draft.forbidden_words_matched.length > 0}
                <p class="draft-blocked-words">🚫 Mots interdits détectés : <strong>{draft.forbidden_words_matched.join(", ")}</strong></p>
              {/if}
              <div class="preview-dual preview-dual-sm">
                <div class="preview-dual-pane">
                  <h4>Journal</h4>
                  <pre>{draft.journal.slice(0, 280)}{draft.journal.length > 280 ? "…" : ""}</pre>
                </div>
                <div class="preview-dual-pane">
                  <h4>Post</h4>
                  <pre>{draft.post.slice(0, 280)}{draft.post.length > 280 ? "…" : ""}</pre>
                </div>
              </div>
              {#if draft.status === "pending_approval"}
                <div class="actions draft-actions">
                  <button type="button" class="approve-btn" on:click={() => approveDraft(draft.id)}>✓ Approuver</button>
                  <button type="button" class="secondary danger" on:click={() => rejectDraft(draft.id)}>✗ Refuser</button>
                </div>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  {/if}
</section>

<style>
  .planning-console { max-width: 100%; }
  .planning-toolbar { display: flex; gap: 0.6rem; align-items: flex-end; flex-wrap: wrap; margin-bottom: 1.2rem; }
  .planning-select-label { display: grid; gap: 0.26rem; font-size: 0.92rem; flex: 1 1 260px; min-width: 200px; }
  .planning-empty { margin-top: 1.5rem; text-align: center; font-size: 0.94rem; }
  .planning-section { margin-top: 1.4rem; border-top: 1px solid var(--border); padding-top: 0.9rem; }
  .planning-section-title { margin: 0 0 0.7rem; font-size: 0.96rem; color: #d8e2ff; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }

  .slots-calendar { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.55rem; }
  .slot-day { display: flex; align-items: flex-start; gap: 0.8rem; flex-wrap: wrap; padding: 0.5rem 0.7rem; border: 1px solid #2b354a; border-radius: 10px; background: rgba(10,14,22,0.4); }
  .slot-day-label { font-size: 0.88rem; color: var(--accent-2); font-weight: 600; white-space: nowrap; min-width: 170px; padding-top: 0.12rem; }
  .slot-times { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .slot-chip { background: rgba(78,161,255,0.12); border: 1px solid rgba(78,161,255,0.28); border-radius: 6px; padding: 0.22rem 0.5rem; font-size: 0.82rem; color: #c8d7ff; font-variant-numeric: tabular-nums; }

  .draft-queue-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.55rem; margin-bottom: 0.7rem; }
  .draft-filter-tabs { display: flex; gap: 0.35rem; margin-bottom: 0.8rem; }
  .filter-tab { background: rgba(71,87,117,0.22); border: 1px solid #4b607f; border-radius: 8px; padding: 0.32rem 0.72rem; font-size: 0.86rem; cursor: pointer; color: var(--text-muted); }
  .filter-tab.active { background: rgba(78,161,255,0.2); border-color: var(--accent-2); color: var(--text-main); }

  .draft-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.8rem; }
  .draft-item { border: 1px solid #33405b; border-radius: 12px; padding: 0.8rem; background: rgba(10,14,22,0.45); }
  .draft-item-header { display: flex; align-items: center; flex-wrap: wrap; gap: 0.45rem; margin-bottom: 0.45rem; }
  .draft-id { font-size: 0.82rem; }
  .draft-slot, .draft-date { font-size: 0.82rem; margin-left: auto; }
  .draft-blocked-words { font-size: 0.85rem; color: var(--ko); margin: 0.3rem 0; }
  .draft-actions { margin-top: 0.55rem; }
  .approve-btn { background: linear-gradient(135deg, rgba(47,208,140,0.28), rgba(47,208,140,0.12)); border-color: rgba(47,208,140,0.5); }
  .approve-btn:hover { background: linear-gradient(135deg, rgba(47,208,140,0.4), rgba(47,208,140,0.2)); }
</style>
