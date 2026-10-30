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

---

## Paso 2 — Notas con estado

| Archivo | Para qué sirve |
|---|---|
| `src/notas.py` | Servidor con SQLite: 4 tools, 2 resources, 1 prompt. |
| `probar_notas.py` | Cliente que recorre tools, resources y prompts. |
| `notas.db` | Base de datos (se crea sola, está en `.gitignore`). |

### Probar

```bash
.venv/bin/python probar_notas.py
.venv/bin/mcp dev src/notas.py
```

### Las tres piezas de MCP

| Pieza | Quién decide | Para qué |
|---|---|---|
| **Tool** | El modelo | Ejecutar una acción (crear, borrar...). Tiene efectos. |
| **Resource** | La aplicación/cliente | Leer datos por URI, sin efectos. |
| **Prompt** | El usuario | Plantilla de conversación que se rellena y se envía al modelo. |

Ejemplo: `listar_notas` es una tool porque el modelo decide cuándo usarla;
`notas://hoy` es un resource porque es un dato que la app puede adjuntar;
`resumen_diario` es un prompt porque lo pide el usuario desde un menú.

### Detalles que importan

- **Estado**: una conexión SQLite por operación (el SDK puede usar hilos
  distintos). `NOTAS_DB` permite apuntar a otra base.
- **Errores esperados**: `ToolError` en tools, `ResourceNotFoundError` en
  resources. Otras excepciones se tratan como *crash* y el cliente solo ve
  un mensaje genérico.
- **Salida estructurada**: anotar el retorno con un modelo Pydantic
  (`Nota`) publica un `outputSchema` y rellena `structuredContent`.
  Devolver un `dict` suelto deja `structuredContent` en `None`.
- **Listas**: MCP exige que `structuredContent` sea un objeto, así que el
  SDK envuelve `list[Nota]` como `{"result": [...]}`.

### Cosas para trastear

1. Añade `buscar_notas(consulta: str)` con `LIKE`.
2. Añade un resource `notas://completadas`.
3. Cambia el prompt para que devuelva dos mensajes
   (`UserMessage` + `AssistantMessage`).
4. Abre el Inspector y llama a `completar_nota` con `nota_id: 999` para ver
   el error tal como lo recibe el modelo.

