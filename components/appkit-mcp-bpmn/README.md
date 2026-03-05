# appkit-mcp-bpmn

MCP server component for generating and viewing BPMN 2.0 diagrams.

## Features

- **Generate BPMN diagrams** from natural language descriptions via LLM
- **Save & validate** BPMN 2.0 XML with schema-aware validation
- **Render diagrams** in-browser using bpmn-js Viewer (read-only)
- **Download** diagrams as `.bpmn` files
- **Public API** — no authentication required

## MCP Tools

### `generate_bpmn_diagram`

Generate a BPMN 2.0 diagram from a natural language description.

**Parameters:**
- `description` (str, required): Workflow description in natural language
- `diagram_type` (str, optional): `"process"` | `"collaboration"` | `"choreography"` (default: `"process"`)

**Returns:** JSON with `{success, id, xml, download_url, view_url, error}`

### `save_bpmn_diagram`

Save pre-built BPMN 2.0 XML to the filesystem.

**Parameters:**
- `xml` (str, required): Complete BPMN 2.0 XML string

**Returns:** JSON with `{success, id, xml, download_url, view_url, error}`

## MCP Resource

### `ui://appkit/bpmn_viewer.html`

Interactive BPMN diagram viewer powered by bpmn-js. Renders tool results via the MCP App `ui/notifications/tool-result` protocol.

**Features:**
- Zoom to fit viewport
- Download diagram as `.bpmn` file
- Error display for invalid XML

## Quick Start

```python
from appkit_mcp_bpmn.server import create_bpmn_mcp_server

mcp = create_bpmn_mcp_server()
app = mcp.http_app(path="/mcp", transport="streamable-http")
```

## Example Workflow

```
1. User: "Create an expense approval workflow"
2. LLM calls generate_bpmn_diagram(description="...", diagram_type="process")
3. Server generates XML via LLM, validates, saves to uploaded_files/
4. Returns {id, view_url, download_url}
5. MCP App renders diagram in bpmn-js Viewer
```

## Dependencies

- `appkit-commons` — Configuration and logging
- `appkit-mcp-commons` — Shared MCP base models
- `lxml` — XML parsing and validation
- `openai` (optional) — LLM generation via OpenAI API
