"""Servidor MCP de notas/tareas (paso 2).

Conceptos nuevos frente al paso 1:
- tools con ESTADO (SQLite): crear, listar, completar, borrar
- resources: datos de solo lectura que el cliente puede leer por URI
- prompts: plantillas que el cliente puede pedir y rellenar

Transporte: stdio (igual que el paso 1).
"""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import MCPServer, UserMessage
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from pydantic import BaseModel

# La ruta se puede cambiar con la variable de entorno NOTAS_DB.
# Así las pruebas no ensucian tu base de datos real.
DB = Path(os.environ.get("NOTAS_DB", Path(__file__).resolve().parent.parent / "notas.db"))

mcp = MCPServer(
    "notas",
    version="0.1.0",
    instructions="Gestiona notas y tareas pendientes guardadas en SQLite.",
)


# ---------------------------------------------------------------------------
# Acceso a datos
# ---------------------------------------------------------------------------


class Nota(BaseModel):
    """El tipo de salida de las tools.

    Al anotar el retorno con un modelo, el SDK publica un output schema y
    devuelve `structuredContent` además del texto. Un `dict` suelto no lo hace.
    """

    id: int
    texto: str
    creada: str
    completada: bool
    completada_en: str | None = None


class NotaBorrada(BaseModel):
    id: int
    borrada: bool


@contextmanager
def conexion() -> Iterator[sqlite3.Connection]:
    """Abre una conexión por operación.

    SQLite no es thread-safe por defecto, y el SDK puede ejecutar cada tool
    en un hilo distinto. Una conexión por llamada evita sorpresas.
    """
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        with con:  # transacción: commit si todo sale bien, rollback si hay error
            yield con
    finally:
        con.close()


def init_db() -> None:
    with conexion() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS notas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                texto TEXT NOT NULL,
                creada TEXT NOT NULL,
                completada INTEGER NOT NULL DEFAULT 0,
                completada_en TEXT
            )
            """
        )


def a_nota(fila: sqlite3.Row) -> Nota:
    """Convierte una fila de SQLite en el modelo de salida."""
    return Nota(
        id=fila["id"],
        texto=fila["texto"],
        creada=fila["creada"],
        completada=bool(fila["completada"]),
        completada_en=fila["completada_en"],
    )


def ahora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def pendientes() -> list[sqlite3.Row]:
    with conexion() as con:
        return list(con.execute("SELECT * FROM notas WHERE completada = 0 ORDER BY id"))


# Al importar el módulo, la tabla existe. Así funciona igual con
# `mcp dev src/notas.py` que con `python src/notas.py`.
init_db()


# ---------------------------------------------------------------------------
# Tools: acciones que el modelo puede ejecutar
# ---------------------------------------------------------------------------


@mcp.tool()
def crear_nota(texto: str) -> Nota:
    """Crea una nota nueva y devuelve la nota creada."""
    texto = texto.strip()
    if not texto:
        raise ToolError("El texto de la nota no puede estar vacío.")

    creada = ahora()
    with conexion() as con:
        cur = con.execute(
            "INSERT INTO notas (texto, creada) VALUES (?, ?)", (texto, creada)
        )
        nota_id = cur.lastrowid

    return Nota(
        id=nota_id,
        texto=texto,
        creada=creada,
        completada=False,
        completada_en=None,
    )


@mcp.tool()
def listar_notas(solo_pendientes: bool = True) -> list[Nota]:
    """Lista las notas. Por defecto solo muestra las pendientes."""
    sql = "SELECT * FROM notas"
    if solo_pendientes:
        sql += " WHERE completada = 0"
    sql += " ORDER BY completada, id DESC"

    with conexion() as con:
        return [a_nota(fila) for fila in con.execute(sql)]


@mcp.tool()
def completar_nota(nota_id: int) -> Nota:
    """Marca una nota como completada."""
    with conexion() as con:
        cur = con.execute(
            "UPDATE notas SET completada = 1, completada_en = ? "
            "WHERE id = ? AND completada = 0",
            (ahora(), nota_id),
        )
        if cur.rowcount == 0:
            if con.execute("SELECT 1 FROM notas WHERE id = ?", (nota_id,)).fetchone():
                raise ToolError(f"La nota {nota_id} ya estaba completada.")
            raise ToolError(f"No existe ninguna nota con id {nota_id}.")

        fila = con.execute("SELECT * FROM notas WHERE id = ?", (nota_id,)).fetchone()

    return a_nota(fila)


@mcp.tool()
def borrar_nota(nota_id: int) -> NotaBorrada:
    """Borra una nota definitivamente."""
    with conexion() as con:
        cur = con.execute("DELETE FROM notas WHERE id = ?", (nota_id,))
        if cur.rowcount == 0:
            raise ToolError(f"No existe ninguna nota con id {nota_id}.")

    return NotaBorrada(id=nota_id, borrada=True)


# ---------------------------------------------------------------------------
# Resources: datos de solo lectura, identificados por URI
# ---------------------------------------------------------------------------


@mcp.resource("notas://hoy", name="Notas pendientes", mime_type="text/markdown")
def notas_de_hoy() -> str:
    """Vista markdown de todas las notas pendientes."""
    filas = pendientes()
    if not filas:
        return "# Notas pendientes\n\nNo hay notas pendientes. 🎉"

    lineas = [f"- [ ] #{fila['id']} {fila['texto']}" for fila in filas]
    return "# Notas pendientes\n\n" + "\n".join(lineas) + "\n"


@mcp.resource("notas://nota/{nota_id}", name="Nota", mime_type="text/markdown")
def nota_por_id(nota_id: str) -> str:
    """Detalle de una nota concreta. El {nota_id} de la URI llega como parámetro."""
    with conexion() as con:
        fila = con.execute("SELECT * FROM notas WHERE id = ?", (nota_id,)).fetchone()

    if fila is None:
        # En un resource el error "esperado" es ResourceNotFoundError;
        # ToolError es para tools. Una excepción cualquiera se trata como crash.
        raise ResourceNotFoundError(f"No existe ninguna nota con id {nota_id}.")

    estado = "completada" if fila["completada"] else "pendiente"
    return f"# Nota #{fila['id']}\n\n{fila['texto']}\n\n- Estado: {estado}\n- Creada: {fila['creada']}\n"


# ---------------------------------------------------------------------------
# Prompts: plantillas que el CLIENTE pide (no las ejecuta el servidor)
# ---------------------------------------------------------------------------


@mcp.prompt(title="Resumen diario")
def resumen_diario(estilo: Literal["breve", "detallado"] = "breve") -> list[UserMessage]:
    """Genera un prompt para que el modelo resuma tus notas pendientes."""
    filas = pendientes()
    if not filas:
        lista = "(no hay notas pendientes)"
    else:
        lista = "\n".join(f"- #{fila['id']}: {fila['texto']}" for fila in filas)

    if estilo == "breve":
        instruccion = "Resume en 3 líneas qué debería hacer hoy, por orden de prioridad."
    else:
        instruccion = (
            "Haz un plan detallado para hoy: agrupa las tareas por tema, "
            "estima el esfuerzo y propone un orden."
        )

    return [
        UserMessage(
            f"{instruccion}\n\nNotas pendientes:\n{lista}"
        )
    ]


if __name__ == "__main__":
    mcp.run()
