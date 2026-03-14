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

/**
 * Build a Content-Security-Policy <meta> tag from resource CSP metadata.
 * Spec §Security §4: Host MUST enforce CSP based on declared domains.
 * Injected as the FIRST element in <head> so it takes precedence.
 *
 * Returns null when csp is null/undefined — in that case the caller MUST NOT
 * inject a meta tag, and the iframe sandbox attribute acts as the security
 * boundary.  Injecting a restrictive default when no metadata is present would
 * block external resources that the server legitimately loads (e.g. CDN assets
 * declared in AppConfig but not yet forwarded as X-MCP-CSP headers).
 */
function buildCspMetaTag(csp) {
  if (!csp) return null;
  const connectSrc = csp.connectDomains?.join(" ") || "";
  const resourceSrc = csp.resourceDomains?.join(" ") || "";
  const frameSrc = csp.frameDomains?.join(" ") || "'none'";
  const baseUri = csp.baseUriDomains?.join(" ") || "'self'";
  const directives = [
    "default-src 'none'",
    `script-src 'self' 'unsafe-inline'${resourceSrc ? " " + resourceSrc : ""}`,
    `style-src 'self' 'unsafe-inline'${resourceSrc ? " " + resourceSrc : ""}`,
    `img-src 'self' data:${resourceSrc ? " " + resourceSrc : ""}`,
    `font-src 'self'${resourceSrc ? " " + resourceSrc : ""}`,
    `media-src 'self' data:${resourceSrc ? " " + resourceSrc : ""}`,
    `connect-src 'self'${connectSrc ? " " + connectSrc : ""}`,
    `frame-src ${frameSrc}`,
    "object-src 'none'",
    `base-uri ${baseUri}`,
  ].join("; ");
  return `<meta http-equiv="Content-Security-Policy" content="${directives}">`;
}

/**
 * Normalize fetched HTML before injecting it into srcdoc.
 *
 * This defensively removes accidental nullish prefixes that break document
 * parsing by forcing head metadata into the body as visible text.
 */
function normalizeSrcDocHtml(html) {
  if (typeof html !== "string") return "";

  let normalized = html.replace(/^\uFEFF/, "");

  normalized = normalized.replace(
    /^\s*(?:null|undefined)\s*(?=(<!DOCTYPE|<html|<head|<meta|<title|<link|<script|<style))/i,
    ""
  );

  normalized = normalized.replace(
    /(<head\b[^>]*>)\s*(?:null|undefined)\s*/i,
    "$1"
  );

  return normalized;
}

/**
 * Inject markup as the first child of <head> when possible.
 */
function injectIntoHead(html, fragment) {
  if (typeof html !== "string" || html === "") return html;
  if (typeof fragment !== "string" || fragment.trim() === "") return html;

  const headMatch = html.match(/<head\b[^>]*>/i);
  if (headMatch) {
    return html.replace(headMatch[0], `${headMatch[0]}\n${fragment}`);
  }

  const htmlMatch = html.match(/<html\b[^>]*>/i);
  if (htmlMatch) {
    return html.replace(htmlMatch[0], `${htmlMatch[0]}\n<head>\n${fragment}\n</head>`);
  }

  const doctypeMatch = html.match(/<!DOCTYPE html>/i);
  if (doctypeMatch) {
    return html.replace(doctypeMatch[0], `${doctypeMatch[0]}\n<head>\n${fragment}\n</head>`);
  }

  return `${fragment}\n${html}`;
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
  user_id,
  userId,
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
  const _userId = user_id ?? userId ?? 0;
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
  // View-declared capabilities (populated on ui/initialize, used for mode gating)
  const viewCapabilitiesRef = useRef({});
  // Ref mirrors of resource CSP/permissions so handleMessage avoids stale closures
  const resourceCspRef = useRef(null);
  const resourcePermissionsRef = useRef(null);
  // Prevent double-send of tool-input/result (sent once in initialized handler,
  // refs suppress the first effect-triggered send when `ready` becomes true)
  const toolInputInitialSentRef = useRef(false);
  const toolResultInitialSentRef = useRef(false);
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
    fetch(resourceUrl, {
      credentials: "omit",
      headers: {
        "ngrok-skip-browser-warning": "true",
        ...(_userId > 0 ? { "x-user-id": String(_userId) } : {}),
      },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        // Read spec metadata from response headers
        const cspHeader = r.headers.get("X-MCP-CSP");
        const permissionsHeader = r.headers.get("X-MCP-Permissions");
        const prefersBorderHeader = r.headers.get("X-MCP-Prefers-Border");
        let parsedCsp = null;
        if (cspHeader) {
          try {
            parsedCsp = JSON.parse(cspHeader);
            resourceCspRef.current = parsedCsp;
            setResourceCsp(parsedCsp);
          } catch { /* ignore */ }
        }
        if (permissionsHeader) {
          try {
            const parsedPerms = JSON.parse(permissionsHeader);
            resourcePermissionsRef.current = parsedPerms;
            setResourcePermissions(parsedPerms);
          } catch { /* ignore */ }
        }
        if (prefersBorderHeader !== null) {
          setResourcePrefersBorder(prefersBorderHeader === "true");
        }
        return r.text().then((html) => ({ html, parsedCsp }));
      })
      .then(({ html, parsedCsp }) => {
        html = normalizeSrcDocHtml(html);
        // Inject CSP as FIRST element in <head> only when server provided metadata (spec §4).
        // When parsedCsp is null we skip injection and rely on the iframe sandbox attribute.
        const cspMeta = buildCspMetaTag(parsedCsp);
        html = injectIntoHead(html, cspMeta);
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
      // Store view capabilities for display-mode gating and future use
      viewCapabilitiesRef.current = data.params?.appCapabilities || {};
      // Spec: respond with McpUiInitializeResult but do NOT send data yet.
      // Host MUST wait for ui/notifications/initialized before sending anything.
      const csp = resourceCspRef.current;
      const perms = resourcePermissionsRef.current;
      const sandboxPerms = perms ? {
        ...(perms.camera ? { camera: {} } : {}),
        ...(perms.microphone ? { microphone: {} } : {}),
        ...(perms.geolocation ? { geolocation: {} } : {}),
        ...(perms.clipboardWrite ? { clipboardWrite: {} } : {}),
      } : undefined;
      respondToIframe(iframe, data.id, {
        protocolVersion: PROTOCOL_VERSION,
        hostInfo: { name: "appkit", version: "1.0.0" },
        hostCapabilities: {
          openLinks: {},
          serverTools: { listChanged: false },
          serverResources: { listChanged: false },
          logging: {},
          sandbox: {
            ...(sandboxPerms ? { permissions: sandboxPerms } : {}),
            csp: {
              connectDomains: csp?.connectDomains || [],
              resourceDomains: csp?.resourceDomains || [],
              frameDomains: csp?.frameDomains || [],
              baseUriDomains: csp?.baseUriDomains || [],
            },
          },
        },
        hostContext: {
          theme,
          ...(_toolName ? { toolInfo: { tool: { name: _toolName, description: "", inputSchema: { type: "object" } } } } : {}),
          displayMode: "inline",
          availableDisplayModes: ["inline", "fullscreen"],
          platform: "web",
          containerDimensions: { maxHeight: _maxHeight },
          styles: { variables: cssVars },
        },
      });
      return;
    }

    // ui/notifications/initialized (View → Host): View is ready to receive data.
    // Spec: Host MUST NOT send any request/notification before this arrives.
    if (data.method === "ui/notifications/initialized") {
      // Mark as sent so the ready-triggered effects don't double-send
      toolInputInitialSentRef.current = true;
      setReady(true);
      postToIframe(iframe, "ui/notifications/tool-input", {
        arguments: parsedInput,
      });
      if (parsedResult !== null) {
        toolResultInitialSentRef.current = true;
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
        headers: {
          "Content-Type": "application/json",
          ...(_userId > 0 ? { "x-user-id": String(_userId) } : {}),
        },
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
        {
          credentials: "omit",
          headers: {
            ...(_userId > 0 ? { "x-user-id": String(_userId) } : {}),
          },
        }
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

    // ui/notifications/download (View → Host): Trigger file download (legacy)
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

    // ui/download-file (View → Host): Spec-compliant download request (2026-01-26)
    if (data.method === "ui/download-file" && data.id != null) {
      const resource = (data.params?.contents || [])[0]?.resource;
      if (resource) {
        const mimeType = resource.mimeType || "application/octet-stream";
        const filename = resource.uri
          ? decodeURIComponent(resource.uri.split("/").pop() || "download")
          : "download";
        let blobData;
        if (resource.text !== undefined) {
          // text field: plain string content
          blobData = new Blob([resource.text], { type: mimeType });
        } else if (resource.blob !== undefined) {
          // blob field: base64-encoded binary (spec §UI Resource Format)
          try {
            const binary = atob(resource.blob);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
            blobData = new Blob([bytes], { type: mimeType });
          } catch {
            blobData = new Blob([resource.blob], { type: mimeType });
          }
        }
        if (blobData) {
          const url = URL.createObjectURL(blobData);
          const a = document.createElement("a");
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          setTimeout(() => URL.revokeObjectURL(url), 1000);
        }
      }
      respondToIframe(iframe, data.id, {});
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
    // Spec: Host MUST NOT switch to a mode not in view's appCapabilities.availableDisplayModes
    if (data.method === "ui/request-display-mode" && data.id != null) {
      const requestedMode = data.params?.mode;
      const viewModes = viewCapabilitiesRef.current?.availableDisplayModes || [];
      const canFullscreen = viewModes.includes("fullscreen");
      const mode = requestedMode === "fullscreen" && canFullscreen ? "fullscreen" : "inline";
      setIsMaximized(mode === "fullscreen");
      respondToIframe(iframe, data.id, { mode });
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
        // host-context-changed with displayMode is sent via the isMaximized useEffect
      }
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [isMaximized]);

  useEffect(() => {
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [handleMessage]);

  // Push updated tool-input when props change and app is ready.
  // Suppress the first fire (when ready becomes true) — already sent by initialized handler.
  useEffect(() => {
    if (!ready) return;
    if (toolInputInitialSentRef.current) {
      toolInputInitialSentRef.current = false;
      return;
    }
    const iframe = iframeRef.current;
    postToIframe(iframe, "ui/notifications/tool-input", {
      arguments: parsedInput,
    });
  }, [ready, _toolInput, _toolName]);

  // Push tool-result when available and app is ready.
  // Suppress the first fire — already sent by initialized handler.
  useEffect(() => {
    if (!ready || parsedResult === null) return;
    if (toolResultInitialSentRef.current) {
      toolResultInitialSentRef.current = false;
      return;
    }
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

  // Push display mode changes via ui/notifications/host-context-changed
  useEffect(() => {
    if (!ready) return;
    const iframe = iframeRef.current;
    postToIframe(iframe, "ui/notifications/host-context-changed", {
      displayMode: isMaximized ? "fullscreen" : "inline",
    });
  }, [ready, isMaximized]);

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

  // sandbox attribute: standard iframe sandbox permissions
  const sandboxAttr = "allow-scripts allow-popups allow-forms allow-downloads allow-same-origin";
  // allow attribute: Permission Policy features for iframe (spec §Host Behavior)
  // These are NOT valid sandbox tokens — they go in the separate `allow` attribute.
  const permAllowParts = [];
  if (resourcePermissions?.camera) permAllowParts.push("camera");
  if (resourcePermissions?.microphone) permAllowParts.push("microphone");
  if (resourcePermissions?.geolocation) permAllowParts.push("geolocation");
  if (resourcePermissions?.clipboardWrite) permAllowParts.push("clipboard-write");
  const allowAttr = permAllowParts.length ? permAllowParts.join("; ") : undefined;

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
        allow={allowAttr}
        referrerPolicy="no-referrer"
        title={`MCP App: ${_toolName}`}
      />
    </div>
  );
}

export default McpAppBridge;
