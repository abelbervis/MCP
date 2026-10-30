"""Cliente mínimo para comprobar el servidor sin abrir el Inspector.

Hace lo mismo que hará OpenCode: lanza el servidor por stdio, hace el
handshake (initialize), lista las tools y llama a una.
"""

import sys

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVIDOR = StdioServerParameters(
    command=sys.executable,
    args=["src/servidor.py"],
)


async def main() -> None:
    async with stdio_client(SERVIDOR) as (leer, escribir):
        async with ClientSession(leer, escribir) as sesion:
            info = await sesion.initialize()
            print(f"Conectado a: {info.server_info.name} v{info.server_info.version}")
            print(f"Versión del protocolo: {info.protocol_version}")

            tools = await sesion.list_tools()
            print(f"Tools disponibles: {len(tools.tools)}")
            for tool in tools.tools:
                print(f"\n  - {tool.name}: {tool.description}")
                print(f"    esquema de entrada: {tool.input_schema}")

            resultado = await sesion.call_tool("saludar", {"nombre": "Abel"})
            print(f"\nResultado de saludar: {resultado.content[0].text}")


if __name__ == "__main__":
    anyio.run(main)
