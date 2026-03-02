"""Resources for chart visualization."""

VIEW_URI = "ui://appkit/chart_view.html"

_PLOTLY_CDN = "https://cdn.plot.ly/plotly-latest.min.js"

CHART_HTML = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Chart View</title>
<script src="{_PLOTLY_CDN}"></script>
<style>
html, body {{ margin:0; padding:0; width:100%; height:100%; }}
#chart {{ width:100%; height:100%; }}
</style>
</head>
<body>
<div id="chart"><p>Waiting for chart data&hellip;</p></div>
<script>
(function () {{
  var CHART = document.getElementById("chart");

  // Send ui/initialize handshake to host
  window.parent.postMessage({{
    jsonrpc: "2.0", method: "ui/initialize", id: 1,
    params: {{
      protocolVersion: "2025-01-26",
      clientInfo: {{ name: "chart-view", version: "1.0.0" }},
      capabilities: {{}}
    }}
  }}, "*");

  window.addEventListener("message", function (event) {{
    var msg = event.data;
    if (!msg || msg.jsonrpc !== "2.0") return;

    if (msg.method === "ui/notifications/tool-result") {{
      handleToolResult(msg.params);
    }} else if (msg.method === "ping" && msg.id != null) {{
      window.parent.postMessage({{ jsonrpc: "2.0", id: msg.id, result: {{}} }}, "*");
    }}
  }});

  function handleToolResult(result) {{
    try {{
      var text = result && result.content && result.content[0]
                 && result.content[0].text;
      if (!text) {{ CHART.innerHTML = "<p>No chart data.</p>"; return; }}
      var payload = JSON.parse(text);
      if (!payload.success || !payload.html) {{
        CHART.innerHTML = "<p>" + (payload.error || "Unknown error") + "</p>";
        return;
      }}
      // Insert the Plotly <div> fragment and execute its inline scripts
      CHART.innerHTML = payload.html;
      CHART.querySelectorAll("script").forEach(function (old) {{
        var s = document.createElement("script");
        s.textContent = old.textContent;
        old.parentNode.replaceChild(s, old);
      }});
      reportSize();
    }} catch (e) {{
      CHART.innerHTML = "<p>Error: " + e.message + "</p>";
    }}
  }}

  function reportSize() {{
    window.parent.postMessage({{
      jsonrpc: "2.0", method: "ui/notifications/resize",
      params: {{ height: Math.max(CHART.scrollHeight, 400) }}
    }}, "*");
  }}
  new ResizeObserver(function () {{ reportSize(); }}).observe(CHART);
}})();
</script>
</body>
</html>
"""
