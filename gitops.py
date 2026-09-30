"""Operaciones Git locales: commits con autor y fecha controlados, ramas y push."""
import os
import random
import shutil
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class GitError(RuntimeError):
    pass


def _force_remove(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def rmtree(path) -> None:
    if Path(path).exists():
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=_force_remove)
        else:
            shutil.rmtree(path, onerror=_force_remove)


class GitRepo:
    def __init__(self, path, remote: str, secret: str = ""):
        self.path = Path(path)
        self.remote = remote
        self.secret = secret

    def _redact(self, text: str) -> str:
        return text.replace(self.secret, "***") if self.secret else text

    def _run(self, args, cwd, env=None, check=True) -> str:
        full_env = os.environ.copy()
        full_env.update(env or {})
        full_env["GIT_TERMINAL_PROMPT"] = "0"
        cmd = ["git", "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args]
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=full_env)
        if check and r.returncode != 0:
            raise GitError(self._redact(f"git {' '.join(args)}\n{r.stdout}\n{r.stderr}"))
        return r.stdout.strip()

    def git(self, *args, env=None, check=True) -> str:
        return self._run(list(args), cwd=self.path, env=env, check=check)

    # ---------- preparación ----------
    def init_new(self) -> None:
        rmtree(self.path)
        self.path.mkdir(parents=True)
        self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        self.git("remote", "add", "origin", self.remote)

    def clone(self) -> None:
        rmtree(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._run(["clone", "-q", self.remote, str(self.path)], cwd=self.path.parent)

    def _has_ref(self, ref: str) -> bool:
        return self.git("rev-parse", "--verify", "-q", ref, check=False) != ""

    # ---------- ramas ----------
    def local_branch(self, branch: str) -> None:
        """Modo siembra: todo es local, las ramas nacen de main."""
        if self._has_ref(f"refs/heads/{branch}"):
            self.git("checkout", "-q", branch)
        else:
            self.git("checkout", "-q", "-b", branch, "main")

    def remote_branch(self, branch: str) -> None:
        """Modo simulador: sincroniza con GitHub y deja la rama lista para commitear."""
        self.git("fetch", "-q", "origin", "--prune")
        if branch == "main":
            self.git("checkout", "-q", "-B", "main", "origin/main")
        elif self._has_ref(f"refs/remotes/origin/{branch}"):
            self.git("checkout", "-q", "-B", branch, f"origin/{branch}")
        else:
            self.git("checkout", "-q", "-B", branch, "origin/main")

    # ---------- cambios ----------
    def append(self, relpath: str, text: str) -> None:
        p = self.path / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8", newline="\n") as f:
            f.write(text)

    @staticmethod
    def _identity_env(name: str, email: str, when: datetime) -> dict:
        stamp = when.isoformat(timespec="seconds")
        return {
            "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email, "GIT_AUTHOR_DATE": stamp,
            "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email, "GIT_COMMITTER_DATE": stamp,
        }

    def commit(self, message: str, name: str, email: str, when: datetime) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message, env=self._identity_env(name, email, when))

    def merge_local(self, branch: str, message: str, name: str, email: str, when: datetime) -> None:
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", branch, "-m", message, env=self._identity_env(name, email, when))
        self.git("branch", "-q", "-D", branch)

    def push(self, branch: str) -> None:
        self.git("push", "-q", "origin", f"{branch}:{branch}")


def code_block(repo_kind: str, rng: random.Random, label: str) -> str:
    """Genera un bloque de código plausible (Python o TSX) de tamaño variable."""
    n = rng.randint(6, 34)
    name = f"{label}_{rng.randint(100, 999)}"
    if repo_kind == "backend":
        lines = [f"\n\ndef {name}(payload: dict) -> dict:", f'    """Paso {name}."""', "    result = {}"]
        for i in range(n):
            lines.append(f"    result['campo_{i}'] = payload.get('campo_{i}', {rng.randint(0, 99)})")
        lines.append("    return result\n")
    else:
        comp = "".join(p.capitalize() for p in name.split("_"))
        lines = [f"\n\nexport function {comp}() {{", "  return (", "    <div>"]
        for i in range(n):
            lines.append(f'      <span data-field="f{i}">{{/* item {rng.randint(0, 99)} */}}</span>')
        lines += ["    </div>", "  );", "}\n"]
    return "\n".join(lines)
