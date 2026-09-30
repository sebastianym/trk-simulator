"""Borra TODOS los tickets y sprints del espacio TRK para empezar de cero.

Uso: python reset_jira.py --yes
"""
import argparse

from clients import ApiError, Jira
from config import get_config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="confirmar el borrado")
    args = ap.parse_args()
    cfg = get_config()
    jira = Jira(cfg.jira_base_url, cfg.jira_email, cfg.jira_token)

    keys = jira.issue_keys(cfg.project_key)
    board = jira.scrum_board(cfg.project_key)
    sprints = jira.board_sprints(board) if board else []
    print(f"Se borrarán {len(keys)} tickets y {len(sprints)} sprints de {cfg.project_key}.")
    if not args.yes:
        print("Nada se borró. Repite con --yes para confirmar.")
        return
    for k in keys:
        jira.delete_issue(k)
    for s in sprints:
        try:
            jira.delete_sprint(s["id"])
        except ApiError as e:
            print(f"  No se pudo borrar el sprint '{s['name']}': {e}")
    print("Listo. Recuerda borrar también state.json.")


if __name__ == "__main__":
    main()
