"""Servidor MCP mínimo (paso 1).

Transporte: stdio. El cliente lanza este proceso y habla JSON-RPC por
stdin/stdout.

Regla de oro del transporte stdio: NUNCA uses print() en el servidor.
Todo lo que escribas en stdout rompe el protocolo. Para depurar usa
logging (que escribe en stderr).
"""

import logging

from mcp.server.mcpserver import MCPServer

logging.basicConfig(level=logging.INFO)

# El nombre es lo que verá el cliente al conectarse.
mcp = MCPServer("demo", version="0.1.0")


@mcp.tool()
def saludar(nombre: str = "mundo") -> str:
    """Devuelve un saludo para `nombre`.

    Todo lo que el cliente necesita saber sale de esta función:
    - el nombre de la tool: `saludar`
    - la descripción: este docstring
    - el esquema de entrada: los type hints (nombre: str)
    - el tipo de salida: el type hint de retorno (-> str)
    """
    return f"¡Hola, {nombre}! Esto viene de una tool MCP."


if __name__ == "__main__":
    # Sin argumentos usa stdio, que es lo que queremos en local.
    mcp.run()
