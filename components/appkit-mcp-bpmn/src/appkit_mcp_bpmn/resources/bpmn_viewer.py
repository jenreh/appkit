"""BPMN viewer resource endpoint."""

VIEW_URI = "ui://appkit/bpmn_viewer.html"

_BPMN_JS_CDN = "https://unpkg.com/bpmn-js@18.12.1/dist/bpmn-modeler.production.min.js"
_DIAGRAM_JS_CSS = "https://unpkg.com/bpmn-js@18.12.1/dist/assets/diagram-js.css"
_BPMN_JS_CSS = "https://unpkg.com/bpmn-js@18.12.1/dist/assets/bpmn-js.css"
_BPMN_FONT_CSS = "https://unpkg.com/bpmn-js@18.12.1/dist/assets/bpmn-font/css/bpmn.css"
_LUCIDE_CDN = "https://unpkg.com/lucide@latest"

BPMN_VIEWER_HTML = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>BPMN Diagram Editor</title>
<link rel="stylesheet" href="{_DIAGRAM_JS_CSS}" />
<link rel="stylesheet" href="{_BPMN_JS_CSS}" />
<link rel="stylesheet" href="{_BPMN_FONT_CSS}" />
<script src="{_BPMN_JS_CDN}"
  onerror="document.getElementById('error-box').innerHTML=
    '<div class=error-title>\u26a0\ufe0f Failed to load BPMN viewer</div>'
    +'<div class=error-detail>Could not load bpmn-js from CDN. '
    +'Check your internet connection.</div>';
    document.getElementById('error-box').style.display='block';
    document.getElementById('loading-box').style.display='none';"
></script>
<script src="{_LUCIDE_CDN}"></script>
<style>
:root {{
  /* Light mode (default) */
  --bg-primary: #fff;
  --bg-secondary: #fafafa;
  --text-primary: #333;
  --text-secondary: #666;
  --border-color: #e0e0e0;
  --border-color-secondary: #dee2e6;
  --button-hover: rgba(0, 0, 0, 0.06);
  --error-bg: #fff5f5;
  --error-text: #c92a2a;
  --error-text-secondary: #862e2e;
  --error-border: #e03131;
  --loading-text: rgb(0, 144, 255);
  --canvas-bg: #fff;
  --diagram-text: #000;
  --diagram-stroke: #000;
  --diagram-fill: #fff;
}}

@media (prefers-color-scheme: dark) {{
  :root {{
    /* Dark mode */
    --bg-primary: #0d0d0d;
    --bg-secondary: #1a1a1a;
    --text-primary: #e0e0e0;
    --text-secondary: #a0a0a0;
    --border-color: #333;
    --border-color-secondary: #444;
    --button-hover: rgba(255, 255, 255, 0.08);
    --error-bg: #2d1515;
    --error-text: #ff6b6b;
    --error-text-secondary: #ff9999;
    --error-border: #c92a2a;
    --loading-text: #4da6ff;
    --canvas-bg: #1a1a1a;
    --diagram-text: #e0e0e0;
    --diagram-stroke: #ccc;
    --diagram-fill: #2a2a2a;
  }}
}}

html, body {{
  margin: 0;
  padding: 0;
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  transition: background 0.2s, color 0.2s;
}}
#canvas {{
  width: 816px;
  height: 500px;
  display: none;
}}
#toolbar {{
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding: 8px 16px;
  height: 48px;
  box-sizing: border-box;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  position: sticky;
  top: 0;
  z-index: 10;
}}
#toolbar button {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0px;
  padding: 6px 6px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}}
#toolbar button:hover {{
  background: var(--button-hover);
}}
#toolbar button svg {{
  width: 18px;
  height: 18px;
  stroke-width: 1;
  color: var(--text-primary);
}}
.toolbar-separator {{
  width: 1px;
  height: 24px;
  background: var(--border-color-secondary);
  margin: 0 4px;
}}
#status {{
  flex: 1;
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 0px;
  min-width: 0;
  overflow: hidden;
  flex-wrap: nowrap;
  white-space: nowrap;
}}
#diagram-name {{
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  padding: 2px 6px 2px 4px;
  border-radius: 0 4px 4px 0;
  border: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
  display: flex;
  align-items: center;
}}
#diagram-name-group {{
  display: flex;
  align-items: stretch;
  gap: 0;
  min-width: 0;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: 4px;
  transition: border-color 0.15s, background 0.15s;
}}
#diagram-name-group:hover {{
  border-color: var(--border-color-secondary);
  background: var(--button-hover);
}}
#diagram-name-group:hover #diagram-name {{
  border-color: transparent;
  background: transparent;
}}
#diagram-name-group:hover #btn-edit-name {{
  color: var(--text-primary);
  background: transparent;
}}
#btn-edit-name {{
  display: none;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
  border: none;
  border-radius: 4px 0 0 4px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: color 0.15s;
  flex-shrink: 0;
}}
#btn-edit-name:hover {{
  color: var(--text-primary);
}}
#btn-edit-name svg {{
  width: 12px !important;
  height: 12px !important;
  stroke-width: 2 !important;
}}
#diagram-name-input {{
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-primary);
  background: var(--bg-primary);
  border: 1px solid #4da6ff;
  border-radius: 4px;
  padding: 2px 6px;
  outline: none;
  max-width: 300px;
  box-sizing: border-box;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
#error-box {{
  display: none;
  margin: 24px;
  padding: 24px 32px;
  border: 1px solid var(--error-border);
  border-radius: 8px;
  background: var(--error-bg);
  color: var(--error-text);
  font-size: 15px;
  line-height: 1.5;
  text-align: left;
}}
#error-box .error-title {{
  font-weight: 600;
  font-size: 17px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
#error-box .error-detail {{
  color: var(--error-text-secondary);
  word-break: break-word;
}}
body.maximized {{
  margin: 0;
  overflow: hidden;
}}
body.maximized #canvas {{
  width: 100vw;
  height: calc(100vh - 48px);
}}
#toast {{
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%) translateY(20px);
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 13px;
  color: #fff;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s, transform 0.3s;
  z-index: 100;
  white-space: nowrap;
}}
#toast.show {{
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}}
#toast.success {{
  background: #2b8a3e;
}}
#toast.error {{
  background: #c92a2a;
}}

/* Canvas and diagram styling for dark mode */
#canvas {{
  background: var(--canvas-bg);
}}

#canvas svg {{
  background: var(--canvas-bg);
}}

#canvas text {{
  fill: var(--diagram-text);
  color: var(--diagram-text);
}}

#canvas .djs-shape {{
  stroke: var(--diagram-stroke);
}}

#canvas .djs-connection > .djs-visual > path,
#canvas .djs-connection > .djs-visual > polyline {{
  stroke: var(--diagram-stroke);
  stroke-width: 1.5px;
}}

/* Remove text shadows/filters globally (white stroke halo from bpmn-js) */
#canvas text,
#canvas tspan {{
  fill: var(--diagram-text);
  stroke: none !important;
  stroke-width: 0 !important;
  paint-order: normal !important;
}}

/* Disable SVG filters (text halo/shadow effects) globally */
#canvas svg defs filter {{
  display: none !important;
}}

/* BPMN element styles for dark mode */
@media (prefers-color-scheme: dark) {{
  /* Shape styling - all BPMN shapes */
  #canvas .djs-shape > .djs-visual {{
    fill: var(--diagram-fill) !important;
    stroke: var(--diagram-stroke) !important;
  }}
  #canvas .djs-shape:not(.djs-frame) > .djs-visual circle,
  #canvas .djs-shape:not(.djs-frame) > .djs-visual ellipse,
  #canvas .djs-shape:not(.djs-frame) > .djs-visual path,
  #canvas .djs-shape:not(.djs-frame) > .djs-visual polygon,
  #canvas .djs-shape:not(.djs-frame) > .djs-visual rect {{
    fill: var(--diagram-fill) !important;
    stroke: var(--diagram-stroke) !important;
  }}
  /* Connection lines */
  #canvas .djs-connection > .djs-visual > path,
  #canvas .djs-connection > .djs-visual > polyline {{
    stroke: var(--diagram-stroke) !important;
  }}
  /* Arrowhead markers */
  #canvas svg defs marker path,
  #canvas svg defs marker polygon,
  #canvas svg marker path,
  #canvas svg marker polygon {{
    fill: var(--diagram-stroke) !important;
    stroke: var(--diagram-stroke) !important;
  }}
  /* All text in canvas - remove white stroke halo */
  #canvas .djs-label text,
  #canvas text,
  #canvas tspan {{
    fill: var(--diagram-text) !important;
    stroke: none !important;
    stroke-width: 0 !important;
    paint-order: normal !important;
    filter: none !important;
  }}
  /* Remove white background rects behind labels */
  #canvas .djs-label .djs-visual rect,
  #canvas .djs-label rect {{
    fill: transparent !important;
    stroke: none !important;
  }}
  /* Remove any SVG text filters (white halos) */
  #canvas svg defs filter {{
    display: none !important;
  }}
  #canvas .djs-element.selected > .djs-visual {{
    stroke: #4da6ff !important;
  }}
  /* Palette styling - container */
  .djs-palette {{
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border-color) !important;
    color: var(--text-primary) !important;
  }}
  /* Palette entries use bpmn-font (icon font, not SVG) */
  .djs-palette .entry,
  .djs-palette .djs-palette-entries .entry,
  .djs-palette-entry,
  .djs-palette [class*="entry"] {{
    color: var(--text-primary) !important;
    background: transparent !important;
  }}
  .djs-palette .entry:hover,
  .djs-palette-entry:hover {{
    background: var(--button-hover) !important;
  }}
  /* Palette separator */
  .djs-palette .separator,
  .djs-palette hr {{
    border-color: var(--border-color) !important;
  }}
  /* Palette icons - both font icons and any SVG icons */
  .djs-palette .entry svg,
  .djs-palette-entry svg {{
    color: var(--text-primary) !important;
  }}
  .djs-palette .entry svg *,
  .djs-palette-entry svg * {{
    stroke: var(--text-primary) !important;
    fill: none !important;
  }}
  /* Context pad */
  .djs-popup,
  .djs-context-pad {{
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border-color) !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
  }}
  .djs-context-pad .entry,
  .djs-context-pad-item {{
    color: var(--text-primary) !important;
    background: var(--bg-secondary) !important;
  }}
  .djs-context-pad .entry:hover,
  .djs-context-pad-item:hover {{
    background: var(--button-hover) !important;
  }}
  .djs-context-pad .entry svg *,
  .djs-context-pad-item svg * {{
    color: var(--text-primary) !important;
    fill: none !important;
    stroke: var(--text-primary) !important;
  }}
  /* Connection preview */
  #canvas .djs-connection.djs-preview > .djs-visual > polyline {{
    stroke: var(--diagram-stroke) !important;
    opacity: 0.6;
  }}
}}

</style>
</head>
<body>
<div id="toolbar">
  <span id="status">
    <span id="diagram-name-group">
      <button id="btn-edit-name" title="Rename diagram">
        <i data-lucide="pencil"></i>
      </button>
      <span id="diagram-name" title="Click to rename" style="display:none;"></span>
    </span>
    <span id="status-text">Loading diagram&hellip;</span>
  </span>
  <button id="btn-zoom-in" title="Zoom in">
    <i data-lucide="zoom-in"></i>
  </button>
  <button id="btn-zoom-out" title="Zoom out">
    <i data-lucide="zoom-out"></i>
  </button>
  <button id="btn-zoom-fit" title="Fit to viewport">
    <i data-lucide="fullscreen"></i>
  </button>
  <span class="toolbar-separator"></span>
  <button id="btn-download-xml" title="Download .bpmn file">
    <i data-lucide="file-down"></i>
  </button>
  <button id="btn-download-svg" title="Download as SVG">
    <i data-lucide="image-down"></i>
  </button>
  <span class="toolbar-separator"></span>
  <button id="btn-save" title="Save changes">
    <i data-lucide="save"></i>
  </button>
  <span class="toolbar-separator"></span>
  <button id="btn-fullscreen" title="Toggle Fullscreen">
    <i data-lucide="maximize"></i>
  </button></div>
<div id="canvas"></div>
<div id="toast"></div>
<div id="error-box"></div>
<div id="loading-box"
 style="display:flex;align-items:center;justify-content:center;
 height:300px;font-size:18px;color:var(--loading-text);">
 BPMN loading&hellip;</div>

<script>
  function initializeIcons() {{
    if (window.lucide && window.lucide.createIcons) {{
      window.lucide.createIcons();
    }}
  }}

  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', initializeIcons);
  }} else {{
    initializeIcons();
  }}
</script>
<script>
(function () {{
  const CANVAS = document.getElementById("canvas");
  const STATUS = document.getElementById("status-text");
  const ERROR = document.getElementById("error-box");
  const LOADING = document.getElementById("loading-box");
  const NAME_EL = document.getElementById("diagram-name");
  const EDIT_BTN = document.getElementById("btn-edit-name");
  let currentXml = null;
  let currentDiagramId = null;
  let currentDiagramName = null;
  let diagramRendered = false;
  let fetchStarted = false;
  let hostTheme = null;
  var hostInfo = {{}};

  const viewer = new BpmnJS({{
    container: CANVAS,
    keyboard: {{ bindTo: window }}
  }});
  let rpcId = 10;
  const pendingCalls = {{}};

  // Send ui/initialize handshake to host (MCP Apps spec 2026-01-26)
  window.parent.postMessage(
    {{
      jsonrpc: "2.0",
      method: "ui/initialize",
      id: 1,
      params: {{
        protocolVersion: "2026-01-26",
        appInfo: {{ name: "bpmn-viewer", version: "1.0.0" }},
        appCapabilities: {{
          availableDisplayModes: ["inline", "fullscreen"],
        }},
      }},
    }},
    "*"
  );

  window.addEventListener("message", function (event) {{
    const msg = event.data;
    if (!msg || msg.jsonrpc !== "2.0") return;

    if (msg.method === "ui/notifications/tool-result") {{
      handleToolResult(msg.params);
    }} else if (msg.method === "ui/notifications/tool-input") {{
      /* Tool arguments delivered before result; available in msg.params.arguments */
    }} else if (msg.method === "ui/notifications/host-context-changed") {{
      const p = msg.params || {{}};
      if (p.theme) {{
        hostTheme = p.theme;
        if (diagramRendered) applyDarkModeToSvg();
      }}
      if (p.displayMode) {{
        const wantFullscreen = p.displayMode === "fullscreen";
        if (wantFullscreen !== maximized) applyMaximizedState(wantFullscreen);
      }}
    }} else if (msg.method === "ui/resource-teardown" && msg.id != null) {{
      window.parent.postMessage(
        {{ jsonrpc: "2.0", id: msg.id, result: {{}} }},
        "*"
      );
    }} else if (msg.id === 1 && !msg.method) {{
      // ui/initialize response — apply host context, then send initialized
      const hc = (msg.result && msg.result.hostContext) || {{}};
      if (hc.theme) hostTheme = hc.theme;
      hostInfo = (msg.result && msg.result.hostInfo) || {{}};
      window.parent.postMessage(
        {{ jsonrpc: "2.0", method: "ui/notifications/initialized", params: {{}} }},
        "*"
      );
    }} else if (msg.id != null && !msg.method && pendingCalls[msg.id]) {{
      // JSON-RPC response for a tools/call we sent
      const cb = pendingCalls[msg.id];
      delete pendingCalls[msg.id];
      if (msg.error) {{
        cb.reject(new Error(msg.error.message || "RPC error"));
      }} else {{
        cb.resolve(msg.result);
      }}
    }} else if (msg.method === "ping" && msg.id != null) {{
      window.parent.postMessage(
        {{ jsonrpc: "2.0", id: msg.id, result: {{}} }},
        "*"
      );
    }}
  }});

  function callServerTool(name, args) {{
    return new Promise(function (resolve, reject) {{
      const id = ++rpcId;
      pendingCalls[id] = {{ resolve: resolve, reject: reject }};
      window.parent.postMessage(
        {{
          jsonrpc: "2.0",
          method: "tools/call",
          id: id,
          params: {{ name: name, arguments: args || {{}} }},
        }},
        "*"
      );
    }});
  }}

  // Download strategy:
  //  - appkit host: ui/download-file (non-standard appkit extension).
  //    Detected via hostInfo.name === "appkit" from ui/initialize.
  //    Falls back to _showCopyFallback on error/timeout.
  //  - all other hosts: _showCopyFallback — an inline overlay with a
  //    textarea and copy-to-clipboard button, since the MCP Apps sandbox
  //    proxy spec only grants allow-scripts + allow-same-origin and
  //    blob URL / data: URI downloads are blocked.

  function _showCopyFallback(filename, content) {{
    var existing = document.getElementById("bpmn-copy-overlay");
    if (existing) existing.remove();

    var overlay = document.createElement("div");
    overlay.id = "bpmn-copy-overlay";
    overlay.style.cssText = [
      "position:fixed;top:0;left:0;width:100%;height:100%;",
      "background:rgba(0,0,0,0.55);z-index:9999;",
      "display:flex;align-items:center;justify-content:center;",
    ].join("");

    var box = document.createElement("div");
    box.style.cssText = [
      "background:#fff;border-radius:8px;padding:20px;",
      "width:min(600px,90vw);max-height:80vh;",
      "display:flex;flex-direction:column;gap:12px;",
      "box-shadow:0 8px 32px rgba(0,0,0,0.3);",
    ].join("");

    var header = document.createElement("div");
    header.style.cssText = [
      "display:flex;justify-content:space-between;",
      "align-items:center;",
    ].join("");
    var title = document.createElement("strong");
    title.style.cssText = "font-size:14px;font-family:sans-serif;";
    title.textContent = filename;
    var closeBtn = document.createElement("button");
    closeBtn.textContent = "\u00d7";
    closeBtn.style.cssText = [
      "background:none;border:none;font-size:20px;cursor:pointer;",
      "padding:0 4px;line-height:1;color:#555;",
    ].join("");
    closeBtn.onclick = function () {{ overlay.remove(); }};
    header.appendChild(title);
    header.appendChild(closeBtn);

    var hint = document.createElement("p");
    hint.style.cssText = "margin:0;font-size:12px;font-family:sans-serif;color:#666;";
    hint.textContent =
      "Direct download unavailable in this host. Copy the content below:";

    var ta = document.createElement("textarea");
    ta.readOnly = true;
    ta.value = content;
    ta.style.cssText = [
      "width:100%;flex:1;min-height:200px;resize:vertical;",
      "font-family:monospace;font-size:11px;",
      "border:1px solid #ccc;border-radius:4px;padding:8px;",
      "box-sizing:border-box;",
    ].join("");

    var btnRow = document.createElement("div");
    btnRow.style.cssText = "display:flex;gap:8px;justify-content:flex-end;";

    var copyBtn = document.createElement("button");
    copyBtn.textContent = "Copy to clipboard";
    copyBtn.style.cssText = [
      "padding:7px 16px;border:none;border-radius:4px;cursor:pointer;",
      "background:#228be6;color:#fff;font-size:13px;font-family:sans-serif;",
    ].join("");
    copyBtn.onclick = function () {{
      var copied = false;
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(content).then(function () {{
          copyBtn.textContent = "Copied!";
          setTimeout(function () {{
            copyBtn.textContent = "Copy to clipboard";
          }}, 2000);
        }}).catch(function () {{ fallbackCopy(); }});
      }} else {{
        fallbackCopy();
      }}
      function fallbackCopy() {{
        ta.select();
        try {{
          document.execCommand("copy");
          copyBtn.textContent = "Copied!";
          setTimeout(function () {{
            copyBtn.textContent = "Copy to clipboard";
          }}, 2000);
        }} catch (e) {{
          copyBtn.textContent = "Copy failed";
        }}
      }}
    }};

    var tryBtn = document.createElement("button");
    tryBtn.textContent = "Try download anyway";
    tryBtn.style.cssText = [
      "padding:7px 16px;border:1px solid #ccc;border-radius:4px;cursor:pointer;",
      "background:#f8f9fa;color:#333;font-size:13px;font-family:sans-serif;",
    ].join("");
    tryBtn.onclick = function () {{
      try {{
        var blob = new Blob([content], {{ type: "application/octet-stream" }});
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(function () {{ URL.revokeObjectURL(url); }}, 10000);
      }} catch (e) {{
        console.error("[bpmn-viewer] fallback blob download failed:", e);
      }}
    }};

    btnRow.appendChild(tryBtn);
    btnRow.appendChild(copyBtn);
    box.appendChild(header);
    box.appendChild(hint);
    box.appendChild(ta);
    box.appendChild(btnRow);
    overlay.appendChild(box);

    overlay.addEventListener("click", function (e) {{
      if (e.target === overlay) overlay.remove();
    }});

    document.body.appendChild(overlay);
    setTimeout(function () {{ ta.select(); }}, 50);
  }}

  function _downloadForAppkit(filename, content, mimeType) {{
    const id = ++rpcId;
    var timer = setTimeout(function () {{
      if (pendingCalls[id]) {{
        delete pendingCalls[id];
        _showCopyFallback(filename, content);
      }}
    }}, 2000);
    pendingCalls[id] = {{
      resolve: function () {{ clearTimeout(timer); }},
      reject: function () {{
        clearTimeout(timer);
        _showCopyFallback(filename, content);
      }},
    }};
    window.parent.postMessage(
      {{
        jsonrpc: "2.0",
        id: id,
        method: "ui/download-file",
        params: {{
          contents: [{{
            type: "resource",
            resource: {{
              uri: "file:///" + filename,
              mimeType: mimeType,
              text: content,
            }},
          }}],
        }},
      }},
      "*"
    );
  }}

  function downloadFile(filename, content, mimeType) {{
    if (hostInfo.name === "appkit") {{
      _downloadForAppkit(filename, content, mimeType);
    }} else {{
      _showCopyFallback(filename, content);
    }}
  }}

  function handleToolResult(result) {{
    clearLoadTimeout();
    if (diagramRendered || fetchStarted) {{
      console.log(
        "[bpmn-viewer] ignoring tool-result,",
        diagramRendered ? "diagram rendered" : "fetch in progress"
      );
      return;
    }}
    const s = JSON.stringify(result).substring(0, 500);
    console.log("[bpmn-viewer] handleToolResult:", s);
    try {{
      const text =
        result &&
        result.content &&
        result.content[0] &&
        result.content[0].text;
      if (!text) {{
        showError("No diagram data received.");
        return;
      }}
      const payload = JSON.parse(text);
      if (!payload.success) {{
        showError(payload.error || "Unknown error");
        return;
      }}
      if (payload.id) {{
        currentDiagramId = payload.id;
        if (payload.name) {{
          currentDiagramName = payload.name;
        }}
        console.log("[bpmn-viewer] fetching XML for diagram:", payload.id);
        fetchXmlViaTool(payload.id);
      }} else {{
        showError("No diagram ID in response.");
      }}
    }} catch (e) {{
      showError("Error: " + e.message);
    }}
  }}

  function fetchXmlViaTool(diagramId) {{
    clearLoadTimeout();
    fetchStarted = true;
    STATUS.textContent = "Fetching diagram…";
    console.log("[bpmn-viewer] calling tools/call get_bpmn_xml", diagramId);
    callServerTool("get_bpmn_xml", {{ diagram_id: diagramId }})
      .then(function (result) {{
        const s = JSON.stringify(result).substring(0, 500);
        console.log("[bpmn-viewer] get_bpmn_xml response:", s);
        // result is CallToolResult: {{ content: [{{ text: "<xml>" }}] }}
        const xml =
          result &&
          result.content &&
          result.content[0] &&
          result.content[0].text;
        if (!xml) {{
          showError("No XML returned from get_bpmn_xml");
          return;
        }}
        // Check if it's a JSON error response
        if (xml.charAt(0) === "{{") {{
          try {{
            const err = JSON.parse(xml);
            if (!err.success) {{
              showError(err.error || "Failed to load diagram");
              return;
            }}
          }} catch (e) {{
            /* not JSON, treat as XML */
          }}
        }}
        renderXml(xml);
      }})
      .catch(function (err) {{
        console.error("[bpmn-viewer] get_bpmn_xml error:", err);
        showError("Failed to fetch diagram: " + err.message);
      }});
  }}

  function renderXml(xml) {{
    if (diagramRendered) {{
      return;
    }}
    currentXml = xml;
    LOADING.style.display = "none";
    ERROR.style.display = "none";
    CANVAS.style.display = "block";
    viewer.importXML(xml)
      .then(function () {{
        try {{
          fitWithPadding();
        }} catch (zoomErr) {{
          console.warn(
            "[bpmn-viewer] fit-viewport failed, " +
              "falling back to zoom(1):",
            zoomErr.message
          );
          try {{
            viewer.get("canvas").zoom(1);
          }} catch (e) {{
            /* ignore */
          }}
        }}
        diagramRendered = true;
        STATUS.textContent = "";
        if (currentDiagramName) {{
          NAME_EL.textContent = currentDiagramName;
          NAME_EL.style.display = "";
          EDIT_BTN.style.display = "flex";
        }} else {{
          STATUS.textContent = "Generiertes BPMN-Diagramm";
        }}
        applyDarkModeToSvg();
        reportSize();
      }})
      .catch(function (err) {{
        showError("Failed to render: " + err.message);
      }});
  }}

  function showError(msg) {{
    console.error("[bpmn-viewer] showError:", msg);
    if (diagramRendered) {{
      console.warn(
        "[bpmn-viewer] suppressing error, diagram already rendered"
      );
      return;
    }}
    LOADING.style.display = "none";
    CANVAS.style.display = "none";
    ERROR.style.display = "block";
    ERROR.innerHTML =
      '<div class="error-title">⚠️ Rendering failed</div>' +
      '<div class="error-detail">' +
      escapeHtml(String(msg)) +
      "</div>";
    STATUS.textContent = "Error";
    reportSize();
  }}

  function escapeHtml(s) {{
    const d = document.createElement("div");
    d.appendChild(document.createTextNode(s));
    return d.innerHTML;
  }}

  // Timeout: if nothing arrives within 60 s, show a message
  let loadTimeout = setTimeout(function () {{
    if (LOADING.style.display !== "none") {{
      showError(
        "Timed out waiting for diagram data. " +
          "The generation may have failed silently."
      );
    }}
  }}, 60000);

  // Clear timeout once we successfully start processing
  function clearLoadTimeout() {{
    if (loadTimeout) {{
      clearTimeout(loadTimeout);
      loadTimeout = null;
    }}
  }}

  window.addEventListener("error", function (e) {{
    showError("Unexpected error: " + (e.message || e));
  }});

  var pendingFitAfterResize = false;

  // Listen for window resize (fired when parent resizes the iframe)
  window.addEventListener("resize", function () {{
    if (pendingFitAfterResize) {{
      pendingFitAfterResize = false;
      // Small delay so the layout engine finishes reflow
      setTimeout(function () {{
        try {{ fitWithPadding(); }} catch (e) {{ /* ignore */ }}
      }}, 50);
    }}
  }});

  function fitWithPadding() {{
    var c = viewer.get("canvas");
    c.resized();
    c.zoom("fit-viewport");
    var vb = c.viewbox();
    var padRight = vb.width * 0.06;
    var padTop = vb.height * 0.06;
    var padBottom = padTop;
    var padLeft = vb.width * 0.21;
    c.viewbox({{
      x: vb.x - padLeft,
      y: vb.y - padTop,
      width: vb.width + padLeft + padRight,
      height: vb.height + padTop + padBottom
    }});
  }}

  function isDarkMode() {{
    if (hostTheme) return hostTheme === "dark";
    return window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches;
  }}

  function applyDarkModeToSvg() {{
    if (!isDarkMode()) {{
      return;
    }}
    var strokeColor = "#ccc";
    var fillColor = "#2a2a2a";
    var textColor = "#e0e0e0";

    /* Style all SVG markers (arrowheads) */
    var svgEl = document.querySelector("#canvas svg");
    if (!svgEl) return;

    svgEl.querySelectorAll("defs marker path, defs marker polygon")
      .forEach(function(el) {{
        el.setAttribute("fill", strokeColor);
        el.setAttribute("stroke", strokeColor);
      }});

    /* Style connection lines (sequence flows, message flows) */
    document.querySelectorAll(
      "#canvas .djs-connection .djs-visual path, " +
      "#canvas .djs-connection .djs-visual polyline"
    ).forEach(function(el) {{
      el.setAttribute("stroke", strokeColor);
      el.setAttribute("stroke-width", "1.5");
    }});

    /* Style shape elements */
    document.querySelectorAll(
      "#canvas .djs-shape:not(.djs-frame) .djs-visual rect, " +
      "#canvas .djs-shape:not(.djs-frame) .djs-visual circle, " +
      "#canvas .djs-shape:not(.djs-frame) .djs-visual ellipse, " +
      "#canvas .djs-shape:not(.djs-frame) .djs-visual polygon, " +
      "#canvas .djs-shape:not(.djs-frame) .djs-visual path"
    ).forEach(function(el) {{
      var currentFill = el.getAttribute("fill");
      if (currentFill && currentFill !== "none"
          && currentFill !== "transparent") {{
        el.setAttribute("fill", fillColor);
      }}
      el.setAttribute("stroke", strokeColor);
    }});

    /* Style text labels - remove white stroke halo */
    document.querySelectorAll("#canvas text, #canvas tspan")
      .forEach(function(el) {{
        el.setAttribute("fill", textColor);
        el.setAttribute("stroke", "none");
        el.setAttribute("stroke-width", "0");
        el.setAttribute("paint-order", "normal");
        el.removeAttribute("filter");
        el.style.filter = "none";
        el.style.paintOrder = "normal";
        el.style.stroke = "none";
        el.style.strokeWidth = "0";
      }});

    /* Remove white background rects behind labels */
    document.querySelectorAll(
      "#canvas .djs-label rect, #canvas .djs-label .djs-visual rect"
    ).forEach(function(el) {{
      el.setAttribute("fill", "transparent");
      el.setAttribute("stroke", "none");
    }});

    /* Disable SVG filters (white text halos) */
    svgEl.querySelectorAll("defs filter").forEach(function(el) {{
      el.setAttribute("width", "0");
      el.setAttribute("height", "0");
    }});

    /* Style palette entries (bpmn-font icon font) */
    document.querySelectorAll(
      ".djs-palette .entry, .djs-palette-entry"
    ).forEach(function(el) {{
      el.style.color = textColor;
    }});
  }}

  document.getElementById("btn-zoom-in").addEventListener("click", function () {{
    try {{
      const c = viewer.get("canvas");
      c.zoom(Math.min(c.zoom() * 1.2, 4.0));
    }} catch (e) {{
      /* ignore */
    }}
  }});

  document
    .getElementById("btn-zoom-out")
    .addEventListener("click", function () {{
      try {{
        const c = viewer.get("canvas");
        c.zoom(Math.max(c.zoom() * 0.8, 0.2));
      }} catch (e) {{
        /* ignore */
      }}
    }});

  document.getElementById("btn-zoom-fit").addEventListener("click", function () {{
    try {{
      fitWithPadding();
    }} catch (e) {{
      /* ignore */
    }}
  }});

  document
    .getElementById("btn-download-xml")
    .addEventListener("click", function () {{
      if (!diagramRendered) return;
      viewer.saveXML({{ format: true }})
        .then(function (result) {{
          if (result.xml) {{
            downloadFile("diagram.bpmn", result.xml, "application/xml");
          }}
        }})
        .catch(function (err) {{
          console.error("[bpmn-editor] saveXML failed:", err);
        }});
    }});

  let maximized = false;

  function applyMaximizedState(val) {{
    maximized = val;
    if (maximized) {{
      document.body.classList.add("maximized");
    }} else {{
      document.body.classList.remove("maximized");
    }}
    const icon = document.querySelector("#btn-fullscreen i");
    if (icon) {{
      icon.setAttribute("data-lucide", maximized ? "minimize" : "maximize");
      if (window.lucide && window.lucide.createIcons) {{
        window.lucide.createIcons();
      }}
    }}
    if (maximized) {{
      // Maximizing: overlay appears quickly, short delay is fine.
      setTimeout(function () {{
        try {{ fitWithPadding(); }} catch (e) {{ /* ignore */ }}
      }}, 150);
    }} else {{
      // Restoring: wait for the parent to resize the iframe.
      // The window resize event will trigger fitWithPadding.
      pendingFitAfterResize = true;
      // Fallback: if no resize event fires within 600ms, fit anyway.
      setTimeout(function () {{
        if (pendingFitAfterResize) {{
          pendingFitAfterResize = false;
          try {{ fitWithPadding(); }} catch (e) {{ /* ignore */ }}
        }}
      }}, 600);
    }}
  }}

  function setMaximized(val) {{
    applyMaximizedState(val);
    // Request display mode change from host (ui/request-display-mode)
    const id = ++rpcId;
    window.parent.postMessage(
      {{
        jsonrpc: "2.0",
        method: "ui/request-display-mode",
        id: id,
        params: {{ mode: maximized ? "fullscreen" : "inline" }},
      }},
      "*"
    );
  }}

  document
    .getElementById("btn-fullscreen")
    .addEventListener("click", function () {{
      setMaximized(!maximized);
    }});

  function showToast(message, type) {{
    var toast = document.getElementById("toast");
    toast.textContent = message;
    toast.className = type;
    // Force reflow before adding show class
    void toast.offsetWidth;
    toast.classList.add("show");
    var duration = type === "error" ? 4000 : 3000;
    setTimeout(function () {{
      toast.classList.remove("show");
    }}, duration);
  }}

  // Inline name editing
  function startNameEdit() {{
    if (!diagramRendered || !currentDiagramId) return;
    var originalName = currentDiagramName || "";
    var nameWidth = NAME_EL.offsetWidth;
    var input = document.createElement("input");
    input.id = "diagram-name-input";
    input.type = "text";
    input.value = originalName;
    input.maxLength = 128;
    input.style.width = nameWidth + "px";
    EDIT_BTN.style.visibility = "hidden";
    NAME_EL.replaceWith(input);
    input.focus();
    input.select();

    function restoreDisplay() {{
      input.replaceWith(NAME_EL);
      EDIT_BTN.style.visibility = "";
    }}

    function commitRename() {{
      var newName = input.value.trim();
      if (!newName || newName === originalName) {{
        restoreDisplay();
        return;
      }}
      // Optimistically update display
      NAME_EL.textContent = newName;
      restoreDisplay();
      callServerTool("rename_bpmn_diagram", {{
        diagram_id: currentDiagramId,
        name: newName,
      }})
        .then(function (response) {{
          var text =
            response.content &&
            response.content[0] &&
            response.content[0].text;
          if (text) {{
            try {{
              var parsed = JSON.parse(text);
              if (parsed.success) {{
                currentDiagramName = parsed.name || newName;
                NAME_EL.textContent = currentDiagramName;
                showToast("Diagramm umbenannt zu: " + currentDiagramName, "success");
              }} else {{
                NAME_EL.textContent = originalName;
                currentDiagramName = originalName;
                showToast(parsed.error || "Fehler beim Umbenennen", "error");
              }}
            }} catch (e) {{
              NAME_EL.textContent = originalName;
              currentDiagramName = originalName;
              showToast("Fehler beim Umbenennen", "error");
            }}
          }}
        }})
        .catch(function (err) {{
          console.error("[bpmn-viewer] rename failed:", err);
          NAME_EL.textContent = originalName;
          currentDiagramName = originalName;
          showToast("Fehler beim Umbenennen: " + err.message, "error");
        }});
    }}

    input.addEventListener("blur", commitRename);
    input.addEventListener("keydown", function (e) {{
      if (e.key === "Enter") {{
        e.preventDefault();
        input.blur();
      }} else if (e.key === "Escape") {{
        input.removeEventListener("blur", commitRename);
        restoreDisplay();
      }}
    }});
  }}

  NAME_EL.addEventListener("click", startNameEdit);
  EDIT_BTN.addEventListener("click", startNameEdit);

  document
    .getElementById("btn-save")
    .addEventListener("click", function () {{
      if (!diagramRendered || !currentDiagramId) return;
      viewer.saveXML({{ format: true }})
        .then(function (result) {{
          if (!result.xml) return;
          return callServerTool("save_or_update", {{
            diagram_id: currentDiagramId,
            xml: result.xml,
          }});
        }})
        .then(function (response) {{
          if (!response) return;
          var text =
            response.content &&
            response.content[0] &&
            response.content[0].text;
          if (text) {{
            try {{
              var parsed = JSON.parse(text);
              if (parsed.success) {{
                showToast("\u00c4nderungen gespeichert", "success");
              }} else {{
                showToast(parsed.error || "Fehler beim Speichern", "error");
              }}
            }} catch (e) {{
              showToast("Fehler beim Speichern", "error");
            }}
          }}
        }})
        .catch(function (err) {{
          console.error("[bpmn-viewer] save failed:", err);
          showToast("Fehler beim Speichern: " + err.message, "error");
        }});
    }});

  document
    .getElementById("btn-download-svg")
    .addEventListener("click", function () {{
      if (!diagramRendered) return;
      viewer.saveSVG()
        .then(function (result) {{
          const svg = typeof result === "string" ? result : result.svg;
          downloadFile("diagram.svg", svg, "image/svg+xml");
        }})
        .catch(function (err) {{
          console.error("[bpmn-viewer] SVG export failed:", err);
        }});
    }});

  function reportSize() {{
    const h = Math.max(document.body.scrollHeight, 500);
    const w = Math.max(document.body.scrollWidth, 816);
    window.parent.postMessage(
      {{
        jsonrpc: "2.0",
        method: "ui/notifications/size-changed",
        params: {{ height: h, width: w }},
      }},
      "*"
    );
  }}
  new ResizeObserver(function () {{
    reportSize();
  }}).observe(document.body);
}})();
</script>
</body>
</html>
"""
