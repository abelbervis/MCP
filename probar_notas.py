"""Recorre todo el servidor de notas: tools, resources y prompts.

Usa una base de datos temporal para no tocar notas.db.
"""

import sys
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DB_PRUEBA = Path("/tmp/opencode/notas_prueba.db")
SERVIDOR = StdioServerParameters(
    command=sys.executable,
    args=["src/notas.py"],
    env={"NOTAS_DB": str(DB_PRUEBA)},
)


def titulo(texto: str) -> None:
    print(f"\n=== {texto} ===")


async def main() -> None:
    DB_PRUEBA.unlink(missing_ok=True)  # empezar de cero en cada ejecución

    async with stdio_client(SERVIDOR) as (leer, escribir):
        async with ClientSession(leer, escribir) as sesion:
            info = await sesion.initialize()
            print(f"Conectado a: {info.server_info.name} v{info.server_info.version}")
            print(f"Instrucciones: {info.instructions}")

            titulo("Catálogo del servidor")
            for tool in (await sesion.list_tools()).tools:
                print(f"tool    {tool.name}")
            for recurso in (await sesion.list_resources()).resources:
                print(f"resource {recurso.uri}  ({recurso.mime_type})")
            for plantilla in (await sesion.list_resource_templates()).resource_templates:
                print(f"template {plantilla.uri_template}")
            for prompt in (await sesion.list_prompts()).prompts:
                print(f"prompt  {prompt.name}")

            titulo("Crear notas (tools/call)")
            for texto in ["Comprar café", "Terminar el paso 2 de MCP", "Llamar al dentista"]:
                resultado = await sesion.call_tool("crear_nota", {"texto": texto})
                print(f"  creada: {resultado.structured_content}")

            titulo("Listar pendientes")
            resultado = await sesion.call_tool("listar_notas", {})
            for nota in resultado.structured_content["result"]:
                print(f"  #{nota['id']} {nota['texto']}")

            titulo("Leer resource notas://hoy (resources/read)")
            recurso = await sesion.read_resource("notas://hoy")
            print(recurso.contents[0].text)

            titulo("Leer resource con plantilla notas://nota/2")
            recurso = await sesion.read_resource("notas://nota/2")
            print(recurso.contents[0].text)

            titulo("Pedir el prompt resumen_diario (prompts/get)")
            prompt = await sesion.get_prompt("resumen_diario", {"estilo": "breve"})
            print(f"rol: {prompt.messages[0].role}")
            print(prompt.messages[0].content.text)

            titulo("Completar la nota 2")
            resultado = await sesion.call_tool("completar_nota", {"nota_id": 2})
            print(resultado.structured_content)

            titulo("Borrar la nota 3")
            resultado = await sesion.call_tool("borrar_nota", {"nota_id": 3})
            print(resultado.structured_content)

            titulo("Pendientes después de completar y borrar")
            resultado = await sesion.call_tool("listar_notas", {})
            print([nota["texto"] for nota in resultado.structured_content["result"]])

            titulo("Error esperado: completar una nota que no existe")
            resultado = await sesion.call_tool("completar_nota", {"nota_id": 999})
            print(f"is_error: {resultado.is_error}")
            print(resultado.content[0].text)


if __name__ == "__main__":
    anyio.run(main)
