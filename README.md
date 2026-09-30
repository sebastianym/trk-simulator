# trk-simulator

Generador de datos sintéticos para el piloto de seguimiento de desarrollo en **Amazon Quick**.
Simula a un equipo de 6 desarrolladores trabajando en Jira (`TRK`) y GitHub (`trk-backend`, `trk-frontend`).

> Este repositorio **no es parte de la solución**: representa el "mundo real" que la solución observa.
> En producción, este papel lo cumplen los desarrolladores reales.

## Calendario

| Sprint | Fechas | Cómo se genera |
|---|---|---|
| Sprint 1 | 21 sep – 2 oct 2026 | `seed.py`, una sola vez (historial con fechas reales en Git) |
| Sprint 2 | 5 oct – 16 oct 2026 (9 días hábiles; 12 oct festivo) | `simulate_day.py`, cada día hábil a las 18:30 vía GitHub Actions |

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `scenario.py` | Equipo, tickets y guion día a día. Es el único archivo que se edita para cambiar la historia. |
| `seed.py` | Siembra inicial (Sprint 1 cerrado + Sprint 2 planeado). |
| `simulate_day.py` | Aplica la actividad de cada día del Sprint 2. Idempotente. |
| `dryrun.py` | Prueba completa local sin tocar Jira ni GitHub. |
| `reset_jira.py` | Borra tickets y sprints de TRK para empezar de cero. |
| `state.json` | Avance del simulador (se genera en la siembra; no editar a mano). |

## Convenciones que usa el escenario

- Ramas: `feature/TRK-12-ana` · correcciones: `fix/TRK-12-ana`
- Commits y títulos de PR: `TRK-12: descripción`
- Revisiones: comentario en el PR con la marca `<!-- review: approved by <dev> -->`
- Autor del PR: marca `<!-- author: <dev> -->` en el cuerpo (todos los PRs los crea la cuenta dueña del token)
- Las excepciones a estas reglas son intencionales: son los casos que el reporte debe detectar.

## Modo demo

En GitHub → Actions → *Simulador diario TRK* → *Run workflow*, elige `ejecutar` y escribe un día en
`hasta_dia` para adelantar el sprint. Las transiciones de Jira quedarán con la fecha del momento
en que se ejecuten.

## Empezar de cero

1. `python reset_jira.py --yes`
2. Borra y vuelve a crear vacíos `trk-backend` y `trk-frontend` en GitHub.
3. Borra `state.json` y ejecuta de nuevo `python seed.py`.
