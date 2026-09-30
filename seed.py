"""Siembra inicial del piloto (se ejecuta UNA sola vez desde tu computador).

Crea en Jira el Sprint 1 (cerrado, con arrastre) y el Sprint 2 (planeado),
sube a GitHub el historial del Sprint 1 con fechas reales y deja state.json
listo para el simulador diario.

Uso:
  python seed.py --check     # solo verifica credenciales y configuración
  python seed.py             # ejecuta la siembra
"""
import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from clients import GitHub, Jira
from config import BOG, ROOT, at, get_config
from gitops import GitRepo, code_block, rmtree
from scenario import (CARRYOVER, COMMIT_TEMPLATES, SPRINT1_GOAL, SPRINT1_PLAN, SPRINT1_TICKETS,
                      SPRINT2_GOAL, SPRINT2_PLANNED, TEAM, TICKETS, lower_first, ticket_path)


def log(msg):
    print(msg, flush=True)


def description(tid):
    t = TICKETS[tid]
    return [
        f"{t['summary']}.",
        "Criterios de aceptación: cumple la definición de terminado del equipo, incluye pruebas "
        "unitarias y queda enlazado a su PR mediante la clave del ticket.",
        "Convención: rama feature/<CLAVE>-<dev>, commits y título del PR con el prefijo <CLAVE>:",
    ]


# --------------------------------------------------------------------------
def preflight(cfg, jira, gh, force=False):
    log("1/6 Verificando Jira...")
    me = jira.myself()
    log(f"    Conectado como {me.get('displayName')}")
    project = jira.project(cfg.project_key)
    if project.get("style") not in (None, "classic"):
        raise SystemExit("    El espacio TRK no es company-managed. Avísame antes de continuar.")
    existing = jira.issue_keys(cfg.project_key)
    if existing and not force:
        raise SystemExit(f"    El espacio {cfg.project_key} ya tiene {len(existing)} tickets. "
                         "Ejecuta reset_jira.py primero o usa --force.")
    board_id = jira.scrum_board(cfg.project_key)
    if not board_id:
        raise SystemExit("    No encontré un tablero Scrum para el espacio.")
    est_field = jira.estimation_field(board_id)
    types = jira.issue_type_ids(project)
    for kind in ("story", "bug", "task"):
        if kind not in types:
            raise SystemExit(f"    No encontré el tipo de ticket '{kind}' en el espacio.")
    users = {}
    for dev, info in TEAM.items():
        acc = jira.find_user(cfg.project_key, info["name"])
        if not acc:
            raise SystemExit(f"    No encontré a '{info['name']}' como usuario asignable en {cfg.project_key}.")
        users[dev] = acc
    log(f"    Tablero {board_id}, campo de estimación {est_field}, 6 devs encontrados.")

    log("2/6 Verificando GitHub...")
    login = gh.whoami()
    log(f"    Conectado como {login}")
    for repo in cfg.repos.values():
        if not gh.repo_is_empty(repo):
            raise SystemExit(f"    El repositorio {repo} no está vacío. Bórralo y créalo de nuevo vacío.")
    log("    Repositorios encontrados y vacíos.")
    return {"board_id": board_id, "est_field": est_field, "types": types, "users": users}


# --------------------------------------------------------------------------
def build_sprint1_git(cfg, keys, remote_fn, workdir, now, secret=""):
    limit = now - timedelta(minutes=10)
    days = cfg.s1_days
    for kind, repo_name in cfg.repos.items():
        rng = random.Random(f"s1-{kind}")
        repo = GitRepo(Path(workdir) / repo_name, remote_fn(repo_name), secret)
        repo.init_new()

        lead = "diego" if kind == "backend" else "camila"
        if kind == "backend":
            repo.append("README.md", "# trk-backend\n\nAPI del proyecto Tracking Pilot (datos sintéticos).\n")
            repo.append("requirements.txt", "fastapi\nsqlalchemy\npydantic\n")
            repo.append("src/__init__.py", "")
        else:
            repo.append("README.md", "# trk-frontend\n\nAplicación web del proyecto Tracking Pilot (datos sintéticos).\n")
            repo.append("package.json", '{\n  "name": "trk-frontend",\n  "private": true\n}\n')
            repo.append("src/main.tsx", "export {};\n")
        repo.commit("chore: estructura inicial del proyecto", TEAM[lead]["name"], TEAM[lead]["email"],
                    at(cfg.sprint1_start - timedelta(days=3), 10, 0))

        actions = []
        for tid in SPRINT1_TICKETS:
            t = TICKETS[tid]
            if t["repo"] != kind:
                continue
            plan = SPRINT1_PLAN[tid]
            key, dev = keys[tid], t["dev"]
            branch = f"feature/{key}-{dev}"
            last = plan["end"] or len(days)
            n = plan["commits"]
            for i in range(n):
                d = plan["start"] + round(i * (last - plan["start"]) / max(n - 1, 1))
                when = at(days[d - 1], rng.randint(9, 16), rng.randint(0, 59))
                msg = f"{key}: " + COMMIT_TEMPLATES[i % len(COMMIT_TEMPLATES)].format(s=lower_first(t["summary"]))
                actions.append((when, "commit", tid, branch, msg))
            if plan["end"] and n:
                when = at(days[plan["end"] - 1], 17, rng.randint(0, 50))
                actions.append((when, "merge", tid, branch, f"Merge branch '{branch}'"))
        actions.sort(key=lambda a: a[0])

        # Si la siembra corre antes de que termine el Sprint 1, las acciones
        # "futuras" se comprimen justo antes del momento de ejecución.
        future = [i for i, a in enumerate(actions) if a[0] > limit]
        base = limit - timedelta(minutes=2 * len(future))
        for j, i in enumerate(future):
            actions[i] = (base + timedelta(minutes=2 * j),) + actions[i][1:]

        pending = set()
        for when, kind_, tid, branch, msg in actions:
            dev = TICKETS[tid]["dev"]
            name, email = TEAM[dev]["name"], TEAM[dev]["email"]
            if kind_ == "commit":
                repo.local_branch(branch)
                repo.append(ticket_path(tid), code_block(kind, rng, TICKETS[tid]["file"].lower()))
                repo.commit(msg, name, email, when)
                pending.add(branch)
            else:
                repo.merge_local(branch, msg, name, email, when)
                pending.discard(branch)
        repo.git("checkout", "-q", "main")
        repo.push("main")
        for branch in sorted(pending):
            repo.push(branch)
        log(f"    {repo_name}: {sum(1 for a in actions if a[1] == 'commit')} commits, "
            f"{sum(1 for a in actions if a[1] == 'merge')} merges, {len(pending)} ramas sin terminar.")


# --------------------------------------------------------------------------
def run(cfg, jira, gh, remote_fn, workdir, now, ctx, secret=""):
    board, types, users, pk = ctx["board_id"], ctx["types"], ctx["users"], cfg.project_key
    keys = {}

    def create(tid):
        t = TICKETS[tid]
        key = jira.create_issue(pk, types[t["type"]], t["summary"], description(tid), users[t["dev"]])
        jira.set_estimate(key, board, t["sp"])
        keys[tid] = key
        return key

    log("3/6 Creando Sprint 1 y sus tickets en Jira...")
    s1_days, s2_days = cfg.s1_days, cfg.s2_days
    s1 = jira.create_sprint(board, f"{pk} Sprint 1", at(s1_days[0], 9), at(s1_days[-1], 18), SPRINT1_GOAL)
    for tid in SPRINT1_TICKETS:
        create(tid)
    jira.move_to_sprint(s1, [keys[t] for t in SPRINT1_TICKETS])
    jira.update_sprint(s1, state="active", startDate=at(s1_days[0], 9), endDate=at(s1_days[-1], 18))
    log(f"    {len(SPRINT1_TICKETS)} tickets creados ({keys[SPRINT1_TICKETS[0]]} a {keys[SPRINT1_TICKETS[-1]]}).")

    log("4/6 Subiendo historial del Sprint 1 a GitHub...")
    build_sprint1_git(cfg, keys, remote_fn, workdir, now, secret)

    log("5/6 Actualizando estados y cerrando el Sprint 1...")
    for tid in sorted(SPRINT1_TICKETS, key=lambda t: SPRINT1_PLAN[t]["end"] or 99):
        jira.transition(keys[tid], "inprogress")
        if SPRINT1_PLAN[tid]["end"]:
            jira.transition(keys[tid], "done")
    jira.update_sprint(s1, state="closed")

    log("6/6 Planeando el Sprint 2...")
    s2 = jira.create_sprint(board, f"{pk} Sprint 2", at(s2_days[0], 9), at(s2_days[-1], 18), SPRINT2_GOAL)
    for tid in SPRINT2_PLANNED:
        create(tid)
    jira.move_to_sprint(s2, [keys[t] for t in SPRINT2_PLANNED + CARRYOVER])
    committed = sum(TICKETS[t]["sp"] for t in SPRINT2_PLANNED + CARRYOVER)
    log(f"    Sprint 2 planeado con {len(SPRINT2_PLANNED) + len(CARRYOVER)} tickets ({committed} SP), "
        f"incluye {len(CARRYOVER)} arrastrados del Sprint 1.")

    return {
        "version": 1,
        "project_key": pk,
        "sprint2_start": cfg.sprint2_start.isoformat(),
        "board_id": board,
        "types": types,
        "users": users,
        "sprints": {"s1": s1, "s2": s2},
        "tickets": keys,
        "prs": {},
        "commit_counts": {t: SPRINT1_PLAN[t]["commits"] for t in CARRYOVER},
        "days_done": [],
        "progress": {},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="solo verificar, sin crear nada")
    ap.add_argument("--force", action="store_true", help="continuar aunque existan tickets en Jira")
    args = ap.parse_args()

    cfg = get_config()
    jira = Jira(cfg.jira_base_url, cfg.jira_email, cfg.jira_token)
    gh = GitHub(cfg.gh_owner, cfg.gh_token)
    if cfg.state_path.exists() and not args.check:
        raise SystemExit("Ya existe state.json: la siembra ya se ejecutó. Si quieres repetirla, "
                         "sigue la sección 'Empezar de cero' del README.")

    ctx = preflight(cfg, jira, gh, force=args.force)
    log(f"\nCalendario: Sprint 1 del {cfg.sprint1_start} al {cfg.sprint1_end}; "
        f"Sprint 2 del {cfg.sprint2_start} al {cfg.sprint2_end} ({len(cfg.s2_days)} días hábiles).")
    if args.check:
        log("\nVerificación completa. Todo está listo para la siembra.")
        return

    workdir = ROOT / "_work"
    try:
        state = run(cfg, jira, gh, gh.remote_url, workdir, datetime.now(BOG), ctx, secret=cfg.gh_token)
    finally:
        rmtree(workdir)
    cfg.state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    log("\nSiembra completa. Se generó state.json; súbelo junto con el resto de trk-simulator.")


if __name__ == "__main__":
    main()
