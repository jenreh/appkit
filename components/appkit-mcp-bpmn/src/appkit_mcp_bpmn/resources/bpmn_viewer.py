"""BPMN viewer resource endpoint."""

VIEW_URI = "ui://appkit/bpmn_viewer.html"

_BPMN_JS_CDN = "https://unpkg.com/bpmn-js@18.6.3/dist/bpmn-viewer.production.min.js"
_DIAGRAM_JS_CSS = "https://unpkg.com/bpmn-js@18.6.3/dist/assets/diagram-js.css"
_BPMN_FONT_CSS = (
    "https://unpkg.com/bpmn-js@18.6.3/dist/assets/bpmn-font/css/bpmn-embedded.css"
)

BPMN_VIEWER_HTML = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>BPMN Diagram Viewer</title>
<link rel="stylesheet" href="{_DIAGRAM_JS_CSS}" />
<link rel="stylesheet" href="{_BPMN_FONT_CSS}" />
<script src="{_BPMN_JS_CDN}"></script>
<style>
html, body {{
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #fff;
}}
#canvas {{
  width: 100%;
  height: calc(100% - 48px);
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
}}
#toolbar button {{
  padding: 6px 16px;
  border: 1px solid #228be6;
  border-radius: 4px;
  background: #228be6;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}}
#toolbar button:hover {{
  background: #1c7ed6;
}}
#status {{
  flex: 1;
  font-size: 13px;
  color: #666;
}}
#error-box {{
  display: none;
  padding: 24px;
  text-align: center;
  color: #c92a2a;
  font-size: 15px;
}}
</style>
</head>
<body>
<div id="toolbar">
  <span id="status">Loading diagram&hellip;</span>
  <button id="btn-zoom-fit" title="Fit to viewport">Fit</button>
  <button id="btn-download" title="Download .bpmn file">Download</button>
</div>
<div id="canvas"></div>
<div id="error-box"></div>
<div id="loading-box"
 style="display:flex;align-items:center;justify-content:center;
 height:calc(100% - 48px);font-size:18px;color:#228be6;">
 BPMN loading&hellip;</div>

<script>
(function () {{
  var CANVAS = document.getElementById("canvas");
  var STATUS = document.getElementById("status");
  var ERROR  = document.getElementById("error-box");
  var LOADING = document.getElementById("loading-box");
  var currentXml = null;

  var viewer = new BpmnJS({{ container: CANVAS }});
  var rpcId = 10;
  var pendingCalls = {{}};

  // Send ui/initialize handshake to host
  window.parent.postMessage({{
    jsonrpc: "2.0", method: "ui/initialize", id: 1,
    params: {{
      protocolVersion: "2025-01-26",
      clientInfo: {{ name: "bpmn-viewer", version: "1.0.0" }},
      capabilities: {{}}
    }}
  }}, "*");

  window.addEventListener("message", function (event) {{
    var msg = event.data;
    if (!msg || msg.jsonrpc !== "2.0") return;

    if (msg.method === "ui/notifications/tool-result") {{
      handleToolResult(msg.params);
    }} else if (msg.id != null && !msg.method && pendingCalls[msg.id]) {{
      // JSON-RPC response for a tools/call we sent
      var cb = pendingCalls[msg.id];
      delete pendingCalls[msg.id];
      if (msg.error) {{
        cb.reject(new Error(msg.error.message || "RPC error"));
      }} else {{
        cb.resolve(msg.result);
      }}
    }} else if (msg.method === "ping" && msg.id != null) {{
      window.parent.postMessage(
        {{ jsonrpc: "2.0", id: msg.id, result: {{}} }}, "*"
      );
    }}
  }});

  function callServerTool(name, args) {{
    return new Promise(function (resolve, reject) {{
      var id = ++rpcId;
      pendingCalls[id] = {{ resolve: resolve, reject: reject }};
      window.parent.postMessage({{
        jsonrpc: "2.0", method: "tools/call", id: id,
        params: {{ name: name, arguments: args || {{}} }}
      }}, "*");
    }});
  }}

  function handleToolResult(result) {{
    var s = JSON.stringify(result).substring(0, 500);
    console.log("[bpmn-viewer] handleToolResult:", s);
    try {{
      var text = result && result.content && result.content[0]
                 && result.content[0].text;
      if (!text) {{
        showError("No diagram data received.");
        return;
      }}
      var payload = JSON.parse(text);
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
    STATUS.textContent = "Fetching diagram\u2026";
    console.log("[bpmn-viewer] calling tools/call get_bpmn_xml", diagramId);
    callServerTool("get_bpmn_xml", {{ diagram_id: diagramId }})
      .then(function (result) {{
        var s = JSON.stringify(result).substring(0, 500);
        console.log("[bpmn-viewer] get_bpmn_xml response:", s);
        // result is CallToolResult: {{ content: [{{ text: "<xml>" }}] }}
        var xml = result && result.content && result.content[0]
                  && result.content[0].text;
        if (!xml) {{
          showError("No XML returned from get_bpmn_xml");
          return;
        }}
        // Check if it's a JSON error response
        if (xml.charAt(0) === '{{') {{
          try {{
            var err = JSON.parse(xml);
            if (!err.success) {{
              showError(err.error || "Failed to load diagram");
              return;
            }}
          }} catch (e) {{ /* not JSON, treat as XML */ }}
        }}
        renderXml(xml);
      }})
      .catch(function (err) {{
        console.error("[bpmn-viewer] get_bpmn_xml error:", err);
        showError("Failed to fetch diagram: " + err.message);
      }});
  }}

  function renderXml(xml) {{
    currentXml = xml;
    LOADING.style.display = "none";
    CANVAS.style.display = "block";
    viewer.importXML(xml).then(function (result) {{
      if (result.warnings && result.warnings.length) {{
        console.warn("BPMN import warnings:", result.warnings);
      }}
      viewer.get("canvas").zoom("fit-viewport");
      STATUS.textContent = "Diagram loaded";
      reportSize();
    }}).catch(function (err) {{
      showError("Failed to render: " + err.message);
    }});
  }}

  function showError(msg) {{
    console.error("[bpmn-viewer] showError:", msg);
    LOADING.style.display = "none";
    CANVAS.style.display = "none";
    ERROR.style.display = "block";
    ERROR.textContent = msg;
    STATUS.textContent = "Error";
    reportSize();
  }}

  document.getElementById("btn-zoom-fit").addEventListener("click", function () {{
    try {{ viewer.get("canvas").zoom("fit-viewport"); }} catch (e) {{}}
  }});

  document.getElementById("btn-download").addEventListener("click", function () {{
    if (!currentXml) return;
    var blob = new Blob([currentXml], {{ type: "application/xml" }});
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "diagram.bpmn";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }});

  function reportSize() {{
    var h = Math.max(document.body.scrollHeight, 500);
    window.parent.postMessage({{
      jsonrpc: "2.0", method: "ui/notifications/resize",
      params: {{ height: h }}
    }}, "*");
  }}
  new ResizeObserver(function () {{ reportSize(); }}).observe(document.body);
}})();
</script>
</body>
</html>
"""
