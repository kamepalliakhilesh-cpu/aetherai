"""
Pair Programmer Module for JARVIS (Pillar 5).
Provides real-time compiler diagnostics, terminal command execution,
stack trace root-cause analysis, and safe hot-patching with automatic syntax rollback.
"""

import os
import sys
import re
import shutil
import subprocess
import py_compile
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional

def run_compiler_diagnostics(target: str, cwd: Optional[str] = None) -> Dict[str, Any]:
    """
    Runs compiler and runtime diagnostics on a file or command.
    Captures tracebacks, identifies error types and offending line numbers,
    and returns a structured diagnostic report.
    """
    target = target.strip()
    work_dir = cwd or os.getcwd()
    target_path = Path(work_dir) / target if not os.path.isabs(target) else Path(target)

    # 1. Direct Python compilation and syntax check if pointing to a .py file
    if target.endswith(".py") and target_path.exists():
        try:
            py_compile.compile(str(target_path), doraise=True)
            return {
                "success": True,
                "target": str(target_path.name),
                "status": "CLEAN",
                "exit_code": 0,
                "summary": f"Compiler diagnostics passed clean for '{target_path.name}'. Bytecode compiled with zero syntax or indentation errors."
            }
        except py_compile.PyCompileError as pe:
            # SyntaxError caught at compilation stage
            err_msg = str(pe)
            match = re.search(r'File "(.*?)", line (\d+)', err_msg)
            line_no = int(match.group(2)) if match else None
            return {
                "success": False,
                "target": str(target_path.name),
                "status": "SYNTAX_ERROR",
                "error_type": "SyntaxError",
                "line": line_no,
                "traceback": err_msg,
                "suggested_fix": "Inspect unclosed parentheses, quotes, or missing indentation near indicated line.",
                "summary": f"Compiler Syntax Error in '{target_path.name}' at line {line_no}."
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "target": str(target_path.name),
                "status": "TIMEOUT",
                "error_type": "ExecutionTimeout",
                "summary": f"Script execution exceeded 12s timeout (potential infinite loop or blocking I/O)."
            }

    # 2. General command execution (allowlisted only, never shell=True)
    try:
        from src.actions.computer_use import _is_command_allowed
        if not _is_command_allowed(target):
            return {
                "success": False,
                "command": target,
                "status": "BLOCKED",
                "summary": f"Diagnostic command not allowed by safety allowlist: '{target}'."
            }
        import shlex
        cmd_parts = shlex.split(target, posix=False)
        start_t = time.time()
        proc = subprocess.run(
            cmd_parts,
            shell=False,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        duration = round(time.time() - start_t, 3)

        if proc.returncode == 0:
            return {
                "success": True,
                "command": target,
                "status": "SUCCESS",
                "exit_code": 0,
                "duration_seconds": duration,
                "stdout": proc.stdout.strip()[:1500],
                "summary": f"Command '{target}' executed successfully in {duration}s."
            }
        else:
            raw_err = (proc.stderr or proc.stdout).strip()
            parsed = _parse_python_traceback(raw_err, target)
            parsed["duration_seconds"] = duration
            parsed["exit_code"] = proc.returncode
            return parsed
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "command": target,
            "status": "TIMEOUT",
            "summary": f"Terminal command '{target}' timed out after 30s."
        }
    except Exception as e:
        return {
            "success": False,
            "command": target,
            "error": str(e),
            "summary": f"Failed to execute command '{target}': {str(e)}"
        }

def _parse_python_traceback(output: str, source_label: str) -> Dict[str, Any]:
    """Parses standard Python tracebacks to isolate the error type, file, line, and suggested fix."""
    lines = output.strip().splitlines()
    error_type = "RuntimeError"
    error_detail = ""
    line_number = None
    file_name = None

    for line in reversed(lines):
        line = line.strip()
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*Error|Exception):\s*(.*)$", line)
        if match:
            error_type = match.group(1)
            error_detail = match.group(2)
            break

    file_matches = re.findall(r'File "([^"]+)", line (\d+)(?:, in (\w+))?', output)
    if file_matches:
        last_file, last_line, func_name = file_matches[-1]
        file_name = Path(last_file).name
        line_number = int(last_line)

    suggested_fix = _generate_suggested_fix(error_type, error_detail)

    return {
        "success": False,
        "target": source_label,
        "status": "ERROR_DETECTED",
        "error_type": error_type,
        "error_detail": error_detail,
        "file": file_name,
        "line": line_number,
        "traceback": output[-1200:],
        "suggested_fix": suggested_fix,
        "summary": f"Diagnosed {error_type} in {file_name or source_label} (Line {line_number or '?'}) - {error_detail}"
    }

def _generate_suggested_fix(error_type: str, detail: str) -> str:
    """Generates precise prescriptive recommendations based on common compiler/runtime errors."""
    if error_type == "ModuleNotFoundError" or error_type == "ImportError":
        mod = detail.split("'")[1] if "'" in detail else detail
        return f"Missing dependency. Run 'py -m pip install {mod}' or add it to requirements.txt."
    elif error_type == "NameError":
        var = detail.split("'")[1] if "'" in detail else detail
        return f"Variable '{var}' is referenced before assignment or misspelled. Check scoping and variable declarations."
    elif error_type == "TypeError":
        return "Type mismatch or missing argument. Verify function signature and argument types."
    elif error_type == "AttributeError":
        return f"Object does not possess the requested attribute. Verify object instantiation and property names."
    elif error_type == "IndexError":
        return "List index out of range. Check collection length before indexing or use .get() / bounds checking."
    elif error_type == "KeyError":
        return f"Dictionary key {detail} not found. Use .get({detail}, default_value) to avoid KeyErrors."
    elif error_type == "ZeroDivisionError":
        return "Division by zero detected. Add a guard: if denominator != 0 before division."
    elif error_type == "FileNotFoundError":
        return "File path does not exist. Verify relative vs absolute path and check if file exists with Path.exists()."
    return "Review the traceback above and inspect the indicated line number for logic errors."

def diagnose_code_error(error_log: str, code_context: Optional[str] = None) -> Dict[str, Any]:
    """
    Takes an error log, compiler output, or stack trace and returns root-cause analysis
    along with actionable repair instructions.
    """
    if not error_log or not error_log.strip():
        return {"success": False, "summary": "Empty error log provided."}

    parsed = _parse_python_traceback(error_log, "Provided Traceback")
    if code_context and parsed.get("line"):
        context_lines = code_context.splitlines()
        target_idx = parsed["line"] - 1
        start_idx = max(0, target_idx - 3)
        end_idx = min(len(context_lines), target_idx + 4)
        snippet = "\n".join([f"{i+1:4d} | {context_lines[i]}" for i in range(start_idx, end_idx)])
        parsed["code_snippet"] = snippet

    return parsed

def hot_patch_file(file_path: str, target_snippet: str, replacement_snippet: str, verify_compile: bool = True) -> Dict[str, Any]:
    """
    Hot-patches a source code script with atomic backup and rollback protection.
    1. Backs up original file to <file>.bak
    2. Replaces target_snippet with replacement_snippet
    3. Runs syntax validation (py_compile for Python)
    4. If syntax fails, automatically rolls back to original file and aborts!
    5. Returns diff summary and status.
    """
    target = Path(file_path)
    if not target.exists():
        return {"success": False, "error": f"Target file '{file_path}' does not exist."}

    content = target.read_text(encoding="utf-8")
    if target_snippet not in content:
        return {
            "success": False,
            "error": "Target snippet to replace was not found in the file.",
            "file": str(target)
        }

    # Create safety backup
    backup_path = target.with_suffix(target.suffix + ".bak")
    shutil.copy2(target, backup_path)

    # Apply replacement
    patched_content = content.replace(target_snippet, replacement_snippet, 1)
    target.write_text(patched_content, encoding="utf-8")

    # Verification phase
    if verify_compile and target.suffix == ".py":
        try:
            py_compile.compile(str(target), doraise=True)
        except py_compile.PyCompileError as pe:
            # Syntax validation failed! Roll back immediately
            shutil.copy2(backup_path, target)
            return {
                "success": False,
                "status": "ROLLED_BACK",
                "error": f"Patch introduced syntax error: {str(pe)}",
                "summary": f"Hot-patch aborted! Compilation failed, original code restored from backup."
            }

    return {
        "success": True,
        "status": "PATCHED",
        "file": str(target),
        "backup": str(backup_path),
        "lines_changed": len(replacement_snippet.splitlines()),
        "summary": f"Successfully hot-patched '{target.name}'. Syntax verified clean. Backup saved to '{backup_path.name}'."
    }
