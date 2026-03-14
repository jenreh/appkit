"""Image viewer resource for MCP-App UI."""

VIEW_URI = "ui://appkit/image_viewer.html"

_LUCIDE_CDN = "https://unpkg.com/lucide@latest"

IMAGE_VIEWER_HTML = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Image Viewer</title>
<script src="{_LUCIDE_CDN}"></script>
<style>
:root {{
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
}}

:root[data-theme="dark"] {{
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
}}

html {{
  margin: 0;
  padding: 0;
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont,
    "Segoe UI", Roboto, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  transition: background 0.2s, color 0.2s;
}}
body {{
  margin: 0;
  padding: 0;
  max-width: 544px;
}}

/* ── Toolbar ── */
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
  padding: 6px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
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
}}

/* ── Normal view ── */
#content {{
  display: none;
  padding: 0;
}}
#image-container {{
  display: flex;
  justify-content: center;
  background: var(--bg-primary);
}}
#image-container img {{
  max-width: 100%;
  height: auto;
  display: block;
}}
#prompt-container {{
  padding: 16px 16px 24px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
}}
#prompt-label {{
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}}
#prompt-text {{
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-primary);
  word-break: break-word;
}}

/* ── Error / loading ── */
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
}}
#error-box .error-title {{
  font-weight: 600;
  font-size: 17px;
  margin-bottom: 8px;
}}
#error-box .error-detail {{
  color: var(--error-text-secondary);
  word-break: break-word;
}}
#loading-box {{
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  font-size: 18px;
  color: var(--loading-text);
}}

/* ── Maximized state ── */
body.maximized {{
  margin: 0;
  overflow: hidden;
  max-width: 100%;
}}
body.maximized #content {{
  display: flex !important;
  flex-direction: row;
  height: calc(100vh - 48px);
  overflow: hidden;
}}
body.maximized #image-container {{
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: var(--bg-primary);
}}
body.maximized #image-container img {{
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}}
body.maximized #prompt-container {{
  width: 320px;
  min-width: 320px;
  border-top: none;
  border-left: 1px solid var(--border-color);
  overflow-y: auto;
  padding: 20px;
  box-sizing: border-box;
}}
body.maximized #prompt-text {{
  overflow-y: auto;
}}
</style>
</head>
<body>
<div id="toolbar">
  <span id="status">Loading image&hellip;</span>
  <button id="btn-download" title="Download image">
    <i data-lucide="download"></i>
  </button>
  <span class="toolbar-separator"></span>
  <button id="btn-fullscreen" title="Maximize">
    <i data-lucide="maximize"></i>
  </button>
</div>
<div id="content">
  <div id="image-container">
    <img id="image" alt="Generated image" />
  </div>
  <div id="prompt-container">
    <div id="prompt-label">Prompt</div>
    <div id="prompt-text"></div>
  </div>
</div>
<div id="error-box"></div>
<div id="loading-box">Generating image&hellip;</div>

<script>
  function initializeIcons() {{
    if (window.lucide && window.lucide.createIcons) {{
      window.lucide.createIcons();
    }}
  }}
  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", initializeIcons);
  }} else {{
    initializeIcons();
  }}
</script>
<script>
(function () {{
  var ROOT = document.documentElement;
  var CONTENT = document.getElementById("content");
  var IMAGE = document.getElementById("image");
  var PROMPT_TEXT = document.getElementById("prompt-text");
  var STATUS = document.getElementById("status");
  var ERROR = document.getElementById("error-box");
  var LOADING = document.getElementById("loading-box");
  var PROMPT_CONTAINER = document.getElementById("prompt-container");
  var FULLSCREEN_BUTTON = document.getElementById("btn-fullscreen");

  var TRUNCATE_LEN = 200;
  var imageData = {{}};
  var imageRendered = false;
  var maximized = false;
  var hostTheme = null;
  var systemThemeQuery = window.matchMedia("(prefers-color-scheme: dark)");
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

  // ── MCP handshake ──
  window.parent.postMessage(
    {{
      jsonrpc: "2.0",
      method: "ui/initialize",
      id: 1,
      params: {{
        protocolVersion: "2026-01-26",
        appInfo: {{
          name: "image-viewer",
          version: "1.0.0",
        }},
        appCapabilities: {{
          availableDisplayModes: ["inline", "fullscreen"],
        }},
      }},
    }},
    "*"
  );

  window.addEventListener("message", function (ev) {{
    var msg = ev.data;
    if (!msg || msg.jsonrpc !== "2.0") return;

    if (msg.method === "ui/notifications/tool-result") {{
      handleToolResult(msg.params);
    }} else if (msg.method === "ui/notifications/tool-input") {{
      /* Tool arguments are available via msg.params.arguments when needed. */
    }} else if (msg.method === "ui/notifications/host-context-changed") {{
      var context = msg.params || {{}};
      if (context.theme === "dark" || context.theme === "light") {{
        hostTheme = context.theme;
        applyTheme(getResolvedTheme());
      }}
      if (context.displayMode) {{
        var wantFullscreen = context.displayMode === "fullscreen";
        if (wantFullscreen !== maximized) {{
          applyMaximizedState(wantFullscreen);
        }}
      }}
    }} else if (msg.method === "ui/resource-teardown" && msg.id != null) {{
      window.parent.postMessage(
        {{ jsonrpc: "2.0", id: msg.id, result: {{}} }},
        "*"
      );
    }} else if (msg.id === 1 && !msg.method) {{
      var hostContext = (msg.result && msg.result.hostContext) || {{}};
      if (hostContext.theme === "dark" || hostContext.theme === "light") {{
        hostTheme = hostContext.theme;
        applyTheme(getResolvedTheme());
      }}
      if (hostContext.displayMode === "fullscreen") {{
        applyMaximizedState(true);
      }}
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

  function applyTheme(theme) {{
    ROOT.setAttribute("data-theme", theme);
  }}

  // ── Tool result handling ──
  function handleToolResult(result) {{
    clearLoadTimeout();
    if (imageRendered) return;
    try {{
      var text =
        result &&
        result.content &&
        result.content[0] &&
        result.content[0].text;
      if (!text) {{
        showError("No image data received.");
        return;
      }}
      var payload = JSON.parse(text);
      if (!payload.success) {{
        showError(payload.error || "Unknown error");
        return;
      }}
      imageData = payload;
      renderImage();
    }} catch (e) {{
      showError("Error: " + e.message);
    }}
  }}

  function renderImage() {{
    if (imageRendered) return;
    imageRendered = true;

    LOADING.style.display = "none";
    ERROR.style.display = "none";
    CONTENT.style.display = "block";

    IMAGE.src = imageData.image_url;
    IMAGE.onerror = function () {{
      showError("Failed to load image from URL.");
    }};

    updatePromptDisplay();

    STATUS.textContent = "Generiertes Bild";
    reportSize();
  }}

  function updatePromptDisplay() {{
    var p = imageData.enhanced_prompt
      || imageData.prompt || "";
    if (!p) {{
      PROMPT_CONTAINER.style.display = "none";
      return;
    }}
    PROMPT_CONTAINER.style.display = "block";
    if (maximized) {{
      PROMPT_TEXT.textContent = p;
    }} else if (p.length > TRUNCATE_LEN) {{
      PROMPT_TEXT.textContent =
        p.substring(0, TRUNCATE_LEN) + "\u2026";
    }} else {{
      PROMPT_TEXT.textContent = p;
    }}
  }}

  // ── Error / timeout ──
  function showError(msg) {{
    if (imageRendered) return;
    LOADING.style.display = "none";
    CONTENT.style.display = "none";
    ERROR.style.display = "block";
    ERROR.innerHTML =
      '<div class="error-title">' +
      "\u26a0\ufe0f Image generation failed</div>" +
      '<div class="error-detail">' +
      escapeHtml(String(msg)) +
      "</div>";
    STATUS.textContent = "Error";
    reportSize();
  }}

  function escapeHtml(s) {{
    var d = document.createElement("div");
    d.appendChild(document.createTextNode(s));
    return d.innerHTML;
  }}

  var loadTimeout = setTimeout(function () {{
    if (LOADING.style.display !== "none") {{
      showError(
        "Timed out waiting for image data. " +
        "Generation may have failed silently."
      );
    }}
  }}, 120000);

  function clearLoadTimeout() {{
    if (loadTimeout) {{
      clearTimeout(loadTimeout);
      loadTimeout = null;
    }}
  }}

  window.addEventListener("error", function (e) {{
    showError("Unexpected error: " + (e.message || e));
  }});

  // ── Download ──
  document.getElementById("btn-download")
    .addEventListener("click", function () {{
    if (!imageData.image_url) return;
    fetch(imageData.image_url)
      .then(function (r) {{ return r.blob(); }})
      .then(function (blob) {{
        var a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = getFilename(
          imageData.image_url
        );
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
      }})
      .catch(function (err) {{
        console.error(
          "[image-viewer] download failed:", err
        );
      }});
  }});

  function getFilename(url) {{
    try {{
      var parts = new URL(url).pathname.split("/");
      var last = parts[parts.length - 1];
      if (last && last.indexOf(".") !== -1) return last;
    }} catch (e) {{ /* ignore */ }}
    return "generated_image.jpeg";
  }}

  // ── Maximize / minimize ──
  function applyMaximizedState(val) {{
    maximized = val;
    if (maximized) {{
      document.body.classList.add("maximized");
    }} else {{
      document.body.classList.remove("maximized");
    }}
    var icon = FULLSCREEN_BUTTON.querySelector("i");
    if (icon) {{
      icon.setAttribute(
        "data-lucide",
        maximized ? "minimize" : "maximize"
      );
      if (window.lucide && window.lucide.createIcons) {{
        window.lucide.createIcons();
      }}
    }}
    updatePromptDisplay();
    setTimeout(reportSize, 100);
  }}

  function setMaximized(val) {{
    applyMaximizedState(val);
    window.parent.postMessage(
      {{
        jsonrpc: "2.0",
        method: "ui/request-display-mode",
        id: Date.now(),
        params: {{ mode: maximized ? "fullscreen" : "inline" }},
      }},
      "*"
    );
  }}

  document.getElementById("btn-fullscreen")
    .addEventListener("click", function () {{
    setMaximized(!maximized);
  }});

  // ── Size reporting ──
  function reportSize() {{
    var h = Math.max(
      document.body.scrollHeight, 300
    );
    var w = maximized
      ? document.body.scrollWidth
      : 544;
    window.parent.postMessage(
      {{
        jsonrpc: "2.0",
        method: "ui/notifications/size-changed",
        params: {{ height: h, width: w }},
      }},
      "*"
    );
  }}
  resizeObserver = new ResizeObserver(function () {{
    reportSize();
  }});
  resizeObserver.observe(document.body);
}})();
</script>
</body>
</html>
"""
