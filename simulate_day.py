"""Simulador diario del Sprint 2.

Se ejecuta en GitHub Actions cada día hábil a las 18:30 (Bogotá) y aplica en
Jira y GitHub la actividad de ese día según scenario.SPRINT2_DAYS. Es
idempotente: guarda su avance en state.json y nunca repite un paso.

Uso:
  python simulate_day.py                 # ejecuta los días pendientes hasta hoy
  python simulate_day.py --until-day 3   # modo demo: avanza hasta el día 3
  python simulate_day.py --check         # solo verifica credenciales
"""
import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from clients import GitHub, Jira
from config import BOG, ROOT, at, get_config
from gitops import GitRepo, code_block, rmtree
from scenario import COMMIT_TEMPLATES, SPRINT2_DAYS, TEAM, TICKETS, lower_first, ticket_path


def log(msg):
    print(msg, flush=True)


class Simulator:
    def __init__(self, cfg, jira, gh, state, remote_fn, workdir, now, secret="", save=None):
        self.cfg, self.jira, self.gh, self.state = cfg, jira, gh, state
        self.remote_fn, self.workdir, self.now, self.secret = remote_fn, Path(workdir), now, secret
        self.save = save or (lambda: None)
        self.repos = {}

    # ---------- utilidades ----------
    def repo(self, kind):
        if kind not in self.repos:
            name = self.cfg.repos[kind]
            r = GitRepo(self.workdir / name, self.remote_fn(name), self.secret)
            r.clone()
            self.repos[kind] = r
        return self.repos[kind]

    def key(self, tid):
        return self.state["tickets"][tid]

    def branch_for(self, e, tid, dev):
        template = e.get("branch") or "feature/{key}-{dev}"
        return template.format(key=self.key(tid) if tid else "", dev=dev)

    def when(self, day, index):
        rng = random.Random(f"t-{day}-{index}")
        t = at(self.cfg.s2_days[day - 1], 9) + timedelta(minutes=30 * index + rng.randint(0, 25))
        return min(t, self.now - timedelta(minutes=5))

    # ---------- eventos ----------
    def do_start_sprint(self, e, day, i):
        d = self.cfg.s2_days
        self.jira.update_sprint(self.state["sprints"]["s2"], state="active",
                                startDate=at(d[0], 9), endDate=at(d[-1], 18))
        return "Sprint 2 iniciado"

    def do_create(self, e, day, i):
        tid = e["t"]
        t = TICKETS[tid]
        key = self.jira.create_issue(self.state["project_key"], self.state["types"][t["type"]], t["summary"],
                                     [f"{t['summary']}.", "Agregado a mitad de sprint."],
                                     self.state["users"][t["dev"]])
        self.jira.set_estimate(key, self.state["board_id"], t["sp"])
        self.jira.move_to_sprint(self.state["sprints"]["s2"], [key])
        self.state["tickets"][tid] = key
        return f"{key} creado y agregado al sprint activo ({t['sp']} SP)"

    def do_transition(self, e, day, i):
        self.jira.transition(self.key(e["t"]), e["to"])
        return f"{self.key(e['t'])} -> {e['to']}"

    def do_comment(self, e, day, i):
        self.jira.comment(self.key(e["t"]), TEAM[e["by"]]["name"], e["text"])
        return f"comentario de {e['by']} en {self.key(e['t'])}"

    def do_label(self, e, day, i):
        self.jira.add_label(self.key(e["t"]), e["label"])
        return f"etiqueta '{e['label']}' en {self.key(e['t'])}"

    def do_commit(self, e, day, i):
        tid = e.get("t")
        dev = e.get("dev") or TICKETS[tid]["dev"]
        kind = e.get("repo") or TICKETS[tid]["repo"]
        branch = self.branch_for(e, tid, dev)
        if tid:
            n = self.state["commit_counts"].get(tid, 0)
            self.state["commit_counts"][tid] = n + 1
            text = e.get("msg") or COMMIT_TEMPLATES[n % len(COMMIT_TEMPLATES)].format(
                s=lower_first(TICKETS[tid]["summary"]))
            msg = f"{self.key(tid)}: {text}"
            path = e.get("path") or ticket_path(tid)
        else:
            msg, path = e["msg"], e["path"]
        repo = self.repo(kind)
        repo.remote_branch(branch)
        rng = random.Random(f"c-{day}-{i}")
        repo.append(path, code_block(kind, rng, Path(path).stem.lower()))
        repo.commit(msg, TEAM[dev]["name"], TEAM[dev]["email"], self.when(day, i))
        repo.push(branch)
        return f"commit de {dev} en {branch}: {msg}"

    def do_open_pr(self, e, day, i):
        tid = e.get("t")
        pr_id = e.get("pr") or tid
        dev = e.get("dev") or TICKETS[tid]["dev"]
        kind = e.get("repo") or TICKETS[tid]["repo"]
        branch = self.branch_for(e, tid, dev)
        name = TEAM[dev]["name"]
        if tid:
            key = self.key(tid)
            title = f"{key}: {TICKETS[tid]['summary']}"
            body = (f"## {title}\n\nTicket en Jira: {self.cfg.jira_base_url}/browse/{key}\n\n"
                    f"### Cambios\n- Implementación de {lower_first(TICKETS[tid]['summary'])}\n"
                    f"- Pruebas unitarias\n\n_Autor: {name}_\n<!-- author: {dev} -->")
        else:
            title = e["title"]
            body = f"Mejoras visuales solicitadas por diseño.\n\n_Autor: {name}_\n<!-- author: {dev} -->"
        number = self.gh.create_pr(self.cfg.repos[kind], branch, title, body)
        self.state["prs"][pr_id] = {"repo": kind, "number": number, "branch": branch, "title": title}
        return f"PR #{number} abierto: {title}"

    def do_review(self, e, day, i):
        p = self.state["prs"][e["pr"]]
        name = TEAM[e["by"]]["name"]
        status = "APROBADO" if e["approved"] else "CAMBIOS SOLICITADOS"
        icon = "✅" if e["approved"] else "🔁"
        text = e.get("text") or "Revisado. Se ve bien."
        body = (f"**Revisión de código** · {name}\n\nEstado: {icon} {status}\n\n{text}\n\n"
                f"<!-- review: {'approved' if e['approved'] else 'changes_requested'} by {e['by']} -->")
        self.gh.comment(self.cfg.repos[p["repo"]], p["number"], body)
        return f"review de {e['by']} en PR #{p['number']}: {status}"

    def do_merge(self, e, day, i):
        p = self.state["prs"][e["pr"]]
        self.gh.merge_pr(self.cfg.repos[p["repo"]], p["number"], f"Merge pull request #{p['number']}: {p['title']}")
        return f"PR #{p['number']} mergeado"

    # ---------- ciclo ----------
    def run_day(self, day):
        events = SPRINT2_DAYS[day]
        done = self.state["progress"].get(str(day), 0)
        log(f"\n== Día {day} ({self.cfg.s2_days[day - 1]}) ==")
        for i in range(done, len(events)):
            e = events[i]
            result = getattr(self, f"do_{e['kind']}")(e, day, i)
            log(f"  [{i + 1}/{len(events)}] {result}")
            self.state["progress"][str(day)] = i + 1
            self.save()
        self.state["days_done"].append(day)
        self.save()


def pending_days(cfg, state, today, until_day=None):
    if until_day:
        target = min(until_day, len(cfg.s2_days))
    else:
        target = sum(1 for d in cfg.s2_days if d <= today)
    return [d for d in range(1, target + 1) if d not in state["days_done"]]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--until-day", type=int, default=None)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    cfg = get_config()
    jira = Jira(cfg.jira_base_url, cfg.jira_email, cfg.jira_token)
    gh = GitHub(cfg.gh_owner, cfg.gh_token)
    if not cfg.state_path.exists():
        raise SystemExit("No existe state.json. Ejecuta primero seed.py.")
    state = json.loads(cfg.state_path.read_text(encoding="utf-8"))

    if args.check:
        log(f"Jira: {jira.myself().get('displayName')} | GitHub: {gh.whoami()}")
        log(f"Días ejecutados: {state['days_done'] or 'ninguno'}")
        return

    now = datetime.now(BOG)
    days = pending_days(cfg, state, now.date(), args.until_day)
    if not days:
        log("No hay días pendientes para ejecutar.")
        return

    def save():
        cfg.state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    workdir = ROOT / "_work"
    sim = Simulator(cfg, jira, gh, state, gh.remote_url, workdir, now, secret=cfg.gh_token, save=save)
    try:
        for d in days:
            sim.run_day(d)
    finally:
        rmtree(workdir)


if __name__ == "__main__":
    main()
