#!/usr/bin/env python3
"""
Test code quality constraints per ARCHITECTURE.md:
- Files under 400 lines (Python/Rust source code)
- No hardcoded paths in source files (except config/tests)
- All logging via unified logger (no print/println outside tests)
"""

import unittest
import re
from pathlib import Path
from typing import Set, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
MAX_FILE_LINES = 400
MAX_SOURCE_FILES_LINES = 400  # Python and Rust source files

# Paths to exclude from checks
EXCLUDED_DIRS = {
    '.git', '__pycache__', 'node_modules', '.venv', 'venv',
    'target', '.pytest_cache', '.github', '.vscode',
    'dist', 'build', '.cargo', 'logs', 'reports'
}

# Files exempted from line count limits (with documented reasons)
EXEMPTED_FILE_LINE_LIMITS = {
}

# File patterns to check for path constraints
PATH_CHECK_PATTERNS = {
    '.py': r'["\']/?[a-zA-Z0-9/_.-]*(?:/[a-zA-Z0-9_.-]+)+["\']',
    '.rs': r'["\']/?[a-zA-Z0-9/_.-]*(?:/[a-zA-Z0-9_.-]+)+["\']',
}

# Allowed absolute paths (in config, tests, or documentation)
ALLOWED_PATH_PREFIXES = {
    '/Dropbox', '/Users', '/home', '/opt', '/tmp', '/var',
    'C:\\', 'D:\\',  # Windows paths
}

# Logging patterns to check
HARDCODED_LOG_PATTERNS = {
    'print(': r'\bprint\s*\(',
    'println!': r'\bprintln!\s*\[!\(?',
    'eprintln!': r'\beprintln!\s*\[!\(?',
    'console.log': r'\bconsole\.log\s*\(',
}


class CodeConstraintTests(unittest.TestCase):
    """Validate architectural constraints on code."""

    @classmethod
    def setUpClass(cls):
        """Identify all source files to check."""
        cls.py_files = list(PROJECT_ROOT.rglob('*.py'))
        cls.rs_files = list(PROJECT_ROOT.rglob('*.rs'))
        cls.ts_files = list(PROJECT_ROOT.rglob('*.ts'))
        
        # Filter out excluded directories
        cls.py_files = [
            f for f in cls.py_files 
            if not any(part in EXCLUDED_DIRS for part in f.relative_to(PROJECT_ROOT).parts)
        ]
        cls.rs_files = [
            f for f in cls.rs_files 
            if not any(part in EXCLUDED_DIRS for part in f.relative_to(PROJECT_ROOT).parts)
        ]
        cls.ts_files = [
            f for f in cls.ts_files 
            if not any(part in EXCLUDED_DIRS for part in f.relative_to(PROJECT_ROOT).parts)
        ]

    def _read_file_lines(self, path: Path) -> Tuple[int, str]:
        """Read file and return line count and content."""
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
            return len(content.splitlines()), content
        except Exception as e:
            self.fail(f"Failed to read {path}: {e}")

    def test_python_files_under_400_lines(self):
        """Python source files should be under 400 lines (excluding tests)."""
        violations = []
        exempted_violations = []
        
        for py_file in self.py_files:
            # Skip test files - they can be longer
            if 'test_' in py_file.name:
                continue
            
            lines, _ = self._read_file_lines(py_file)
            if lines > MAX_FILE_LINES:
                relative_path = str(py_file.relative_to(PROJECT_ROOT))
                
                # Check if file is exempted
                if relative_path in EXEMPTED_FILE_LINE_LIMITS:
                    reason = EXEMPTED_FILE_LINE_LIMITS[relative_path]
                    exempted_violations.append((relative_path, lines, reason))
                else:
                    violations.append(f"{relative_path}: {lines} lines (max: {MAX_FILE_LINES})")
        
        # Log exempted violations for awareness
        if exempted_violations:
            msg = "⚠️  Python files exceeding limits (exempted):\n"
            for path, line_count, reason in exempted_violations:
                msg += f"  {path}: {line_count} lines — {reason}\n"
            print("\n" + msg)
        
        if violations:
            msg = "Python files exceed 400 lines:\n" + "\n".join(violations)
            self.fail(msg)

    def test_rust_files_under_400_lines(self):
        """Rust source files should be under 400 lines (excluding tests)."""
        violations = []
        exempted_violations = []
        
        for rs_file in self.rs_files:
            # Skip test modules (they often have inline tests)
            if '#[cfg(test)]' in rs_file.read_text(encoding='utf-8', errors='ignore'):
                continue
            
            lines, _ = self._read_file_lines(rs_file)
            if lines > MAX_FILE_LINES:
                relative_path = str(rs_file.relative_to(PROJECT_ROOT))
                
                # Check if file is exempted
                if relative_path in EXEMPTED_FILE_LINE_LIMITS:
                    reason = EXEMPTED_FILE_LINE_LIMITS[relative_path]
                    exempted_violations.append((relative_path, lines, reason))
                else:
                    violations.append(f"{relative_path}: {lines} lines (max: {MAX_FILE_LINES})")
        
        # Log exempted violations for awareness
        if exempted_violations:
            msg = "⚠️  Rust files exceeding limits (exempted):\n"
            for path, line_count, reason in exempted_violations:
                msg += f"  {path}: {line_count} lines — {reason}\n"
            print("\n" + msg)
        
        if violations:
            msg = "Rust files exceed 400 lines:\n" + "\n".join(violations)
            self.fail(msg)

    def test_no_hardcoded_paths_in_python(self):
        """Python source files should not contain hardcoded paths."""
        violations = []
        
        for py_file in self.py_files:
            # Skip test files and config files
            if 'test_' in py_file.name or py_file.name == 'config.py':
                continue
            
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            
            for line_no, line in enumerate(lines, 1):
                # Skip comments and docstrings
                if line.strip().startswith('#') or line.strip().startswith('"""') or line.strip().startswith("'''"):
                    continue
                
                # Look for absolute paths
                if any(prefix in line for prefix in ALLOWED_PATH_PREFIXES):
                    # Check if it's in a string (hardcoded path)
                    if re.search(r'["\'].*(?:/Dropbox|/Users|/home|/opt|/tmp|/var|C:\\|D:\\)', line):
                        relative_path = py_file.relative_to(PROJECT_ROOT)
                        violations.append(f"{relative_path}:{line_no}: {line.strip()}")
        
        if violations:
            msg = "Hardcoded paths found in Python:\n" + "\n".join(violations)
            self.fail(msg)

    def test_no_hardcoded_paths_in_rust(self):
        """Rust source files should not contain hardcoded paths (except in tests/config)."""
        violations = []
        
        for rs_file in self.rs_files:
            # Skip test files, build scripts, and config defaults
            if 'test' in rs_file.name or rs_file.name == 'build.rs' or rs_file.name == 'config.rs':
                continue
            if '#[cfg(test)]' in rs_file.read_text(encoding='utf-8', errors='ignore'):
                continue
            
            content = rs_file.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            
            for line_no, line in enumerate(lines, 1):
                # Skip comments and default config values
                if line.strip().startswith('//'):
                    continue
                if 'DEFAULT_CONFIG' in line or 'test_' in rs_file.name:
                    continue
                
                # Look for absolute paths (not /tmp which is normal for tests)
                if re.search(r'["\'](?:/home|/opt|/var|/Dropbox|/Users|C:\\|D:\\)', line):
                    relative_path = rs_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{relative_path}:{line_no}: {line.strip()}")
        
        if violations:
            msg = "Hardcoded paths found in Rust source (non-test):\n" + "\n".join(violations)
            self.fail(msg)

    def test_logging_via_unified_logger_python(self):
        """Python code should use logger, not print() directly."""
        violations = []
        
        # Only check core API, not tests
        for py_file in self.py_files:
            if 'test_' in py_file.name or py_file.name == '__init__.py':
                continue
            if 'core/api' not in str(py_file):
                continue
            
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            
            for line_no, line in enumerate(lines, 1):
                # Skip comments and docstrings
                if line.strip().startswith('#') or line.strip().startswith('"""'):
                    continue
                
                # Check for direct print() calls (not in logging, not in test)
                if re.search(r'\bprint\s*\(', line) and 'logger' not in line:
                    relative_path = py_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{relative_path}:{line_no}: {line.strip()}")
        
        if violations:
            msg = "Direct print() calls found (use logger instead):\n" + "\n".join(violations)
            self.fail(msg)

    def test_logging_via_unified_logger_rust(self):
        """Rust code should use logging facade/crate, not println! directly."""
        violations = []
        
        # Only check core Rust binaries, not tests or examples
        for rs_file in self.rs_files:
            if 'test' in rs_file.name:
                continue
            if 'examples' in str(rs_file):
                continue
            if 'src-tauri/src' not in str(rs_file):
                continue
            
            content = rs_file.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            
            for line_no, line in enumerate(lines, 1):
                # Skip comments
                if line.strip().startswith('//'):
                    continue
                
                # Check for println!/eprintln! (except in main or tests)
                if re.search(r'\b(?:println|eprintln)!\s*\(', line):
                    # Allow in main.rs for startup messages
                    if rs_file.name == 'main.rs':
                        continue
                    
                    relative_path = rs_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{relative_path}:{line_no}: {line.strip()}")
        
        if violations:
            msg = "Direct println! calls found (use logger instead):\n" + "\n".join(violations)
            self.fail(msg)

    def test_path_manager_usage(self):
        """Critical paths should use dedicated path manager, not raw Path/std::path."""
        # This is a soft check - log but don't fail if not found
        violations = []
        
        for rs_file in self.rs_files:
            if 'src-tauri/src/paths.rs' in str(rs_file):
                continue  # This is the path manager itself
            if 'test' in rs_file.name:
                continue
            
            content = rs_file.read_text(encoding='utf-8', errors='ignore')
            
            # Check if file uses path operations but doesn't import the path manager
            if re.search(r'(?:std::path|PathBuf|paths::)', content):
                if 'paths::' not in content and 'std::path::PathBuf' in content:
                    # Check if it's creating paths without going through path manager
                    if re.search(r'PathBuf::from\s*\(\s*["\']', content):
                        relative_path = rs_file.relative_to(PROJECT_ROOT)
                        violations.append(f"{relative_path}: direct PathBuf creation (consider paths:: module)")
        
        # This is informational, not a hard failure
        if violations:
            print("\n⚠️  Path manager usage suggestions:\n" + "\n".join(violations))


if __name__ == '__main__':
    unittest.main()
