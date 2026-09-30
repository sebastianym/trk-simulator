"""Prueba completa SIN tocar Jira ni GitHub.

Simula la siembra y los días del Sprint 2 con un Jira y un GitHub falsos en
memoria, y repositorios Git locales. Sirve para verificar que tu computador
tiene todo lo necesario y para ver el resultado esperado del escenario.

Uso: python dryrun.py
"""
import subprocess
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import seed
from clients import CATEGORY, ApiError
from config import ROOT, at, get_config
from gitops import GitRepo, rmtree
from scenario import TEAM, TICKETS
from simulate_day import Simulator, pending_days

DRY = ROOT / "_dryrun"


class FakeJira:
    def __init__(self):
        self.issues, self.sprints, self.n = {}, {}, 0

    def create_issue(self, pk, type_id, summary, desc, assignee):
        self.n += 1
        key = f"{pk}-{self.n}"
        self.issues[key] = {"summary": summary, "cat": "new", "assignee": assignee, "sp": None,
                            "sprints": [], "labels": [], "comments": [], "type": type_id}
        return key

    def set_estimate(self, key, board, value):
        self.issues[key]["sp"] = float(value)

    def transition(self, key, target):
        cat = CATEGORY[target]
        if self.issues[key]["cat"] == cat:
            raise ApiError(f"{key} ya está en {cat}")
        self.issues[key]["cat"] = cat

    def comment(self, key, author, text):
        self.issues[key]["comments"].append((author, text))

    def add_label(self, key, label):
        self.issues[key]["labels"].append(label)

    def create_sprint(self, board, name, start, end, goal):
        sid = len(self.sprints) + 1
        self.sprints[sid] = {"name": name, "state": "future"}
        return sid

    def update_sprint(self, sid, **f):
        if f.get("state") == "active" and any(s["state"] == "active" for s in self.sprints.values()):
            raise ApiError("Ya hay un sprint activo")
        self.sprints[sid].update({k: v for k, v in f.items() if k == "state"})

    def move_to_sprint(self, sid, keys):
        if self.sprints[sid]["state"] == "closed":
            raise ApiError("No se puede mover a un sprint cerrado")
        for k in keys:
            self.issues[k]["sprints"].append(sid)


class FakeGitHub:
    def __init__(self, remotes):
        self.remotes, self.prs = remotes, {}

    def create_pr(self, repo, head, title, body):
        out = subprocess.run(["git", "rev-parse", "--verify", "-q", f"refs/heads/{head}"],
                             cwd=self.remotes[repo], capture_output=True, text=True)
        if out.returncode != 0:
            raise ApiError(f"La rama {head} no existe en {repo}")
        n = len([p for p in self.prs if p[0] == repo]) + 1
        self.prs[(repo, n)] = {"head": head, "title": title, "state": "open", "comments": []}
        return n

    def comment(self, repo, number, body):
        self.prs[(repo, number)]["comments"].append(body)

    def merge_pr(self, repo, number, title):
        p = self.prs[(repo, number)]
        if p["state"] != "open":
            raise ApiError("PR no está abierto")
        tmp = GitRepo(DRY / "_merge", self.remotes[repo])
        tmp.clone()
        tmp.git("checkout", "-q", "main")
        tmp.git("merge", "-q", "--no-ff", f"origin/{p['head']}", "-m", title,
                env=GitRepo._identity_env("sebastianym", "owner@example.com", at(get_config(False).sprint2_end, 19)))
        tmp.push("main")
        rmtree(tmp.path)
        p["state"] = "merged"


def main():
    cfg = get_config(require_secrets=False)
    rmtree(DRY)
    DRY.mkdir()
    remotes = {}
    for name in cfg.repos.values():
        path = DRY / "remotes" / f"{name}.git"
        path.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", "--bare", str(path)], check=True)
        subprocess.run(["git", "symbolic-ref", "HEAD", "refs/heads/main"], cwd=path, check=True)
        remotes[name] = str(path)

    jira, gh = FakeJira(), FakeGitHub(remotes)
    users = {dev: f"acc-{dev}" for dev in TEAM}
    ctx = {"board_id": 1, "est_field": "customfield_10016", "types": {"story": "1", "bug": "2", "task": "3"}, "users": users}

    print("=== SIEMBRA (simulada) ===")
    seed_now = at(cfg.sprint2_start - timedelta(days=2), 12)
    state = seed.run(cfg, jira, gh, lambda r: remotes[r], DRY / "_work", seed_now, ctx)

    print("\n=== SPRINT 2 (simulado completo) ===")
    sim_now = at(cfg.sprint2_end, 19)
    sim = Simulator(cfg, jira, gh, state, lambda r: remotes[r], DRY / "_work2", sim_now)
    for d in pending_days(cfg, state, sim_now.date()):
        sim.run_day(d)

    # ---------------- Resumen del resultado esperado ----------------
    by_acc = {v: k for k, v in users.items()}
    s2 = state["sprints"]["s2"]
    commits_by_key = defaultdict(int)
    orphan = defaultdict(int)
    for name in cfg.repos.values():
        log = subprocess.run(["git", "log", "--all", "--no-merges", f"--since={cfg.sprint2_start}",
                              "--format=%ae|%s"], cwd=remotes[name], capture_output=True, text=True,
                             encoding="utf-8").stdout.splitlines()
        for line in log:
            email, subj = line.split("|", 1)
            if subj.startswith(f"{cfg.project_key}-"):
                commits_by_key[subj.split(":")[0]] += 1
            else:
                orphan[email] += 1
    pr_keys = {p["title"].split(":")[0] for p in gh.prs.values()}

    print("\n=== RESULTADO ESPERADO AL CIERRE DEL SPRINT 2 ===")
    print(f"{'Dev':<16}{'Comprom.':>9}{'Hecho':>7}{'Tickets Done sin PR':>22}{'Commits sin ticket':>20}")
    for dev, info in TEAM.items():
        mine = [k for k, i in jira.issues.items() if s2 in i["sprints"] and by_acc[i["assignee"]] == dev]
        total = sum(jira.issues[k]["sp"] for k in mine)
        done = sum(jira.issues[k]["sp"] for k in mine if jira.issues[k]["cat"] == "done")
        no_pr = [k for k in mine if jira.issues[k]["cat"] == "done" and k not in pr_keys]
        print(f"{info['name']:<16}{total:>9.0f}{done:>7.0f}{', '.join(no_pr) or '-':>22}{orphan[info['email']]:>20}")
    open_prs = [f"#{n} {p['title']}" for (r, n), p in gh.prs.items() if p["state"] == "open"]
    print(f"\nPRs abiertos al cierre: {len(open_prs)}")
    for p in open_prs:
        print(f"  {p}")
    print(f"PRs totales: {len(gh.prs)} | Tickets creados: {len(jira.issues)}")
    rmtree(DRY)
    print("\nPrueba local completa: el escenario se ejecutó de principio a fin sin errores.")


if __name__ == "__main__":
    main()
