# Code Constraints & Quality Checks

## Overview
AuriPostao enforces architectural constraints via automated tests to maintain code quality and team standards:

| Check | Goal | Limit | Status |
|-------|------|-------|--------|
| **File size (Python/Rust)** | Keep modules focused | ≤ 400 lines | ✅ Enforced |
| **No hardcoded paths** | Use path manager for portability | 0 violations | ✅ Enforced |
| **Unified logging** | Single logger, no print/println | All logs via logger | ✅ Enforced |
| **Path manager usage** | Centralized path handling | Suggested improvement | ⚠️ Informational |

## Execution

**Manually:**
```bash
bash scripts/test-constraints.sh
```

**In Pipeline:**
- Runs automatically in `test-unit-fast.sh`
- Runs in full suite via `test-unit.sh`

## Current Exemptions (Technical Debt)

### `core/api/main.py` (1952 lines)
**Issue:** Main API orchestration file is too large
**Debt:** Should be refactored into modules by functional domain
**Proposed Structure:**
```
core/api/
  main.py              (entry point only, ~50 lines)
  models.py            (Pydantic models)
  database.py          (SQLite operations)
  workflows.py         (CRUD + business logic)
  channels.py          (Channel management)
  scheduling.py        (Scheduler operations)
  generation.py        (AI generation + validation)
  ingestion.py         (File ingestion)
  confidentiality.py    (Content filtering)
```

**Migration Path:**
1. Extract modules one at a time
2. Keep existing unit tests passing
3. Update imports in main.py
4. Submit as multi-step refactor PR
5. Remove exemption when complete

### `src-tauri/src/main.rs` (1200 lines)
**Issue:** Tauri app initialization and IPC handlers mixed in one file
**Debt:** Should split into separate command handlers
**Proposed Structure:**
```
src-tauri/src/
  main.rs              (app init only, ~200 lines)
  commands/
    mod.rs             (command module registry)
    workflow.rs        (workflow IPC handlers)
    scheduler.rs       (scheduler IPC handlers)
    generation.rs      (AI generation handlers)
    ingestion.rs       (file ingestion handlers)
```

**Migration Path:**
1. Create `commands/` submodule
2. Extract command handlers incrementally
3. Ensure Tauri invocation paths still work
4. Test IPC with existing frontend code
5. Remove exemption when complete

## Path Manager Usage Warnings

### Issue: Direct PathBuf Creation
Some files use `PathBuf::from()` directly instead of the centralized path manager.

**Files affected:**
- `src-tauri/src/config.rs` — Default config paths
- `src-tauri/src/api_process.rs` — Subprocess path handling

**Solution:**
Use existing functions from `src-tauri/src/paths.rs`:

```rust
// ❌ Before
let logs_dir = PathBuf::from("/tmp/logs");

// ✅ After (use path manager)
let logs_dir = paths::ensure_within_allowed("/tmp/logs")?;
// or
let logs_dir = paths::get_logs_directory()?;
```

**Benefits:**
- Single place to update path logic
- Ensures all paths go through security checks (`ensure_within_allowed`)
- Portable across environments

## Logging Constraints

### No Direct print() in Python
```python
# ❌ Bad
print("Processing workflow")

# ✅ Good
import logging
logger = logging.getLogger(__name__)
logger.info("Processing workflow")
```

### No Direct println! in Rust
```rust
// ❌ Bad (except in main.rs for startup)
println!("Starting API on port {}", port);

// ✅ Good
use log::info;
info!("Starting API on port {}", port);
```

## How to Add New Constraints

Constraints are defined in `tests/test_code_constraints.py`:

```python
# Example: Add new regex-based file check
def test_no_unwrap_in_rust(self):
    """Rust should use Result types carefully."""
    violations = []
    for rs_file in self.rs_files:
        content = rs_file.read_text()
        # Find unwrap() calls outside tests
        if '.unwrap()' in content:
            # Add to violations list
            violations.append(...)
    
    if violations:
        self.fail(msg)
```

Run tests after adding:
```bash
python3 -m pytest tests/test_code_constraints.py::CodeConstraintTests::test_no_unwrap_in_rust -v
```

## Future Improvements

- [ ] **Complexity checks**: Detect functions with high cyclomatic complexity
- [ ] **Dependency analysis**: Ensure modules don't create circular dependencies
- [ ] **Test coverage requirements**: Enforce minimum coverage per module
- [ ] **Comment ratio**: Suggest adding comments for complex sections
- [ ] **Performance markers**: Flag potentially slow operations (heavy loops, N+1 queries)

## References

- [ARCHITECTURE.md](ARCHITECTURE.md) — Full architecture guidelines
- [TEST_STRATEGY.md](TEST_STRATEGY.md) — Testing approach and gaps
- [src-tauri/src/paths.rs](../src-tauri/src/paths.rs) — Path manager API
