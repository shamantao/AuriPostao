// paths.rs — Path manager module
// Centralizes ALL path logic. No other module should build paths directly.

use std::path::{Path, PathBuf};

use crate::config::AppConfig;
use crate::errors::AppError;

// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct RuntimePaths {
    pub temp_dir:    PathBuf,
    pub logs_dir:    PathBuf,
    pub reports_dir: PathBuf,
}

// ---------------------------------------------------------------------------

/// Build, validate, and create all required runtime directories.
pub fn build(cfg: &AppConfig) -> Result<RuntimePaths, AppError> {
    let pm = &cfg.path_manager;

    let temp_dir    = normalize(&pm.temp_dir);
    let logs_dir    = normalize(&pm.logs_dir);
    let reports_dir = normalize(&pm.reports_dir);

    create_dir_safe(&temp_dir,    &pm.allowed_roots)?;
    create_dir_safe(&logs_dir,    &pm.allowed_roots)?;
    create_dir_safe(&reports_dir, &pm.allowed_roots)?;

    Ok(RuntimePaths { temp_dir, logs_dir, reports_dir })
}

/// Resolve a candidate output path, applying the collision strategy.
pub fn resolve_output(
    source:     &Path,
    output_dir: &Path,
    extension:  &str,
    strategy:   &str,
) -> Result<PathBuf, AppError> {
    let stem = source
        .file_stem()
        .ok_or_else(|| AppError::Path("source has no file stem".into()))?
        .to_string_lossy();

    let candidate = output_dir.join(format!("{stem}.{extension}"));

    if !candidate.exists() {
        return Ok(candidate);
    }

    // Collision: apply strategy
    match strategy {
        "increment" => {
            for i in 1u32.. {
                let p = output_dir.join(format!("{stem}_{i:03}.{extension}"));
                if !p.exists() {
                    return Ok(p);
                }
            }
            Err(AppError::Path("collision increment overflow".into()))
        }
        "suffix" => {
            let ts = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_secs())
                .unwrap_or(0);
            Ok(output_dir.join(format!("{stem}_{ts}.{extension}")))
        }
        "short_hash" => {
            use std::collections::hash_map::DefaultHasher;
            use std::hash::{Hash, Hasher};
            let mut h = DefaultHasher::new();
            source.hash(&mut h);
            let hash = format!("{:08x}", h.finish());
            Ok(output_dir.join(format!("{stem}_{hash}.{extension}")))
        }
        other => Err(AppError::Path(format!("unknown collision strategy: {other}"))),
    }
}

/// Ensure a path is inside at least one of the allowed roots (path traversal guard).
pub fn ensure_within_allowed(path: &Path, allowed_roots: &[PathBuf]) -> Result<(), AppError> {
    let canonical = path
        .canonicalize()
        .unwrap_or_else(|_| path.to_path_buf());

    for root in allowed_roots {
        let root_canonical = root.canonicalize().unwrap_or_else(|_| root.clone());
        if canonical.starts_with(&root_canonical) {
            return Ok(());
        }
    }

    Err(AppError::Path(format!(
        "path '{}' is outside allowed roots",
        path.display()
    )))
}

// ---------------------------------------------------------------------------
// Helpers

fn normalize(p: &Path) -> PathBuf {
    if p.is_absolute() {
        p.to_path_buf()
    } else {
        std::env::current_dir()
            .unwrap_or_default()
            .join(p)
    }
}

fn create_dir_safe(dir: &Path, allowed_roots: &[PathBuf]) -> Result<(), AppError> {
    // The parent must exist or be within an allowed root before we create.
    if !dir.exists() {
        if let Some(parent) = dir.parent() {
            // Heuristic: if parent doesn't exist either, check allowed roots
            if !parent.exists() {
                ensure_within_allowed(dir, allowed_roots)?;
            }
        }
        std::fs::create_dir_all(dir)
            .map_err(|e| AppError::Path(format!("cannot create {}: {e}", dir.display())))?;
    }
    Ok(())
}

// ---------------------------------------------------------------------------
#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn resolve_output_increment_on_collision() {
        let dir = tempdir().unwrap();
        let source = dir.path().join("movie.mkv");

        // Create a collision
        std::fs::write(dir.path().join("movie.mp4"), b"").unwrap();

        let out = resolve_output(&source, dir.path(), "mp4", "increment").unwrap();
        assert_eq!(out.file_name().unwrap(), "movie_001.mp4");
    }

    #[test]
    fn ensure_within_allowed_rejects_escape() {
        let allowed = vec![PathBuf::from("/tmp/safe")];
        let bad = PathBuf::from("/etc/passwd");
        assert!(ensure_within_allowed(&bad, &allowed).is_err());
    }
}
