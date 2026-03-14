"""Resources for chart visualization."""

VIEW_URI = "ui://appkit/chart_view.html"

_PLOTLY_CDN = "https://cdn.plot.ly/plotly-3.4.0.min.js"

CHART_HTML = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Chart View</title>
<script src="{_PLOTLY_CDN}"></script>
<style>
:root {{
  /* Light mode (default) */
  --bg-primary: #fff;
  --text-primary: #333;
  --border-color: #e0e0e0;
}}

:root[data-theme="dark"] {{
  /* Dark mode */
  --bg-primary: #0d0d0d;
  --text-primary: #e0e0e0;
  --border-color: #333;
}}

html, body {{
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  background: var(--bg-primary);
  color: var(--text-primary);
  transition: background 0.2s, color 0.2s;
}}
#chart {{
  width: 100%;
  height: 100%;
}}

:root[data-theme="dark"] .modebar-btn svg {{
  fill: #a0a0a0 !important;
}}

:root[data-theme="dark"] .modebar-btn:hover svg {{
  fill: #e0e0e0 !important;
}}

:root[data-theme="dark"] .modebar-btn.active svg {{
  fill: #fff !important;
}}

:root[data-theme="dark"] .modebar {{
  background: rgba(255,255,255,0.05) !important;
}}
</style>
</head>
<body>
<div id="chart"><p>Waiting for chart data&hellip;</p></div>
<script>
(function () {{
  var ROOT = document.documentElement;
  var CHART = document.getElementById("chart");
  var systemThemeQuery = window.matchMedia("(prefers-color-scheme: dark)");
  var hostTheme = null;
  var isDarkMode = false;
  var resizeObserver = null;

  function handleSystemThemeChange(event) {{
    if (hostTheme === null) {{
      applyTheme(event.matches ? "dark" : "light");
    }}
  }}

  if (typeof systemThemeQuery.addEventListener === "function") {{
    systemThemeQuery.addEventListener("change", handleSystemThemeChange);
  }} else if (typeof systemThemeQuery.addListener === "function") {{
    systemThemeQuery.addListener(handleSystemThemeChange);
  }}

  applyTheme(getResolvedTheme());

  // Send ui/initialize handshake to host (MCP Apps spec 2026-01-26)
  window.parent.postMessage(
    {{
      jsonrpc: "2.0",
      method: "ui/initialize",
      id: 1,
      params: {{
        protocolVersion: "2026-01-26",
        appInfo: {{ name: "chart-view", version: "1.0.0" }},
        appCapabilities: {{
          availableDisplayModes: ["inline", "fullscreen"],
        }},
      }},
    }},
    "*"
  );

  window.addEventListener("message", function (event) {{
    var msg = event.data;
    if (!msg || msg.jsonrpc !== "2.0") return;

    if (msg.method === "ui/notifications/tool-result") {{
      handleToolResult(msg.params);
    }} else if (msg.method === "ui/notifications/tool-input") {{
      /* Tool arguments are available via msg.params.arguments when needed. */
    }} else if (msg.method === "ui/notifications/host-context-changed") {{
      applyHostContext(msg.params || {{}});
    }} else if (msg.method === "ui/resource-teardown" && msg.id != null) {{
      window.parent.postMessage(
        {{ jsonrpc: "2.0", id: msg.id, result: {{}} }},
        "*"
      );
    }} else if (msg.id === 1 && !msg.method) {{
      applyHostContext((msg.result && msg.result.hostContext) || {{}});
      window.parent.postMessage(
        {{
          jsonrpc: "2.0",
          method: "ui/notifications/initialized",
          params: {{}},
        }},
        "*"
      );
    }} else if (msg.method === "ping" && msg.id != null) {{
      window.parent.postMessage(
        {{ jsonrpc: "2.0", id: msg.id, result: {{}} }},
        "*"
      );
    }}
  }});

  function getResolvedTheme() {{
    if (hostTheme === "dark" || hostTheme === "light") {{
      return hostTheme;
    }}
    return systemThemeQuery.matches ? "dark" : "light";
  }}

  function applyHostContext(context) {{
    if (context.theme === "dark" || context.theme === "light") {{
      hostTheme = context.theme;
    }}
    applyTheme(getResolvedTheme());
    reportSize();
  }}

  function applyTheme(theme) {{
    isDarkMode = theme === "dark";
    ROOT.setAttribute("data-theme", theme);
    applyPlotlyTemplate();
  }}

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
      // Apply Plotly template after chart renders
      if (window.Plotly) {{
        setTimeout(function () {{
          applyPlotlyTemplate();
          reportSize();
        }}, 300);
      }}
      reportSize();
    }} catch (e) {{
      CHART.innerHTML = "<p>Error: " + e.message + "</p>";
    }}
  }}

  function applyPlotlyTemplate() {{
    // Find Plotly graph divs - they have class "js-plotly-plot"
    var gd = CHART.querySelector(".js-plotly-plot");
    if (!gd || !window.Plotly) return;
    var bg = isDarkMode ? "#111" : "#fff";
    var fg = isDarkMode ? "#e0e0e0" : "#333";
    var grid = isDarkMode ? "#333" : "#eee";
    var modebarBg = isDarkMode
      ? "rgba(255,255,255,0.05)"
      : "rgba(0,0,0,0.05)";
    var modebarFg = isDarkMode
      ? "rgba(255,255,255,0.5)"
      : "rgba(0,0,0,0.5)";
    var modebarActive = isDarkMode
      ? "rgba(255,255,255,0.9)"
      : "rgba(0,0,0,0.9)";
    try {{
      window.Plotly.relayout(gd, {{
        "paper_bgcolor": bg,
        "plot_bgcolor": bg,
        "font.color": fg,
        "title.font.color": fg,
        "xaxis.gridcolor": grid,
        "yaxis.gridcolor": grid,
        "xaxis.zerolinecolor": grid,
        "yaxis.zerolinecolor": grid,
        "xaxis.linecolor": grid,
        "yaxis.linecolor": grid,
        "xaxis.tickfont.color": fg,
        "yaxis.tickfont.color": fg,
        "xaxis.title.font.color": fg,
        "yaxis.title.font.color": fg,
        "legend.font.color": fg,
        "modebar.bgcolor": modebarBg,
        "modebar.color": modebarFg,
        "modebar.activecolor": modebarActive
      }});
    }} catch (e) {{
      console.warn("Plotly relayout failed:", e);
    }}
  }}

  function reportSize() {{
    var height = Math.max(
      CHART.scrollHeight,
      document.body.scrollHeight,
      document.documentElement.scrollHeight,
      400
    );
    var width = Math.max(
      CHART.scrollWidth,
      document.body.scrollWidth,
      document.documentElement.scrollWidth,
      0
    );
    var params = {{ height: height }};
    if (width > 0) {{
      params.width = width;
    }}
    window.parent.postMessage(
      {{
        jsonrpc: "2.0",
        method: "ui/notifications/size-changed",
        params: params,
      }},
      "*"
    );
  }}
  resizeObserver = new ResizeObserver(function () {{ reportSize(); }});
  resizeObserver.observe(CHART);
}})();
</script>
</body>
</html>
"""
