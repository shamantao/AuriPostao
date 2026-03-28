# Test Strategy - AuriPostao

## Problem: Why Unit Tests Don't Catch Application Startup Failures

The previous test failures highlighted a critical gap in test coverage:
- ✅ All 85 Python + 6 Rust **unit tests** passed
- ✅ All **lint checks** passed  
- ✅ All **API integration tests** passed
- ❌ But `./auripostao.sh` **failed to start** due to stale Cargo build cache

### Root Cause
The issue was a stale build artifact path from the old Dropbox workspace location. This occurred because:

1. **Unit tests** use an isolated Cargo cache (`src-tauri/target/test-cache`) that doesn't accumulate old artifacts
2. The **real Tauri build** (`tauri dev`) uses the default Cargo cache which retained references to the old workspace path
3. **Isolation strategy** fixed tests but left the production build broken

This is why unit tests passed but the application wouldn't start.

## Test Coverage Breakdown

| Test Suite | What It Tests | What It DOESN'T Test |
|-----------|---------------|---------------------|
| **unit-fast.sh** | Code constraints + Python API unit tests + Rust component tests | Full Tauri/React startup, real build artifacts |
| **unit.sh** | Same as unit-fast (full verbosity) | End-to-end application flow |
| **lint.sh** | Code formatting (rustfmt, black) | Functionality or build success |
| **integration-light.sh** | API health check + core endpoint smoke tests | UI/Frontend layer, Tauri dev mode |
| **tauri-startup.sh** *(NEW)* | Full `tauri dev` startup, Vite + Tauri compilation | Long-running application stability |

## Solutions Implemented

### 1. Cache Isolation (Fixes Tests)
```bash
# All unit test scripts now use:
export CARGO_TARGET_DIR="$PROJECT_DIR/src-tauri/target/test-cache"
```
This prevents test interference with the main build cache.

### 2. Resource Strictness (Catches Leaks)
```bash
# Python tests now fail on ANY resource leak:
PYTHONWARNINGS="error::ResourceWarning" python3 -m unittest ...
```

### 3. Full Startup Test (NEW)
Created `scripts/test-tauri-startup.sh` which:
- Launches `npm run tauri dev`
- Waits for Vite dev server (http://localhost:5173)
- Detects any build errors in the startup process
- Ensures fresh Cargo artifacts are used

### 4. Cargo Cache Cleanup (Permanent Fix)
Executed once:
```bash
cd src-tauri && rm -rf target && cargo clean
```
This forces Tauri to rebuild with fresh, correct artifact paths.

## Recommended CI/CD Pipeline

```bash
# Stage 0: Code constraints (architectural validation)
bash scripts/test-constraints.sh

# Stage 1: Unit tests (fast, isolated, includes constraint checks)
bash scripts/test-unit-fast.sh

# Stage 2: Full tests (thorough)
bash scripts/test-unit.sh

# Stage 3: Lint check
bash scripts/lint.sh

# Stage 4: API integration (no UI)
bash scripts/test-integration-light.sh

# Stage 5: Full startup (catches build errors) - OPTIONAL, takes ~15-20s
bash scripts/test-tauri-startup.sh
```

Stage 5 is optional for local development but **should** run in CI/CD to catch startup regressions.

## Key Insights

1. **Unit tests** are necessary but insufficient for full-stack applications
2. **Isolated build caches** prevent interference between test and production code
3. **Resource strictness** catches lifecycle bugs that would otherwise cause hard-to-debug failures
4. **Startup tests** must validate the actual build process, not just test logic

## Next Steps

- [ ] Add `test-tauri-startup.sh` to GitHub Actions CI pipeline
- [ ] Document workspace setup in CONTRIBUTING.md (clarify cache strategy)
- [ ] Consider pre-commit hook mentioning `test-tauri-startup.sh` for developers making Tauri config changes
