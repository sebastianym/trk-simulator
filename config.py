"""Configuración del piloto y calendario de los sprints.

Los valores no secretos tienen un valor por defecto. Los secretos (tokens)
se leen del archivo .env (en tu computador) o de los Secrets de GitHub
Actions (en el simulador diario). Nunca se escriben en el código.
"""
import os
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Bogotá no tiene horario de verano, así que un desfase fijo es exacto
# y evita depender de la base de datos de zonas horarias en Windows.
BOG = timezone(timedelta(hours=-5), name="America/Bogota")

# Festivos de Colombia que caen dentro del periodo del piloto.
HOLIDAYS = {date(2026, 10, 12)}  # Día de la Raza (lunes festivo)


def load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def working_days(start: date, end: date) -> list[date]:
    """Días hábiles (lunes a viernes, sin festivos) entre start y end, inclusive."""
    days, d = [], start
    while d <= end:
        if d.weekday() < 5 and d not in HOLIDAYS:
            days.append(d)
        d += timedelta(days=1)
    return days


def at(d: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(d, time(hour, minute), tzinfo=BOG)


@dataclass
class Config:
    jira_base_url: str
    jira_email: str
    jira_token: str
    project_key: str
    gh_owner: str
    gh_token: str
    sprint2_start: date
    repos: dict = field(default_factory=lambda: {"backend": "trk-backend", "frontend": "trk-frontend"})
    state_path: Path = ROOT / "state.json"

    # Calendario: Sprint 1 son las dos semanas anteriores al Sprint 2.
    @property
    def sprint1_start(self) -> date:
        return self.sprint2_start - timedelta(days=14)

    @property
    def sprint1_end(self) -> date:
        return self.sprint2_start - timedelta(days=3)

    @property
    def sprint2_end(self) -> date:
        return self.sprint2_start + timedelta(days=11)

    @property
    def s1_days(self) -> list[date]:
        return working_days(self.sprint1_start, self.sprint1_end)

    @property
    def s2_days(self) -> list[date]:
        return working_days(self.sprint2_start, self.sprint2_end)


def get_config(require_secrets: bool = True) -> Config:
    load_dotenv()
    env = os.environ
    missing = [k for k in ("JIRA_EMAIL", "JIRA_API_TOKEN", "GH_PAT") if not env.get(k)]
    if require_secrets and missing:
        raise SystemExit(
            "Faltan variables: " + ", ".join(missing)
            + ".\nCopia .env.example como .env y complétalo (o configura los Secrets en GitHub)."
        )
    start = date.fromisoformat(env.get("SPRINT2_START", "2026-10-05"))
    if start.weekday() != 0:
        raise SystemExit("SPRINT2_START debe ser un lunes (formato AAAA-MM-DD).")
    return Config(
        jira_base_url=env.get("JIRA_BASE_URL", "https://piloto-prueba.atlassian.net").rstrip("/"),
        jira_email=env.get("JIRA_EMAIL", ""),
        jira_token=env.get("JIRA_API_TOKEN", ""),
        project_key=env.get("JIRA_PROJECT_KEY", "TRK"),
        gh_owner=env.get("GH_OWNER", "sebastianym"),
        gh_token=env.get("GH_PAT", ""),
        sprint2_start=start,
    )
