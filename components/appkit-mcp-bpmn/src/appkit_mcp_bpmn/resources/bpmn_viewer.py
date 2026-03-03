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
html, body {{
  margin: 0;
  padding: 0;
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #fff;
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
  border-bottom: 1px solid #e0e0e0;
  background: #fafafa;
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
  color: #333;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}}
#toolbar button:hover {{
  background: rgba(0, 0, 0, 0.06);
}}
#toolbar button svg {{
  width: 18px;
  height: 18px;
  stroke-width: 1;
  color: #333;
}}
.toolbar-separator {{
  width: 1px;
  height: 24px;
  background: #dee2e6;
  margin: 0 4px;
}}
#status {{
  flex: 1;
  font-size: 13px;
  color: #666;
}}
#error-box {{
  display: none;
  margin: 24px;
  padding: 24px 32px;
  border: 1px solid #e03131;
  border-radius: 8px;
  background: #fff5f5;
  color: #c92a2a;
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
  color: #862e2e;
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
</style>
</head>
<body>
<div id="toolbar">
  <span id="status">Loading diagram&hellip;</span>
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
  </button>  <span class="toolbar-separator"></span>
  <button id="btn-fullscreen" title="Toggle Fullscreen">
    <i data-lucide="maximize"></i>
  </button></div>
<div id="canvas"></div>
<div id="error-box"></div>
<div id="loading-box"
 style="display:flex;align-items:center;justify-content:center;
 height:300px;font-size:18px;color:rgb(0, 144, 255);">
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
  const STATUS = document.getElementById("status");
  const ERROR = document.getElementById("error-box");
  const LOADING = document.getElementById("loading-box");
  let currentXml = null;
  let diagramRendered = false;
  let fetchStarted = false;

  const viewer = new BpmnJS({{
    container: CANVAS,
    keyboard: {{ bindTo: window }}
  }});
  let rpcId = 10;
  const pendingCalls = {{}};

  // Send ui/initialize handshake to host
  window.parent.postMessage(
    {{
      jsonrpc: "2.0",
      method: "ui/initialize",
      id: 1,
      params: {{
        protocolVersion: "2025-01-26",
        clientInfo: {{ name: "bpmn-viewer", version: "1.0.0" }},
        capabilities: {{}},
      }},
    }},
    "*"
  );

  window.addEventListener("message", function (event) {{
    const msg = event.data;
    if (!msg || msg.jsonrpc !== "2.0") return;

    if (msg.method === "ui/notifications/tool-result") {{
      handleToolResult(msg.params);
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
        STATUS.textContent = "Diagram loaded";
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

  function fitWithPadding() {{
    var c = viewer.get("canvas");
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
            window.parent.postMessage(
              {{
                jsonrpc: "2.0",
                method: "ui/notifications/download",
                params: {{
                  filename: "diagram.bpmn",
                  content: result.xml,
                  mimeType: "application/xml",
                }},
              }},
              "*"
            );
          }}
        }})
        .catch(function (err) {{
          console.error("[bpmn-editor] saveXML failed:", err);
        }});
    }});

  let maximized = false;

  function setMaximized(val) {{
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
    // Tell the parent to maximize/restore the iframe
    window.parent.postMessage(
      {{
        jsonrpc: "2.0",
        method: "ui/notifications/maximize",
        params: {{ maximized: maximized }},
      }},
      "*"
    );
    // Re-fit viewport after layout change.
    // Use longer delay when restoring from maximized so the parent
    // iframe resize has time to settle.
    var delay = maximized ? 150 : 350;
    setTimeout(function () {{
      try {{ fitWithPadding(); }} catch (e) {{ /* ignore */ }}
    }}, delay);
  }}

  // Listen for parent telling us maximize state changed (e.g. ESC pressed)
  window.addEventListener("message", function (event) {{
    const msg = event.data;
    if (!msg || msg.jsonrpc !== "2.0") return;
    if (msg.method === "ui/notifications/maximize-changed") {{
      const val = msg.params && msg.params.maximized;
      if (typeof val === "boolean" && val !== maximized) {{
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
        var delay2 = maximized ? 150 : 350;
        setTimeout(function () {{
          try {{
            fitWithPadding();
          }} catch (e) {{ /* ignore */ }}
        }}, delay2);
      }}
    }}
  }});

  document
    .getElementById("btn-fullscreen")
    .addEventListener("click", function () {{
      setMaximized(!maximized);
    }});

  document
    .getElementById("btn-download-svg")
    .addEventListener("click", function () {{
      if (!diagramRendered) return;
      viewer.saveSVG()
        .then(function (result) {{
          const svg = typeof result === "string" ? result : result.svg;
          window.parent.postMessage(
            {{
              jsonrpc: "2.0",
              method: "ui/notifications/download",
              params: {{
                filename: "diagram.svg",
                content: svg,
                mimeType: "image/svg+xml",
              }},
            }},
            "*"
          );
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
