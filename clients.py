"""Clientes mínimos para las APIs REST de Jira Cloud y GitHub."""
import time

import requests

CATEGORY = {"todo": "new", "inprogress": "indeterminate", "done": "done"}
TYPE_ALIASES = {
    "story": ["story", "historia"],
    "bug": ["bug", "error", "fallo", "defecto"],
    "task": ["task", "tarea"],
}


class ApiError(RuntimeError):
    pass


def _request(session, method, url, retries=4, **kw):
    for attempt in range(retries):
        r = session.request(method, url, timeout=60, **kw)
        if r.status_code in (429, 502, 503, 504) and attempt < retries - 1:
            time.sleep(int(r.headers.get("Retry-After", 2 * (attempt + 1))))
            continue
        if r.status_code >= 400:
            raise ApiError(f"{method} {url} -> {r.status_code}: {r.text[:800]}")
        return r.json() if r.content else {}


def adf(paragraphs, author=None):
    """Convierte texto a Atlassian Document Format."""
    content = []
    for i, p in enumerate(paragraphs):
        nodes = []
        if author and i == 0:
            nodes.append({"type": "text", "text": f"{author}: ", "marks": [{"type": "strong"}]})
        nodes.append({"type": "text", "text": p})
        content.append({"type": "paragraph", "content": nodes})
    return {"type": "doc", "version": 1, "content": content}


class Jira:
    def __init__(self, base_url, email, token):
        self.base = base_url
        self.s = requests.Session()
        self.s.auth = (email, token)
        self.s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

    def req(self, method, path, **kw):
        return _request(self.s, method, self.base + path, **kw)

    # ----- descubrimiento -----
    def myself(self):
        return self.req("GET", "/rest/api/3/myself")

    def project(self, key):
        return self.req("GET", f"/rest/api/3/project/{key}")

    def issue_keys(self, project_key):
        keys, token = [], None
        while True:
            params = {"jql": f"project = {project_key}", "maxResults": 100, "fields": "summary"}
            if token:
                params["nextPageToken"] = token
            data = self.req("GET", "/rest/api/3/search/jql", params=params)
            keys += [i["key"] for i in data.get("issues", [])]
            token = data.get("nextPageToken")
            if not token or data.get("isLast", True):
                return keys

    def find_user(self, project_key, display_name):
        users = self.req("GET", "/rest/api/3/user/assignable/search",
                         params={"project": project_key, "query": display_name, "maxResults": 50})
        for u in users:
            if u.get("displayName", "").strip().lower() == display_name.lower():
                return u["accountId"]
        return None

    def scrum_board(self, project_key):
        data = self.req("GET", "/rest/agile/1.0/board", params={"projectKeyOrId": project_key, "type": "scrum"})
        boards = data.get("values", [])
        return boards[0]["id"] if boards else None

    def estimation_field(self, board_id):
        cfg = self.req("GET", f"/rest/agile/1.0/board/{board_id}/configuration")
        return cfg.get("estimation", {}).get("field", {}).get("fieldId")

    def issue_type_ids(self, project):
        found = {}
        for it in project.get("issueTypes", []):
            if it.get("subtask"):
                continue
            names = {it.get("name", "").lower(), it.get("untranslatedName", "").lower()}
            for kind, aliases in TYPE_ALIASES.items():
                if kind not in found and names & set(aliases):
                    found[kind] = it["id"]
        return found

    # ----- tickets -----
    def create_issue(self, project_key, type_id, summary, description, assignee_id):
        body = {"fields": {
            "project": {"key": project_key},
            "issuetype": {"id": type_id},
            "summary": summary,
            "description": adf(description),
            "assignee": {"accountId": assignee_id},
        }}
        return self.req("POST", "/rest/api/3/issue", json=body)["key"]

    def set_estimate(self, key, board_id, value):
        self.req("PUT", f"/rest/agile/1.0/issue/{key}/estimation",
                 params={"boardId": board_id}, json={"value": str(value)})

    def transition(self, key, target):
        cat = CATEGORY[target]
        data = self.req("GET", f"/rest/api/3/issue/{key}/transitions")
        for t in data.get("transitions", []):
            if t["to"]["statusCategory"]["key"] == cat:
                self.req("POST", f"/rest/api/3/issue/{key}/transitions", json={"transition": {"id": t["id"]}})
                return
        raise ApiError(f"No hay transición de {key} hacia la categoría '{cat}'.")

    def comment(self, key, author, text):
        self.req("POST", f"/rest/api/3/issue/{key}/comment", json={"body": adf([text], author=author)})

    def add_label(self, key, label):
        self.req("PUT", f"/rest/api/3/issue/{key}", json={"update": {"labels": [{"add": label}]}})

    def delete_issue(self, key):
        self.req("DELETE", f"/rest/api/3/issue/{key}", params={"deleteSubtasks": "true"})

    # ----- sprints -----
    def create_sprint(self, board_id, name, start, end, goal):
        body = {"name": name, "originBoardId": board_id, "goal": goal,
                "startDate": start.isoformat(timespec="milliseconds"),
                "endDate": end.isoformat(timespec="milliseconds")}
        return self.req("POST", "/rest/agile/1.0/sprint", json=body)["id"]

    def update_sprint(self, sprint_id, **fields):
        for k in ("startDate", "endDate"):
            if k in fields:
                fields[k] = fields[k].isoformat(timespec="milliseconds")
        self.req("POST", f"/rest/agile/1.0/sprint/{sprint_id}", json=fields)

    def move_to_sprint(self, sprint_id, keys):
        for i in range(0, len(keys), 50):
            self.req("POST", f"/rest/agile/1.0/sprint/{sprint_id}/issue", json={"issues": keys[i:i + 50]})

    def board_sprints(self, board_id):
        out, start = [], 0
        while True:
            data = self.req("GET", f"/rest/agile/1.0/board/{board_id}/sprint", params={"startAt": start, "maxResults": 50})
            out += data.get("values", [])
            if data.get("isLast", True):
                return out
            start += 50

    def delete_sprint(self, sprint_id):
        self.req("DELETE", f"/rest/agile/1.0/sprint/{sprint_id}")


class GitHub:
    API = "https://api.github.com"

    def __init__(self, owner, token):
        self.owner = owner
        self.token = token
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def req(self, method, path, **kw):
        return _request(self.s, method, self.API + path, **kw)

    def remote_url(self, repo):
        return f"https://{self.owner}:{self.token}@github.com/{self.owner}/{repo}.git"

    def whoami(self):
        return self.req("GET", "/user")["login"]

    def repo_is_empty(self, repo):
        self.req("GET", f"/repos/{self.owner}/{repo}")  # falla si no existe o no hay acceso
        r = self.s.get(f"{self.API}/repos/{self.owner}/{repo}/commits", params={"per_page": 1}, timeout=60)
        return r.status_code == 409

    def create_pr(self, repo, head, title, body):
        for attempt in range(4):
            try:
                return self.req("POST", f"/repos/{self.owner}/{repo}/pulls",
                                json={"title": title, "head": head, "base": "main", "body": body})["number"]
            except ApiError:
                if attempt == 3:
                    raise
                time.sleep(3)  # GitHub a veces tarda en ver una rama recién subida

    def comment(self, repo, number, body):
        self.req("POST", f"/repos/{self.owner}/{repo}/issues/{number}/comments", json={"body": body})

    def merge_pr(self, repo, number, title):
        self.req("PUT", f"/repos/{self.owner}/{repo}/pulls/{number}/merge",
                 json={"merge_method": "merge", "commit_title": title})
