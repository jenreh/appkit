/**
 * McpAppBridge — Host-side React component for MCP Apps.
 *
 * Implements the MCP Apps spec lifecycle (2026-01-26):
 *   Phase 1: Connection & Discovery (backend McpAppsService)
 *   Phase 2: UI Initialization via ui/initialize ↔ McpUiInitializeResult
 *   Phase 3: Interactive Phase (tools/call, resources/read, ui/open-link, etc.)
 *   Phase 4: Cleanup via ui/resource-teardown on unmount
 *
 * Spec: https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx
 */

import React, { useRef, useEffect, useState, useCallback } from "react";

/** Protocol version as per spec. */
const PROTOCOL_VERSION = "2026-01-26";

/**
 * Post a JSON-RPC notification to the iframe.
 */
function postToIframe(iframe, method, params = {}, id = null) {
  if (!iframe || !iframe.contentWindow) return;
  const msg = { jsonrpc: "2.0", method, params };
  if (id !== null) msg.id = id;
  // srcdoc iframes have an opaque ("null") origin, so we must use "*".
  // Security is enforced by checking event.source on the receive side.
  iframe.contentWindow.postMessage(msg, "*");
}

/**
 * Post a JSON-RPC success response to the iframe.
 */
function respondToIframe(iframe, id, result) {
  if (!iframe || !iframe.contentWindow) return;
  iframe.contentWindow.postMessage({ jsonrpc: "2.0", id, result }, "*");
}

/**
 * Post a JSON-RPC error response to the iframe.
 */
function respondErrorToIframe(iframe, id, code, message) {
  if (!iframe || !iframe.contentWindow) return;
  iframe.contentWindow.postMessage(
    { jsonrpc: "2.0", id, error: { code, message } },
    "*"
  );
}

export function McpAppBridge({
  // Reflex may pass props as camelCase or snake_case depending on version.
  // Accept both naming conventions with fallback.
  resource_uri,
  resourceUri,
  tool_input,
  toolInput,
  tool_result,
  toolResult,
  server_id,
  serverId,
  server_name,
  serverName,
  tool_name,
  toolName,
  theme = "light",
  max_height,
  maxHeight,
  prefers_border,
  prefersBorder,
  on_message,
  onMessage,
  backend_url,
  backendUrl,
  ...rest
}) {
  // Resolve props: prefer snake_case (Reflex custom component default), fall back to camelCase
  const _resourceUri = resource_uri || resourceUri || "";
  const _toolInput = tool_input ?? toolInput ?? "{}";
  const _toolResult = tool_result ?? toolResult ?? "null";
  const _serverId = server_id ?? serverId ?? 0;
  const _serverName = server_name || serverName || "";
  const _toolName = tool_name || toolName || "";
  const _maxHeight = max_height ?? maxHeight ?? 600;
  const _prefersBorder = prefers_border ?? prefersBorder ?? true;
  const _onMessage = on_message || onMessage;
  // Backend URL: strip trailing slash; fall back to same-origin (production)
  const _backendUrl = (backend_url || backendUrl || "").replace(/\/+$/, "");
  const iframeRef = useRef(null);
  const [iframeHeight, setIframeHeight] = useState(0);
  const [iframeWidth, setIframeWidth] = useState(null);
  const [ready, setReady] = useState(false);
  const [htmlContent, setHtmlContent] = useState("");
  const [fetchError, setFetchError] = useState("");
  const [isMaximized, setIsMaximized] = useState(false);
  const isMaximizedRef = useRef(false);
  // Keep ref in sync so handleMessage callback can access current value
  useEffect(() => { isMaximizedRef.current = isMaximized; }, [isMaximized]);
  // Lightweight auto-height script injected into MCP app HTML.
  // Reports scrollHeight once on load and once after a short settle delay.
  // Apps that need dynamic resizing should use ui/notifications/size-changed.
  // No ResizeObserver/MutationObserver — those cause feedback loops.
  const AUTO_SIZE_SCRIPT = `<script>
(function(){
  function report(){
    var h=document.documentElement.scrollHeight;
    var w=document.documentElement.scrollWidth;
    var p={};if(h>0)p.height=h;if(w>0)p.width=w;
    if(p.height||p.width){window.parent.postMessage({jsonrpc:"2.0",method:"ui/notifications/size-changed",params:p},"*");}
  }
  window.addEventListener("load",function(){report();setTimeout(report,300);});
})();
<\/script>`;

  // Resource metadata from X-MCP-* response headers (spec §UI Resource Format)
  const [resourceCsp, setResourceCsp] = useState(null);
  const [resourcePermissions, setResourcePermissions] = useState(null);
  const [resourcePrefersBorder, setResourcePrefersBorder] = useState(null);

  // Build the resource URL with proper URI encoding
  const resourceUrl = React.useMemo(() => {
    if (!_resourceUri) return "";
    return `${_backendUrl}/api/mcp-apps/${_serverId}/resource?uri=${encodeURIComponent(_resourceUri)}`;
  }, [_backendUrl, _serverId, _resourceUri]);

  // Debug: log resolved props on mount/change
  useEffect(() => {
    console.debug("[McpAppBridge] props:", {
      resourceUri: _resourceUri,
      serverId: _serverId,
      toolName: _toolName,
      resourceUrl,
    });
  }, [_resourceUri, _serverId, _toolName, resourceUrl]);

  // Parse JSON props safely.
  // Props may arrive as a JSON string (when typed as Var[str]) OR as a
  // plain JS object (when Reflex serialises a dict/None state field
  // and the prop type coercion keeps it as an object).  Handle both.
  const _parseOrUse = (v, fallback) => {
    if (v === null || v === undefined) return fallback;
    if (typeof v === "string") {
      try { return JSON.parse(v); } catch { return fallback; }
    }
    return v; // already a JS object/array
  };

  const parsedInput = React.useMemo(
    () => _parseOrUse(_toolInput, {}),
    [_toolInput]
  );

  const parsedResult = React.useMemo(
    () => _parseOrUse(_toolResult, null),
    [_toolResult]
  );

  // Build CSS variables from theme (spec: HostContext.styles.variables)
  const cssVars = React.useMemo(() => ({
    "--color-background-primary": theme === "dark" ? "#1a1b1e" : "#ffffff",
    "--color-background-secondary": theme === "dark" ? "#25262b" : "#f8f9fa",
    "--color-text-primary": theme === "dark" ? "#c1c2c5" : "#000000",
    "--color-text-secondary": theme === "dark" ? "#909296" : "#495057",
    "--color-border-primary": theme === "dark" ? "#373a40" : "#dee2e6",
    "--font-sans": "system-ui, sans-serif",
    "--font-mono": "monospace",
    "--border-radius-sm": "4px",
    "--border-radius-md": "8px",
  }), [theme]);

  // Fetch HTML content from the resource endpoint
  // Also reads X-MCP-* response headers for CSP/permissions metadata
  useEffect(() => {
    if (!resourceUrl) return;
    setFetchError("");
    fetch(resourceUrl, { credentials: "omit" })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        // Read spec metadata from response headers
        const cspHeader = r.headers.get("X-MCP-CSP");
        const permissionsHeader = r.headers.get("X-MCP-Permissions");
        const prefersBorderHeader = r.headers.get("X-MCP-Prefers-Border");
        if (cspHeader) {
          try { setResourceCsp(JSON.parse(cspHeader)); } catch { /* ignore */ }
        }
        if (permissionsHeader) {
          try { setResourcePermissions(JSON.parse(permissionsHeader)); } catch { /* ignore */ }
        }
        if (prefersBorderHeader !== null) {
          setResourcePrefersBorder(prefersBorderHeader === "true");
        }
        return r.text();
      })
      .then((html) => {
        // Inject auto-size reporter before </body>, </html>, or at the end
        if (html.includes("</body>")) {
          html = html.replace("</body>", AUTO_SIZE_SCRIPT + "</body>");
        } else if (html.includes("</html>")) {
          html = html.replace("</html>", AUTO_SIZE_SCRIPT + "</html>");
        } else {
          html = html + AUTO_SIZE_SCRIPT;
        }
        setHtmlContent(html);
      })
      .catch((err) => {
        console.error("Failed to fetch MCP App resource:", err);
        setFetchError(String(err));
        setHtmlContent("");
      });
  }, [resourceUrl]);

  // Handle messages from iframe (spec §Communication Protocol)
  const handleMessage = useCallback((event) => {
    const data = event.data;
    if (!data || data.jsonrpc !== "2.0") return;

    // Only accept messages from our sandboxed iframe
    if (event.source !== iframeRef.current?.contentWindow) return;

    const iframe = iframeRef.current;

    // ── LIFECYCLE: Phase 2 ────────────────────────────────────────────────
    // ui/initialize (View → Host): MCP-like handshake
    // Host MUST respond with McpUiInitializeResult then send tool-input.
    if (data.method === "ui/initialize" && data.id != null) {
      setReady(true);

      // Spec: McpUiInitializeResult
      respondToIframe(iframe, data.id, {
        protocolVersion: PROTOCOL_VERSION,
        hostInfo: { name: "appkit", version: "1.0.0" },
        hostCapabilities: {
          openLinks: {},
          serverTools: { listChanged: false },
          serverResources: { listChanged: false },
          logging: {},
          sandbox: {
            csp: {
              connectDomains: [],
              resourceDomains: [],
            },
          },
        },
        hostContext: {
          theme,
          displayMode: "inline",
          availableDisplayModes: ["inline"],
          platform: "web",
          containerDimensions: { maxHeight: _maxHeight },
          styles: { variables: cssVars },
        },
      });

      // Spec: Host MUST send ui/notifications/tool-input after handshake
      // Params: { arguments: Record<string, unknown> }
      postToIframe(iframe, "ui/notifications/tool-input", {
        arguments: parsedInput,
      });

      // Spec: Host MUST send ui/notifications/tool-result when available
      if (parsedResult !== null) {
        postToIframe(iframe, "ui/notifications/tool-result", parsedResult);
      }
      return;
    }

    // ping: Connection health check (spec §Standard MCP Messages)
    if (data.method === "ping" && data.id != null) {
      respondToIframe(iframe, data.id, {});
      return;
    }

    // ── INTERACTIVE PHASE: Phase 3 ────────────────────────────────────────
    // tools/call (View → Host): Proxy to MCP server
    if (data.method === "tools/call" && data.id != null) {
      const reqId = data.id;
      const params = data.params || {};
      fetch(`${_backendUrl}/api/mcp-apps/${_serverId}/tools/call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "omit",
        body: JSON.stringify({
          tool_name: params.name,
          arguments: params.arguments || {},
        }),
      })
        .then((r) => r.ok ? r.json() : Promise.reject(r.status))
        .then((result) => respondToIframe(iframe, reqId, result))
        .catch(() =>
          respondErrorToIframe(iframe, reqId, -32000, "Tool call failed")
        );
      return;
    }

    // resources/read (View → Host): Proxy resource fetch to MCP server
    if (data.method === "resources/read" && data.id != null) {
      const reqId = data.id;
      const uri = data.params?.uri;
      if (!uri) {
        respondErrorToIframe(iframe, reqId, -32602, "Missing uri parameter");
        return;
      }
      fetch(
        `${_backendUrl}/api/mcp-apps/${_serverId}/resource?uri=${encodeURIComponent(uri)}`,
        { credentials: "omit" }
      )
        .then((r) => r.ok ? r.text() : Promise.reject(r.status))
        .then((html) =>
          respondToIframe(iframe, reqId, {
            contents: [
              { uri, mimeType: "text/html;profile=mcp-app", text: html },
            ],
          })
        )
        .catch(() =>
          respondErrorToIframe(iframe, reqId, -32002, "Resource not found")
        );
      return;
    }

    // ui/open-link (View → Host): Open external URL in browser
    if (data.method === "ui/open-link") {
      const url = data.params?.url;
      if (url && (url.startsWith("https://") || url.startsWith("http://"))) {
        window.open(url, "_blank", "noopener,noreferrer");
        if (data.id != null) respondToIframe(iframe, data.id, {});
      } else if (data.id != null) {
        respondErrorToIframe(iframe, data.id, -32000, "Invalid URL");
      }
      return;
    }

    // ui/notifications/download (View → Host): Trigger file download
    if (data.method === "ui/notifications/download") {
      const { filename, content, mimeType } = data.params || {};
      if (filename && content) {
        const blob = new Blob([content], { type: mimeType || "application/octet-stream" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        // Delay revoke to give the browser time to start the download
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
      return;
    }

    // ui/notifications/size-changed (View → Host): Resize iframe
    // Skip size updates while maximized to avoid inflating stored dimensions
    if (data.method === "ui/notifications/size-changed") {
      if (isMaximizedRef.current) return;
      const h = data.params?.height;
      if (typeof h === "number" && h > 0) {
        setIframeHeight(Math.min(h, _maxHeight));
      }
      const w = data.params?.width;
      if (typeof w === "number" && w > 0) {
        setIframeWidth(w);
      }
      return;
    }

    // ui/notifications/maximize (View → Host): Toggle maximized overlay
    if (data.method === "ui/notifications/maximize") {
      const maximize = data.params?.maximized;
      setIsMaximized(typeof maximize === "boolean" ? maximize : (prev) => !prev);
      return;
    }

    // ui/message (View → Host): Insert message into chat
    // Spec: respond with { isError: boolean }
    if (data.method === "ui/message") {
      if (data.id != null) respondToIframe(iframe, data.id, { isError: false });
      if (_onMessage) {
        _onMessage(JSON.stringify(data.params || {}));
      }
      return;
    }

    // ui/request-display-mode (View → Host): Change display mode
    // We only support "inline"; return current mode.
    if (data.method === "ui/request-display-mode" && data.id != null) {
      respondToIframe(iframe, data.id, { mode: "inline" });
      return;
    }

    // ui/update-model-context (View → Host): Update model context
    // Accept and acknowledge; full model context piping is a future enhancement.
    if (data.method === "ui/update-model-context" && data.id != null) {
      respondToIframe(iframe, data.id, {});
      return;
    }

    // notifications/message (View → Host): Log message
    if (data.method === "notifications/message") {
      const level = data.params?.level ?? "info";
      const logger = data.params?.logger ?? "mcp-app";
      const msg = data.params?.data ?? "";
      console[level === "error" ? "error" : level === "warning" ? "warn" : "log"](
        `[MCP App][${logger}]`, msg
      );
      return;
    }
  }, [cssVars, _maxHeight, parsedInput, parsedResult, _serverId, theme, _toolName, _onMessage]);

  // ESC key to exit maximized mode
  useEffect(() => {
    if (!isMaximized) return;
    const handleEsc = (e) => {
      if (e.key === "Escape") {
        setIsMaximized(false);
        // Notify the iframe that maximize was cancelled
        const iframe = iframeRef.current;
        postToIframe(iframe, "ui/notifications/maximize-changed", { maximized: false });
      }
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [isMaximized]);

  useEffect(() => {
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [handleMessage]);

  // Push updated tool-input when props change and app is ready
  // Spec: ui/notifications/tool-input params = { arguments }
  useEffect(() => {
    if (!ready) return;
    const iframe = iframeRef.current;
    postToIframe(iframe, "ui/notifications/tool-input", {
      arguments: parsedInput,
    });
  }, [ready, _toolInput, _toolName]);

  // Push tool-result when available and app is ready
  // Spec: ui/notifications/tool-result params = CallToolResult
  useEffect(() => {
    if (!ready || parsedResult === null) return;
    const iframe = iframeRef.current;
    postToIframe(iframe, "ui/notifications/tool-result", parsedResult);
  }, [ready, _toolResult]);

  // Push theme/context changes via ui/notifications/host-context-changed
  // Spec: params = Partial<HostContext>
  useEffect(() => {
    if (!ready) return;
    const iframe = iframeRef.current;
    postToIframe(iframe, "ui/notifications/host-context-changed", {
      theme,
      styles: { variables: cssVars },
    });
  }, [ready, theme, cssVars]);

  // Phase 4: Cleanup — send ui/resource-teardown before unmounting
  // Spec: Host MUST send this before tearing down the View.
  useEffect(() => {
    return () => {
      const iframe = iframeRef.current;
      if (iframe && iframe.contentWindow && ready) {
        postToIframe(
          iframe,
          "ui/resource-teardown",
          { reason: "component unmounted" },
          Date.now()
        );
      }
    };
  }, [ready]);

  if (!resourceUrl) return null;

  // While loading or on fetch error, render a placeholder with defined height
  // so the conversation layout doesn't collapse.
  if (!htmlContent) {
    const placeholderBorder = `1px solid ${theme === "dark" ? "#373a40" : "#dee2e6"}`;
    return (
      <div
        style={{
          width: "100%",
          minHeight: "60px",
          borderRadius: "8px",
          border: placeholderBorder,
          marginTop: "8px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: theme === "dark" ? "#909296" : "#868e96",
          fontSize: "13px",
          padding: "12px",
        }}
      >
        {fetchError ? `⚠ MCP App: ${fetchError}` : "Loading MCP App…"}
      </div>
    );
  }

  const effectivePrefersBorder =
    resourcePrefersBorder !== null ? resourcePrefersBorder : _prefersBorder;
  const borderStyle = effectivePrefersBorder
    ? `1px solid ${theme === "dark" ? "#373a40" : "#dee2e6"}`
    : "none";

  // Build iframe Permission-Policy allow attribute from resource permissions
  // Spec §Host Behavior: Host MAY honor permissions by setting allow attribute
  const allowParts = ["allow-scripts", "allow-popups", "allow-forms", "allow-downloads", "allow-same-origin"];
  if (resourcePermissions?.camera) allowParts.push("allow-camera");
  if (resourcePermissions?.microphone) allowParts.push("allow-microphone");
  if (resourcePermissions?.geolocation) allowParts.push("allow-geolocation");

  // Build referrerPolicy: restrictive by default (no referrer to untrusted HTML)
  const sandboxAttr = allowParts.join(" ");

  const containerWidth = iframeWidth ? `${iframeWidth}px` : "auto";

  const containerStyle = isMaximized
    ? {
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        zIndex: 9999,
        borderRadius: 0,
        overflow: "hidden",
        border: "none",
        margin: 0,
        background: "#fff",
      }
    : {
        width: containerWidth,
        maxWidth: "100%",
        borderRadius: "8px",
        overflow: "hidden",
        border: borderStyle,
        marginTop: "8px",
      };

  const iframeStyle = isMaximized
    ? {
        width: "100%",
        height: "100%",
        border: "none",
        display: "block",
      }
    : {
        width: iframeWidth ? `${iframeWidth}px` : "100%",
        height: `${iframeHeight}px`,
        border: "none",
        display: "block",
      };

  return (
    <div style={containerStyle}>
      <iframe
        ref={iframeRef}
        srcDoc={htmlContent}
        style={iframeStyle}
        sandbox={sandboxAttr}
        referrerPolicy="no-referrer"
        title={`MCP App: ${_toolName}`}
      />
    </div>
  );
}

export default McpAppBridge;
