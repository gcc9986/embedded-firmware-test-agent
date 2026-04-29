from __future__ import annotations

import subprocess
from pathlib import Path

EMBEDDED_EXTENSIONS = {".c", ".h", ".cpp", ".hpp", ".s", ".S", ".ld", ".cmake", ".mk"}


def _git(repo_path: str | Path, args: list[str], timeout_sec: int = 20) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(Path(repo_path).resolve()),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except Exception as exc:
        return 1, "", str(exc)


def is_git_repo(repo_path: str | Path) -> bool:
    code, out, _ = _git(repo_path, ["rev-parse", "--is-inside-work-tree"])
    return code == 0 and out.strip() == "true"


def current_branch(repo_path: str | Path) -> str:
    code, out, _ = _git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])
    return out.strip() if code == 0 and out.strip() else "unknown"


def head_commit(repo_path: str | Path) -> str:
    code, out, _ = _git(repo_path, ["rev-parse", "--short", "HEAD"])
    return out.strip() if code == 0 and out.strip() else "unknown"


def changed_files(repo_path: str | Path, base_ref: str = "HEAD~1", head_ref: str = "HEAD") -> list[str]:
    if not is_git_repo(repo_path):
        return scan_embedded_files(repo_path)
    code, out, _ = _git(repo_path, ["diff", "--name-only", f"{base_ref}...{head_ref}"])
    if code != 0 or not out.strip():
        code, out, _ = _git(repo_path, ["diff", "--name-only", f"{base_ref}", f"{head_ref}"])
    if code != 0 or not out.strip():
        code, out, _ = _git(repo_path, ["status", "--short"])
        if code == 0:
            return [line[3:].strip() for line in out.splitlines() if len(line) > 3]
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def diff_text(repo_path: str | Path, base_ref: str = "HEAD~1", head_ref: str = "HEAD", limit_chars: int = 60000) -> str:
    if not is_git_repo(repo_path):
        return ""
    code, out, err = _git(repo_path, ["diff", "--unified=3", f"{base_ref}...{head_ref}"])
    if code != 0 or not out.strip():
        code, out, err = _git(repo_path, ["diff", "--unified=3", f"{base_ref}", f"{head_ref}"])
    if code != 0:
        return err.strip()
    return out[:limit_chars]


def scan_embedded_files(repo_path: str | Path, max_files: int = 200) -> list[str]:
    root = Path(repo_path)
    if not root.exists():
        return []
    files: list[str] = []
    for p in root.rglob("*"):
        if len(files) >= max_files:
            break
        if ".git" in p.parts or not p.is_file():
            continue
        if p.suffix in EMBEDDED_EXTENSIONS or p.name in {"Makefile", "CMakeLists.txt"}:
            files.append(str(p.relative_to(root)))
    return files
