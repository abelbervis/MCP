# Aprendiendo MCP en Python

## Paso 1 — Servidor mínimo

Un servidor MCP con una sola tool, hablando por **stdio**.

| Archivo | Para qué sirve |
|---|---|
| `src/servidor.py` | El servidor. Una tool: `saludar(nombre)`. |
| `probar_servidor.py` | Cliente de prueba: handshake, `tools/list`, `tools/call`. |
| `pyproject.toml` | Dependencias (`mcp[cli]`). |

### Probar

```bash
# 1. Cliente mínimo (no necesita navegador)
.venv/bin/python probar_servidor.py

# 2. Inspector visual de MCP (abre el navegador)
.venv/bin/mcp dev src/servidor.py
```

### Qué está pasando

1. El cliente **lanza** `src/servidor.py` como subproceso.
2. Hablan **JSON-RPC** por stdin/stdout.
3. `initialize` negocia versión y capabilities.
4. `tools/list` devuelve nombre, descripción y **JSON Schema** de cada tool.
5. `tools/call` ejecuta la función Python y devuelve el resultado.

El esquema no se escribe a mano: sale de los type hints. Por eso

```python
def saludar(nombre: str = "mundo") -> str:
```

se convierte en `{"nombre": {"type": "string", "default": "mundo"}}`.

### Reglas que conviene grabarse

- **Nunca `print()` en el servidor**: stdout es el canal del protocolo.
  Para depurar, `logging` (va a stderr).
- **mcp 2.x**: `FastMCP` ahora se llama `MCPServer`
  (`from mcp.server.mcpserver import MCPServer`). Casi todos los tutoriales
  que encuentres usan el nombre viejo.
- **Los modelos son Pydantic**: los campos son `snake_case`
  (`server_info`, `input_schema`), no camelCase como en el JSON.

### Siguiente paso (paso 2)

Convertir esto en un gestor de notas/tareas con SQLite:

- tools: `crear_nota`, `listar_notas`, `completar_nota`, `borrar_nota`
- resource: `notas://hoy`
- prompt: `resumen_diario`
