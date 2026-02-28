/**
 * McpAppBridge — Host-side React component for MCP Apps.
 *
 * Renders an MCP App in a sandboxed iframe and manages the
 * JSON-RPC postMessage protocol for tool input/result push,
 * tool call proxying, theme sync, and iframe sizing.
 */

import React, { useRef, useEffect, useState, useCallback } from "react";

/** Unique message counter for JSON-RPC IDs */
let _msgId = 0;
const nextId = () => ++_msgId;

/**
 * Post a JSON-RPC message to the iframe.
 */
function postToIframe(iframe, method, params = {}, id = null) {
  if (!iframe || !iframe.contentWindow) return;
  const msg = { jsonrpc: "2.0", method, params };
  if (id !== null) msg.id = id;
  iframe.contentWindow.postMessage(msg, "*");
}

/**
 * Post a JSON-RPC response to the iframe.
 */
function respondToIframe(iframe, id, result) {
  if (!iframe || !iframe.contentWindow) return;
  iframe.contentWindow.postMessage(
    { jsonrpc: "2.0", id, result },
    "*"
  );
}

export function McpAppBridge({
  resource_url = "",
  tool_input = "{}",
  tool_result = "null",
  server_id = 0,
  server_name = "",
  tool_name = "",
  theme = "light",
  max_height = 600,
  prefers_border = true,
  on_tool_call,
  on_message,
  ...rest
}) {
  const iframeRef = useRef(null);
  const [iframeHeight, setIframeHeight] = useState(300);
  const [ready, setReady] = useState(false);

  // Parse JSON props safely
  const parsedInput = React.useMemo(() => {
    try { return JSON.parse(tool_input); }
    catch { return {}; }
  }, [tool_input]);

  const parsedResult = React.useMemo(() => {
    try { return JSON.parse(tool_result); }
    catch { return null; }
  }, [tool_result]);

  // Build CSS variables from theme
  const cssVars = React.useMemo(() => ({
    "--color-background-primary": theme === "dark" ? "#1a1b1e" : "#ffffff",
    "--color-text-primary": theme === "dark" ? "#c1c2c5" : "#000000",
    "--color-border": theme === "dark" ? "#373a40" : "#dee2e6",
  }), [theme]);

  // Handle messages from iframe
  const handleMessage = useCallback((event) => {
    const data = event.data;
    if (!data || data.jsonrpc !== "2.0") return;

    // Only accept messages from our own iframe (sandboxed iframes
    // post with origin "null") or same origin
    if (event.source !== iframeRef.current?.contentWindow) return;

    const iframe = iframeRef.current;

    // ui/initialize request from app
    if (data.method === "ui/initialize" && data.id != null) {
      setReady(true);
      respondToIframe(iframe, data.id, {
        hostContext: {
          displayMode: "inline",
          platform: "web",
          cssVariables: cssVars,
          containerDimensions: {
            maxHeight: max_height,
          },
        },
        capabilities: {
          serverTools: true,
          openLinks: true,
          logging: true,
        },
      });
      // Push initial tool data after handshake
      if (parsedInput && Object.keys(parsedInput).length > 0) {
        postToIframe(iframe, "ui/notifications/tool-input", {
          toolName: tool_name,
          input: parsedInput,
        });
      }
      if (parsedResult) {
        postToIframe(iframe, "ui/notifications/tool-result", {
          toolName: tool_name,
          result: parsedResult,
        });
      }
      return;
    }

    // tools/call request from app
    if (data.method === "tools/call" && data.id != null) {
      const reqId = data.id;
      const params = data.params || {};
      fetch(`/api/mcp-apps/${server_id}/tools/call?user_id=0`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool_name: params.name || params.toolName,
          arguments: params.arguments || {},
        }),
      })
        .then((r) => r.json())
        .then((result) => respondToIframe(iframe, reqId, result))
        .catch(() =>
          respondToIframe(iframe, reqId, { isError: true, content: [] })
        );
      return;
    }

    // ui/open-link from app
    if (data.method === "ui/open-link") {
      const url = data.params?.url;
      if (url && (url.startsWith("https://") || url.startsWith("http://"))) {
        window.open(url, "_blank", "noopener,noreferrer");
      }
      return;
    }

    // ui/notifications/size-changed from app
    if (data.method === "ui/notifications/size-changed") {
      const h = data.params?.height;
      if (typeof h === "number" && h > 0) {
        setIframeHeight(Math.min(h, max_height));
      }
      return;
    }

    // ui/message from app
    if (data.method === "ui/message" && on_message) {
      on_message(JSON.stringify(data.params || {}));
    }
  }, [cssVars, max_height, parsedInput, parsedResult, server_id, tool_name, on_message]);

  useEffect(() => {
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [handleMessage]);

  // Push updated tool data when props change and app is ready
  useEffect(() => {
    if (!ready) return;
    const iframe = iframeRef.current;
    if (parsedInput && Object.keys(parsedInput).length > 0) {
      postToIframe(iframe, "ui/notifications/tool-input", {
        toolName: tool_name,
        input: parsedInput,
      });
    }
  }, [ready, tool_input, tool_name]);

  useEffect(() => {
    if (!ready) return;
    const iframe = iframeRef.current;
    if (parsedResult) {
      postToIframe(iframe, "ui/notifications/tool-result", {
        toolName: tool_name,
        result: parsedResult,
      });
    }
  }, [ready, tool_result, tool_name]);

  // Push theme changes
  useEffect(() => {
    if (!ready) return;
    const iframe = iframeRef.current;
    postToIframe(iframe, "ui/notifications/host-context-changed", {
      cssVariables: cssVars,
    });
  }, [ready, cssVars]);

  if (!resource_url) return null;

  const borderStyle = prefers_border
    ? `1px solid ${theme === "dark" ? "#373a40" : "#dee2e6"}`
    : "none";

  return (
    <div
      style={{
        width: "100%",
        maxWidth: "100%",
        borderRadius: "8px",
        overflow: "hidden",
        border: borderStyle,
        marginTop: "8px",
      }}
    >
      <iframe
        ref={iframeRef}
        src={resource_url}
        style={{
          width: "100%",
          height: `${iframeHeight}px`,
          border: "none",
          display: "block",
        }}
        sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
        title={`MCP App: ${tool_name}`}
      />
    </div>
  );
}

export default McpAppBridge;
