/**
 * MCP OAuth message handler
 * Listens for postMessage events from OAuth popup windows
 * and triggers Reflex events to resume the assistant flow.
 */

(function() {
    'use strict';

    window.addEventListener('message', function(event) {
        // Verify the message is from our OAuth flow
        if (event.data && event.data.type === 'mcp-oauth-success') {
            console.log('MCP OAuth success received:', event.data);

            // Dispatch a custom event that Reflex can listen to
            const customEvent = new CustomEvent('mcp-oauth-complete', {
                detail: {
                    serverId: event.data.serverId,
                    serverName: event.data.serverName
                }
            });
            window.dispatchEvent(customEvent);

            // Trigger Reflex state update via backend call
            // This uses Reflex's internal event system
            if (window.__REFLEX && window.__REFLEX.call) {
                window.__REFLEX.call('thread_state.handle_mcp_oauth_success', {
                    server_id: event.data.serverId,
                    server_name: event.data.serverName
                });
            }
        }
    }, false);
})();
