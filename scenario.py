"""Escenario sintético del piloto: equipo, tickets de ambos sprints y el
guion día a día del Sprint 2.

Perfiles de los devs (lo que el reporte debería detectar):
  Ana     -> La referencia: todo trazable, PRs revisados a tiempo.
  Bruno   -> "Done sin evidencia": cierra tickets sin commits ni PR.
  Camila  -> "Código huérfano": commits y un PR sin clave de ticket.
  Diego   -> "PRs estancados": PR sin revisión 6 días, otro mergeado sin review.
  Elena   -> "Sobrecargada": 16 SP comprometidos, WIP alto, arrastre.
  Felipe  -> "Silencioso": ticket en progreso días sin actividad, bloqueo tardío.
"""

TEAM = {
    "ana":    {"name": "Ana Gómez",      "email": "ana.gomez@example.com",      "repo": "backend"},
    "bruno":  {"name": "Bruno Díaz",     "email": "bruno.diaz@example.com",     "repo": "backend"},
    "camila": {"name": "Camila Rojas",   "email": "camila.rojas@example.com",   "repo": "frontend"},
    "diego":  {"name": "Diego Martínez", "email": "diego.martinez@example.com", "repo": "backend"},
    "elena":  {"name": "Elena Castro",   "email": "elena.castro@example.com",   "repo": "frontend"},
    "felipe": {"name": "Felipe Torres",  "email": "felipe.torres@example.com",  "repo": "backend"},
}

SPRINT1_GOAL = "Autenticación, catálogo y carrito base"
SPRINT2_GOAL = "Checkout, pagos y notificaciones"


def T(summary, type_, sp, dev, module, file, repo=None):
    return {"summary": summary, "type": type_, "sp": sp, "dev": dev,
            "module": module, "file": file, "repo": repo or TEAM[dev]["repo"]}


TICKETS = {
    # ---------------- Sprint 1 ----------------
    "S1-01": T("API de registro de usuarios", "story", 3, "ana", "usuarios", "registro"),
    "S1-02": T("Autenticación con JWT y refresh tokens", "story", 5, "ana", "auth", "jwt"),
    "S1-03": T("Modelo de datos de productos", "story", 3, "bruno", "catalogo", "modelo_producto"),
    "S1-04": T("Endpoint de búsqueda de productos", "story", 5, "bruno", "catalogo", "busqueda"),
    "S1-05": T("Pantalla de inicio de sesión", "story", 5, "camila", "auth", "LoginPage"),
    "S1-06": T("Listado del catálogo de productos", "story", 3, "camila", "catalogo", "CatalogList"),
    "S1-07": T("Integración con pasarela de pagos en sandbox", "story", 5, "diego", "pagos", "pasarela"),
    "S1-08": T("Configurar pipeline de integración continua", "task", 2, "diego", "ci", "pipeline"),
    "S1-09": T("Vista de detalle de producto", "story", 5, "elena", "producto", "ProductDetail"),
    "S1-10": T("Carrito de compras (interfaz)", "story", 5, "elena", "carrito", "CartView"),
    "S1-11": T("API del carrito de compras", "story", 5, "felipe", "carrito", "carrito_api"),
    "S1-12": T("Migraciones iniciales de base de datos", "task", 3, "felipe", "db", "migraciones"),
    "S1-13": T("Error 500 al buscar con caracteres especiales", "bug", 2, "bruno", "catalogo", "busqueda_fix"),
    "S1-14": T("Documentación OpenAPI inicial", "task", 2, "ana", "docs", "openapi"),
    "S1-15": T("Servicio de inventario", "story", 3, "felipe", "inventario", "inventario"),
    # ---------------- Sprint 2 (planeados) ----------------
    "S2-01": T("API de creación de pedidos", "story", 5, "ana", "pedidos", "crear_pedido"),
    "S2-02": T("Validación de stock al confirmar pedido", "story", 3, "ana", "pedidos", "validar_stock"),
    "S2-03": T("Cálculo de impuestos y costo de envío", "story", 5, "bruno", "impuestos", "calculo"),
    "S2-04": T("Cupones de descuento", "story", 3, "bruno", "cupones", "cupones"),
    "S2-05": T("Timeout en consulta del catálogo", "bug", 2, "bruno", "catalogo", "timeout_fix"),
    "S2-06": T("Flujo de checkout (interfaz)", "story", 5, "camila", "checkout", "CheckoutFlow"),
    "S2-07": T("Página de confirmación de pedido", "story", 3, "camila", "checkout", "OrderConfirmation"),
    "S2-08": T("Webhooks de la pasarela de pagos", "story", 5, "diego", "pagos", "webhooks"),
    "S2-09": T("Reintentos automáticos de pagos fallidos", "story", 3, "diego", "pagos", "reintentos"),
    "S2-10": T("Logs estructurados en el servicio de pagos", "task", 2, "diego", "observabilidad", "logs_pagos"),
    "S2-11": T("Historial de pedidos del cliente", "story", 5, "elena", "pedidos", "OrderHistory"),
    "S2-12": T("Centro de notificaciones en la app", "story", 3, "elena", "notificaciones", "NotificationCenter"),
    "S2-13": T("Accesibilidad del flujo de checkout", "story", 3, "elena", "accesibilidad", "CheckoutA11y"),
    "S2-14": T("Servicio de notificaciones por correo", "story", 5, "felipe", "notificaciones", "email_service"),
    "S2-15": T("Pruebas de carga del API de pedidos", "task", 2, "ana", "pedidos", "pruebas_carga"),
    # ---------------- Agregados a mitad del Sprint 2 ----------------
    "X1": T("Pedidos duplicados al hacer doble clic en Pagar", "bug", 3, "ana", "pedidos", "idempotencia"),
    "X2": T("Banner promocional de temporada (solicitud comercial)", "story", 3, "camila", "marketing", "PromoBanner"),
}

SPRINT1_TICKETS = [k for k in TICKETS if k.startswith("S1-")]
SPRINT2_PLANNED = [k for k in TICKETS if k.startswith("S2-")]
CARRYOVER = ["S1-10", "S1-15"]  # quedan sin terminar en el Sprint 1

# Plan del Sprint 1 (histórico). Días = días hábiles 1..10 del sprint.
# end=None -> no se termina (arrastre al Sprint 2).
SPRINT1_PLAN = {
    "S1-01": {"start": 1, "end": 3, "commits": 3},
    "S1-02": {"start": 3, "end": 7, "commits": 4},
    "S1-14": {"start": 8, "end": 9, "commits": 2},
    "S1-03": {"start": 1, "end": 2, "commits": 2},
    "S1-04": {"start": 3, "end": 7, "commits": 0},   # Bruno: primer "Done sin evidencia"
    "S1-13": {"start": 8, "end": 9, "commits": 2},
    "S1-05": {"start": 1, "end": 5, "commits": 4},
    "S1-06": {"start": 6, "end": 9, "commits": 3},
    "S1-07": {"start": 1, "end": 6, "commits": 4},
    "S1-08": {"start": 7, "end": 8, "commits": 2},
    "S1-09": {"start": 1, "end": 5, "commits": 3},
    "S1-10": {"start": 6, "end": None, "commits": 3},
    "S1-11": {"start": 1, "end": 5, "commits": 4},
    "S1-12": {"start": 6, "end": 8, "commits": 2},
    "S1-15": {"start": 9, "end": None, "commits": 1},
}


def ev(kind, **kw):
    return {"kind": kind, **kw}


def c(t, **kw):
    return ev("commit", t=t, **kw)


def tr(t, to):
    return ev("transition", t=t, to=to)


def pr(t, **kw):
    return ev("open_pr", t=t, **kw)


def rv(p, by, approved=True, text=None):
    return ev("review", pr=p, by=by, approved=approved, text=text)


def mg(p):
    return ev("merge", pr=p)


HEADER_PR = {"pr": "header", "dev": "camila", "repo": "frontend", "branch": "feature/rediseno-header"}

# Guion del Sprint 2. Clave = día hábil del sprint (el 12 de octubre es festivo).
SPRINT2_DAYS = {
    1: [
        ev("start_sprint"),
        tr("S2-01", "inprogress"), c("S2-01"),
        tr("S2-03", "inprogress"),
        tr("S2-06", "inprogress"),
        tr("S2-08", "inprogress"), c("S2-08"),
        c("S1-10"),
        c("S1-15"),
    ],
    2: [
        c("S2-01"),
        tr("S2-05", "inprogress"), c("S2-05"),
        c("S2-06"),
        ev("commit", dev="camila", repo="frontend", branch="main",
           msg="ajustes de estilos generales", path="src/styles/global.css"),
        c("S2-08"), pr("S2-08"),
        c("S1-10"),
        c("S1-15"), pr("S1-15"),
    ],
    3: [
        ev("create", t="X1"), tr("X1", "inprogress"), c("X1"), pr("X1"),
        c("S2-01"), pr("S2-01"),
        pr("S2-05"), rv("S2-05", "ana"), mg("S2-05"), tr("S2-05", "done"),
        ev("commit", dev="camila", repo="frontend", branch=HEADER_PR["branch"],
           msg="rediseño del header con el nuevo logo", path="src/layout/Header.tsx"),
        tr("S2-09", "inprogress"), c("S2-09"),
        pr("S1-10"),
        rv("S1-15", "diego"), mg("S1-15"), tr("S1-15", "done"),
        tr("S2-14", "inprogress"), c("S2-14"),
    ],
    4: [
        rv("S2-01", "diego"), mg("S2-01"), tr("S2-01", "done"),
        rv("X1", "bruno"), mg("X1"), tr("X1", "done"),
        tr("S2-02", "inprogress"), c("S2-02"),
        tr("S2-03", "done"),                                   # Bruno: sin commits ni PR
        c("S2-06"),
        ev("commit", dev="camila", repo="frontend", branch=HEADER_PR["branch"],
           msg="ajustes responsivos del header", path="src/layout/Header.tsx"),
        ev("open_pr", title="Rediseño del header", **HEADER_PR),  # PR sin ticket
        c("S2-09"), pr("S2-09"),
        rv("S1-10", "camila"), mg("S1-10"), tr("S1-10", "done"),
        tr("S2-11", "inprogress"),
    ],
    5: [
        c("S2-02"), pr("S2-02"), rv("S2-02", "bruno"), mg("S2-02"), tr("S2-02", "done"),
        tr("S2-04", "inprogress"),
        pr("S2-06"),
        rv("header", "elena"), mg("header"),
        mg("S2-09"), tr("S2-09", "done"),                     # Diego: merge sin revisión
        c("S2-11"),
    ],
    6: [
        tr("S2-02", "inprogress"),                            # Ticket reabierto
        ev("comment", t="S2-02", by="ana",
           text="QA reportó que la validación de stock no considera las variantes (talla y color). Reabro para corregir."),
        c("S2-02", branch="fix/{key}-{dev}", msg="corrige validación de stock para variantes"),
        pr("S2-02", pr="S2-02-fix", branch="fix/{key}-{dev}"),
        tr("S2-04", "done"),                                   # Bruno: sin commits ni PR
        ev("create", t="X2"),
        rv("S2-06", "elena", approved=False,
           text="Faltan validaciones del formulario de dirección de envío y el manejo del error de pago."),
        c("S2-06", msg="agrega validaciones del formulario de envío"),
        ev("commit", dev="camila", repo="frontend", branch="main",
           msg="corrige texto del footer", path="src/layout/Footer.tsx"),
        tr("S2-10", "inprogress"), c("S2-10"), pr("S2-10"),
        c("S2-11"),
        ev("comment", t="S2-11", by="elena",
           text="Voy atrasada con esta historia. Este sprint tengo más carga de la que alcanzo a cubrir."),
    ],
    7: [
        rv("S2-02-fix", "diego"), mg("S2-02-fix"), tr("S2-02", "done"),
        tr("S2-15", "inprogress"), c("S2-15"),
        rv("S2-06", "elena"), mg("S2-06"), tr("S2-06", "done"),
        tr("S2-07", "inprogress"),
        tr("X2", "inprogress"), c("X2"),
        rv("S2-10", "bruno"), mg("S2-10"), tr("S2-10", "done"),
        c("S2-11"),
        tr("S2-12", "inprogress"),
        ev("comment", t="S2-14", by="ana",
           text="Felipe, veo este ticket sin movimiento desde la semana pasada. ¿Necesitas apoyo?"),
    ],
    8: [
        c("S2-15"), pr("S2-15"), rv("S2-15", "camila"),
        c("S2-03", msg="ajuste en el cálculo del costo de envío"),  # commit después de cerrar
        c("S2-07"),
        pr("X2"),
        rv("S2-08", "ana"),                                   # primera revisión tras 6 días
        c("S2-11"), pr("S2-11"),
        c("S2-12"),
        ev("comment", t="S2-14", by="felipe",
           text="Estoy bloqueado: no tengo las credenciales SMTP del ambiente de pruebas. Las pedí a infraestructura hace varios días."),
        ev("label", t="S2-14", label="bloqueado"),
    ],
    9: [
        mg("S2-15"), tr("S2-15", "done"),
        pr("S2-07"),
        rv("X2", "elena"), mg("X2"), tr("X2", "done"),
        mg("S2-08"), tr("S2-08", "done"),
        c("S2-11", msg="ajustes de paginación del historial"),
        c("S2-14"),
    ],
}

COMMIT_TEMPLATES = [
    "estructura inicial de {s}",
    "lógica principal de {s}",
    "validaciones y manejo de errores en {s}",
    "pruebas unitarias para {s}",
    "ajustes por revisión de código en {s}",
    "refactor menor en {s}",
]


def lower_first(s: str) -> str:
    if not s or (len(s) > 1 and s[1].isupper()):  # respeta siglas como "API"
        return s
    return s[0].lower() + s[1:]


def ticket_path(tid: str) -> str:
    t = TICKETS[tid]
    ext = ".py" if t["repo"] == "backend" else ".tsx"
    return f"src/{t['module']}/{t['file']}{ext}"
