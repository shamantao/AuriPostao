import type { DraftStatus } from "./types";

export function invokeError(e: unknown): string {
  if (typeof e === "string") return e;
  return `Erreur Tauri: ${String(e)}`;
}

export function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function dedupePaths(paths: string[]): string[] {
  return [...new Set(paths)];
}

export function formatSlotDate(iso: string): string {
  try {
    return (
      new Date(iso).toLocaleString("fr-FR", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "UTC",
      }) + " UTC"
    );
  } catch {
    return iso;
  }
}

export function statusLabel(status: DraftStatus): string {
  const map: Record<DraftStatus, string> = {
    pending_approval: "En attente",
    approved: "Approuvé",
    rejected: "Refusé",
    abandoned: "Abandonné",
    blocked_confidentiality: "Bloqué (confidentialité)",
  };
  return map[status] ?? status;
}

export function statusBadgeClass(status: DraftStatus): string {
  const map: Record<DraftStatus, string> = {
    pending_approval: "badge-pending",
    approved: "badge-ok",
    rejected: "badge-ko",
    abandoned: "badge-muted",
    blocked_confidentiality: "badge-blocked",
  };
  return map[status] ?? "";
}

export function slotScheduleTypeLabel(stype: string): string {
  const map: Record<string, string> = {
    none: "Aucun",
    one_shot: "Ponctuel",
    daily: "Quotidien",
    weekly: "Hebdomadaire",
    monthly: "Mensuel",
  };
  return map[stype] ?? stype;
}

export function groupSlotsByDate(
  slots: string[],
): Array<{ date: string; times: string[] }> {
  const grouped: Record<string, string[]> = {};
  for (const iso of slots) {
    try {
      const d = new Date(iso);
      const dateKey = d.toLocaleDateString("fr-FR", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
        timeZone: "UTC",
      });
      const timeStr =
        d.toLocaleTimeString("fr-FR", {
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "UTC",
        }) + " UTC";
      (grouped[dateKey] ??= []).push(timeStr);
    } catch {
      (grouped[iso] ??= []).push(iso);
    }
  }
  return Object.entries(grouped).map(([date, times]) => ({ date, times }));
}

export function formatGenerationError(
  errType: string | null,
  errMsg: string | null,
  aiModel: string,
  aiBaseUrl: string,
  aiTimeout: number,
): string {
  const base = `${errType}: ${errMsg ?? "unknown error"}`;
  if (errMsg?.includes("timed out") || errMsg?.includes("Request timed out"))
    return `${base} — Try a smaller model, or increase Timeout (current: ${aiTimeout}s).`;
  if (errMsg?.includes("404"))
    return `${base} — Check Base URL and model name ("${aiModel}").`;
  if (errMsg?.includes("connect") || errMsg?.includes("unreachable"))
    return `${base} — Is the provider running at ${aiBaseUrl}?`;
  if (errMsg?.includes("HTTP 500"))
    return `${base} — The provider returned an internal error (model loading or out of memory). AuriPostao retried 3x automatically.`;
  return base;
}

export const defaultTomlText = `# AuriPostao - Default Configuration
# Template version: 1.0.0
#
# Layer priority (highest wins):
#   default (this file) -> user (~/.config/auripostao/user.toml)
#   -> config/config.toml (local machine, git-ignored)
#   -> runtime (env vars APP__ prefix)
#
# For local overrides (paths, secrets): copy values into config/config.toml (git-ignored).

[app]
name       = "AuriPostao"
version    = "0.1.0"
mode       = "debug"   # debug | normal
language   = "fr"

[config]
schema_version       = 1
enable_layered_merge = true
strict_mode          = false

[path_manager]
allowed_roots = []
temp_dir    = ".tmp"
logs_dir    = "logs"
reports_dir = "reports"
collision_strategy = "increment"   # increment | suffix | short_hash
normalize_unicode  = false
trim_whitespace    = true

[logger]
level          = "info"   # trace | debug | info | warn | error
console_pretty = true
file_json      = true
rotation_enabled = true
max_file_mb      = 20
max_files        = 5
include_context_ids = true

[reporting]
enabled        = true
json_report    = true
csv_report     = true
include_failed = true`;
