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

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

const PROTOCOL_VERSION = "2026-01-26";
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

function parseJsonLike(value, fallback) {
  if (value === null || value === undefined) return fallback;

  if (typeof value === "string") {
    try {
      return JSON.parse(value);
    } catch {
      return fallback;
    }
  }

  return value;
}

function parseHeaderJson(value) {
  if (!value) return null;

  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function createUserHeaders(userId) {
  return userId > 0 ? { "x-user-id": String(userId) } : {};
}

function triggerDownload(parts, filename, mimeType = "application/octet-stream") {
  const blob = new Blob(Array.isArray(parts) ? parts : [parts], {
    type: mimeType,
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");

  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);

  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function decodeBase64Blob(blob) {
  try {
    const binary = atob(blob);
    const bytes = new Uint8Array(binary.length);

    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }

    return [bytes];
  } catch {
    return [blob];
  }
}

function getDownloadFilename(uri) {
  if (!uri) return "download";
  return decodeURIComponent(uri.split("/").pop() || "download");
}

export function McpAppBridge({
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
  useEffect(() => {
    isMaximizedRef.current = isMaximized;
  }, [isMaximized]);
  const viewCapabilitiesRef = useRef({});
  const resourceCspRef = useRef(null);
  const resourcePermissionsRef = useRef(null);
  const toolInputInitialSentRef = useRef(false);
  const toolResultInitialSentRef = useRef(false);
  const [resourcePermissions, setResourcePermissions] = useState(null);
  const [resourcePrefersBorder, setResourcePrefersBorder] = useState(null);

  const resourceUrl = useMemo(() => {
    if (!_resourceUri) return "";
    return `${_backendUrl}/api/mcp-apps/${_serverId}/resource?uri=${encodeURIComponent(_resourceUri)}`;
  }, [_backendUrl, _serverId, _resourceUri]);

  const parsedInput = useMemo(() => parseJsonLike(_toolInput, {}), [_toolInput]);
  const parsedResult = useMemo(() => parseJsonLike(_toolResult, null), [_toolResult]);
  const userHeaders = useMemo(() => createUserHeaders(_userId), [_userId]);
  const jsonHeaders = useMemo(
    () => ({ "Content-Type": "application/json", ...userHeaders }),
    [userHeaders]
  );

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

  useEffect(() => {
    if (!resourceUrl) return;
    const controller = new AbortController();

    resourceCspRef.current = null;
    resourcePermissionsRef.current = null;
    setFetchError("");
    setHtmlContent("");
    setResourcePermissions(null);
    setResourcePrefersBorder(null);

    const loadResource = async () => {
      try {
        const response = await fetch(resourceUrl, {
          credentials: "omit",
          headers: {
            "ngrok-skip-browser-warning": "true",
            ...userHeaders,
          },
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const parsedCsp = parseHeaderJson(response.headers.get("X-MCP-CSP"));
        const parsedPermissions = parseHeaderJson(
          response.headers.get("X-MCP-Permissions")
        );
        const prefersBorderHeader = response.headers.get("X-MCP-Prefers-Border");

        resourceCspRef.current = parsedCsp;
        resourcePermissionsRef.current = parsedPermissions;
        setResourcePermissions(parsedPermissions);
        setResourcePrefersBorder(
          prefersBorderHeader === null ? null : prefersBorderHeader === "true"
        );

        let html = normalizeSrcDocHtml(await response.text());

        // Inject CSP as FIRST element in <head> only when server provided metadata (spec §4).
        // When parsedCsp is null we skip injection and rely on the iframe sandbox attribute.
        html = injectIntoHead(html, buildCspMetaTag(parsedCsp));

        if (html.includes("</body>")) {
          html = html.replace("</body>", AUTO_SIZE_SCRIPT + "</body>");
        } else if (html.includes("</html>")) {
          html = html.replace("</html>", AUTO_SIZE_SCRIPT + "</html>");
        } else {
          html += AUTO_SIZE_SCRIPT;
        }

        setHtmlContent(html);
      } catch (err) {
        if (controller.signal.aborted) return;
        console.error("Failed to fetch MCP App resource:", err);
        setFetchError(err instanceof Error ? err.message : String(err));
        setHtmlContent("");
      }
    };

    void loadResource();

    return () => controller.abort();
  }, [resourceUrl, userHeaders]);

  const handleMessage = useCallback((event) => {
    const data = event.data;
    if (!data || data.jsonrpc !== "2.0") return;
    if (event.source !== iframeRef.current?.contentWindow) return;

    const iframe = iframeRef.current;
    switch (data.method) {
      case "ui/initialize": {
        if (data.id == null) return;

        viewCapabilitiesRef.current = data.params?.appCapabilities || {};

        const csp = resourceCspRef.current;
        const permissions = resourcePermissionsRef.current;
        const sandboxPermissions = permissions
          ? {
              ...(permissions.camera ? { camera: {} } : {}),
              ...(permissions.microphone ? { microphone: {} } : {}),
              ...(permissions.geolocation ? { geolocation: {} } : {}),
              ...(permissions.clipboardWrite ? { clipboardWrite: {} } : {}),
            }
          : undefined;

        respondToIframe(iframe, data.id, {
          protocolVersion: PROTOCOL_VERSION,
          hostInfo: { name: "appkit", version: "1.0.0" },
          hostCapabilities: {
            openLinks: {},
            serverTools: { listChanged: false },
            serverResources: { listChanged: false },
            logging: {},
            sandbox: {
              ...(sandboxPermissions ? { permissions: sandboxPermissions } : {}),
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
            ...(_toolName
              ? {
                  toolInfo: {
                    tool: {
                      name: _toolName,
                      description: "",
                      inputSchema: { type: "object" },
                    },
                  },
                }
              : {}),
            displayMode: "inline",
            availableDisplayModes: ["inline", "fullscreen"],
            platform: "web",
            containerDimensions: { maxHeight: _maxHeight },
            styles: { variables: cssVars },
          },
        });
        return;
      }

      case "ui/notifications/initialized": {
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

      case "ping": {
        if (data.id != null) {
          respondToIframe(iframe, data.id, {});
        }
        return;
      }

      case "tools/call": {
        if (data.id == null) return;

        const requestId = data.id;
        const params = data.params || {};

        fetch(`${_backendUrl}/api/mcp-apps/${_serverId}/tools/call`, {
          method: "POST",
          headers: jsonHeaders,
          credentials: "omit",
          body: JSON.stringify({
            tool_name: params.name,
            arguments: params.arguments || {},
          }),
        })
          .then((response) =>
            response.ok ? response.json() : Promise.reject(response.status)
          )
          .then((result) => respondToIframe(iframe, requestId, result))
          .catch(() => {
            respondErrorToIframe(iframe, requestId, -32000, "Tool call failed");
          });
        return;
      }

      case "resources/read": {
        if (data.id == null) return;

        const requestId = data.id;
        const uri = data.params?.uri;

        if (!uri) {
          respondErrorToIframe(iframe, requestId, -32602, "Missing uri parameter");
          return;
        }

        fetch(
          `${_backendUrl}/api/mcp-apps/${_serverId}/resource?uri=${encodeURIComponent(uri)}`,
          {
            credentials: "omit",
            headers: userHeaders,
          }
        )
          .then((response) =>
            response.ok ? response.text() : Promise.reject(response.status)
          )
          .then((html) => {
            respondToIframe(iframe, requestId, {
              contents: [
                { uri, mimeType: "text/html;profile=mcp-app", text: html },
              ],
            });
          })
          .catch(() => {
            respondErrorToIframe(iframe, requestId, -32002, "Resource not found");
          });
        return;
      }

      case "ui/open-link": {
        const url = data.params?.url;

        if (url && (url.startsWith("https://") || url.startsWith("http://"))) {
          window.open(url, "_blank", "noopener,noreferrer");
          if (data.id != null) {
            respondToIframe(iframe, data.id, {});
          }
        } else if (data.id != null) {
          respondErrorToIframe(iframe, data.id, -32000, "Invalid URL");
        }
        return;
      }

      case "ui/notifications/download": {
        const { filename, content, mimeType } = data.params || {};

        if (filename && content) {
          triggerDownload(content, filename, mimeType);
        }
        return;
      }

      case "ui/download-file": {
        if (data.id == null) return;

        const resource = (data.params?.contents || [])[0]?.resource;

        if (resource) {
          const mimeType = resource.mimeType || "application/octet-stream";
          const filename = getDownloadFilename(resource.uri);

          if (resource.text !== undefined) {
            triggerDownload(resource.text, filename, mimeType);
          } else if (resource.blob !== undefined) {
            triggerDownload(decodeBase64Blob(resource.blob), filename, mimeType);
          }
        }

        respondToIframe(iframe, data.id, {});
        return;
      }

      case "ui/notifications/size-changed": {
        if (isMaximizedRef.current) return;

        const height = data.params?.height;
        const width = data.params?.width;

        if (typeof height === "number" && height > 0) {
          setIframeHeight(Math.min(height, _maxHeight));
        }
        if (typeof width === "number" && width > 0) {
          setIframeWidth(width);
        }
        return;
      }

      case "ui/notifications/maximize": {
        const maximize = data.params?.maximized;
        setIsMaximized(
          typeof maximize === "boolean" ? maximize : (prev) => !prev
        );
        return;
      }

      case "ui/message": {
        if (data.id != null) {
          respondToIframe(iframe, data.id, { isError: false });
        }
        if (_onMessage) {
          _onMessage(JSON.stringify(data.params || {}));
        }
        return;
      }

      case "ui/request-display-mode": {
        if (data.id == null) return;

        const requestedMode = data.params?.mode;
        const viewModes = viewCapabilitiesRef.current?.availableDisplayModes || [];
        const mode =
          requestedMode === "fullscreen" && viewModes.includes("fullscreen")
            ? "fullscreen"
            : "inline";

        setIsMaximized(mode === "fullscreen");
        respondToIframe(iframe, data.id, { mode });
        return;
      }

      case "ui/update-model-context": {
        if (data.id != null) {
          respondToIframe(iframe, data.id, {});
        }
        return;
      }

      case "notifications/message": {
        const level = data.params?.level ?? "info";
        const logger = data.params?.logger ?? "mcp-app";
        const message = data.params?.data ?? "";
        const consoleMethod =
          level === "error" ? "error" : level === "warning" ? "warn" : "log";

        console[consoleMethod](`[MCP App][${logger}]`, message);
        return;
      }

      default:
        return;
    }
  }, [
    _backendUrl,
    _maxHeight,
    _onMessage,
    _serverId,
    _toolName,
    cssVars,
    jsonHeaders,
    parsedInput,
    parsedResult,
    theme,
    userHeaders,
  ]);

  useEffect(() => {
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [handleMessage]);

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
  }, [parsedInput, ready]);

  useEffect(() => {
    if (!ready || parsedResult === null) return;
    if (toolResultInitialSentRef.current) {
      toolResultInitialSentRef.current = false;
      return;
    }
    const iframe = iframeRef.current;
    postToIframe(iframe, "ui/notifications/tool-result", parsedResult);
  }, [parsedResult, ready]);

  useEffect(() => {
    if (!ready) return;
    const iframe = iframeRef.current;
    postToIframe(iframe, "ui/notifications/host-context-changed", {
      theme,
      styles: { variables: cssVars },
    });
  }, [ready, theme, cssVars]);

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

  const sandboxAttr = "allow-scripts allow-popups allow-forms allow-downloads allow-same-origin";
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
