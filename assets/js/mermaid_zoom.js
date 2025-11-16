/**
 * Mermaid SVG Zoom - Click-to-zoom functionality for Mermaid diagrams and images.
 *
 * Provides modal overlay zoom for SVG diagrams rendered by Mermaid and images
 * within markdown-driven content. Mimics behavior of react-medium-image-zoom.
 */

(function () {
    'use strict';

    let activeModal = null;
    let originalBodyOverflow = null;
    let isInitialized = false;

    const ZOOMABLE_SELECTORS = [
        'code[data-name="mermaid"] svg',
        '.wmde-markdown svg[id^="mermaid-"]',
        '.markdown svg[id^="mermaid-"]',
        '.wmde-markdown img',
        '.markdown img',
    ];

    /**
     * Ensure zoomable elements expose cursor styling hooks.
     */
    function markZoomableElements(root = document) {
        ZOOMABLE_SELECTORS.forEach((selector) => {
            const elements = root.querySelectorAll?.(selector) ?? [];
            elements.forEach((element) => {
                if (!element.hasAttribute('data-mermaid-zoomable')) {
                    element.setAttribute('data-mermaid-zoomable', 'true');
                }
            });
        });
    }

    /**
     * Initialize zoom functionality when DOM is ready
     */
    function init() {
        if (isInitialized) {
            console.log('[Mermaid Zoom] Already initialized, skipping...');
            return;
        }

        isInitialized = true;
        console.log('[Mermaid Zoom] Initializing...');

        // Use event delegation for better performance with dynamic content
        document.addEventListener('click', handleClick, true);
        document.addEventListener('keydown', handleKeydown, true);

        markZoomableElements();

        // Log available mermaid diagrams and images
        setTimeout(() => {
            const diagrams = document.querySelectorAll(ZOOMABLE_SELECTORS[0] + ', ' + ZOOMABLE_SELECTORS[1] + ', ' + ZOOMABLE_SELECTORS[2]);
            const images = document.querySelectorAll(ZOOMABLE_SELECTORS[3] + ', ' + ZOOMABLE_SELECTORS[4]);
            console.log('[Mermaid Zoom] Found diagrams:', diagrams.length, 'images:', images.length);
        }, 500);
    }

    /**
     * Handle click events on zoomable elements.
     */
    function handleClick(event) {
        // Use capture phase to ensure we catch events even if stopped elsewhere
        const target = event.target;

        // Check if click is on a Mermaid SVG (or child element of SVG)
        // Try multiple selectors to match different Mermaid rendering structures
        let zoomable = target.closest('code[data-name="mermaid"] svg');

        // Fallback: check if it's an SVG with mermaid ID in markdown container
        if (!zoomable) {
            zoomable = target.closest('.wmde-markdown svg[id^="mermaid-"], .markdown svg[id^="mermaid-"]');
        }

        // Also try without class containers (for raw SVGs)
        if (!zoomable) {
            zoomable = target.closest('svg[id^="mermaid-"]');
        }

        // Finally check for zoomable markdown images
        if (!zoomable) {
            zoomable = target.closest('.wmde-markdown img, .markdown img');
        }

        if (zoomable && !activeModal) {
            // Click on unzoomed element - open zoom
            console.log('[Mermaid Zoom] Opening zoom for:', zoomable.tagName, zoomable.className);
            event.preventDefault();
            event.stopPropagation();
            openZoom(zoomable);
        } else if (activeModal && (target === activeModal || target.closest('[data-mermaid-zoom-modal]'))) {
            // Click on modal or zoomed content - close zoom
            console.log('[Mermaid Zoom] Closing zoom');
            event.preventDefault();
            event.stopPropagation();
            closeZoom();
        }
    }

    /**
     * Handle keyboard events (Escape key closes zoom)
     */
    function handleKeydown(event) {
        if (event.key === 'Escape' && activeModal) {
            event.preventDefault();
            closeZoom();
        }
    }

    /**
     * Open zoom modal with cloned element
     */
    function openZoom(originalElement) {
        if (activeModal) return;

        // Clone the source element (supports SVG and IMG)
        const clone = originalElement.cloneNode(true);

        // Create modal container
        const modal = document.createElement('div');
        modal.setAttribute('data-mermaid-zoom-modal', 'opening');
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('aria-label', 'Zoomed diagram');

        // Create content wrapper
        const content = document.createElement('div');
        content.setAttribute('data-mermaid-zoom-content', '');
        content.appendChild(clone);
        modal.appendChild(content);

        // Lock body scroll
        originalBodyOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';

        // Add to DOM
        document.body.appendChild(modal);
        activeModal = modal;

        // Trigger animation by changing attribute after paint
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                modal.setAttribute('data-mermaid-zoom-modal', 'visible');
            });
        });
    }

    /**
     * Close zoom modal
     */
    function closeZoom() {
        if (!activeModal) return;

        const modal = activeModal;

        // Start closing animation
        modal.setAttribute('data-mermaid-zoom-modal', 'closing');

        // Wait for animation to complete
        const duration = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 10 : 300;

        setTimeout(() => {
            // Remove modal from DOM
            if (modal.parentNode) {
                modal.parentNode.removeChild(modal);
            }

            // Restore body scroll
            if (originalBodyOverflow !== null) {
                document.body.style.overflow = originalBodyOverflow;
                originalBodyOverflow = null;
            }

            activeModal = null;
        }, duration);
    }

    /**
     * Cleanup on page unload
     */
    function cleanup() {
        if (activeModal) {
            closeZoom();
        }
        document.removeEventListener('click', handleClick);
        document.removeEventListener('keydown', handleKeydown);
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOM already loaded, initialize now
        init();
    }

    // Also initialize on window load to catch late-loaded content
    if (document.readyState !== 'complete') {
        window.addEventListener('load', init);
    }

    // Re-initialize when new content is added (for dynamic Mermaid rendering)
    // Use MutationObserver to detect when Mermaid diagrams are added
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            if (mutation.addedNodes.length > 0) {
                const hasZoomableContent = Array.from(mutation.addedNodes).some(node => {
                    if (node.nodeType === 1) {
                        return node.querySelector && (
                            node.querySelector('svg[id^="mermaid-"]') ||
                            node.querySelector('code[data-name="mermaid"] svg') ||
                            node.querySelector('.wmde-markdown img, .markdown img')
                        );
                    }
                    return false;
                });
                if (hasZoomableContent) {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) {
                            markZoomableElements(node);
                        }
                    });
                    console.log('[Mermaid Zoom] New zoomable content detected');
                }
            }
        }
    });

    // Start observing after DOM is ready
    function startObserver() {
        if (document.body) {
            observer.observe(document.body, { childList: true, subtree: true });
            console.log('[Mermaid Zoom] MutationObserver started');
        } else {
            setTimeout(startObserver, 100);
        }
    }

    startObserver();

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        cleanup();
        observer.disconnect();
    });

    // Expose public API for manual re-initialization if needed
    window._mermaidZoomReinit = function () {
        console.log('[Mermaid Zoom] Manual reinit requested');
        markZoomableElements();
        const diagrams = document.querySelectorAll(ZOOMABLE_SELECTORS[0] + ', ' + ZOOMABLE_SELECTORS[1] + ', ' + ZOOMABLE_SELECTORS[2]);
        const images = document.querySelectorAll(ZOOMABLE_SELECTORS[3] + ', ' + ZOOMABLE_SELECTORS[4]);
        console.log('[Mermaid Zoom] After reinit - Found diagrams:', diagrams.length, 'images:', images.length);
    };

    console.log('[Mermaid Zoom] Script loaded successfully');

})();
