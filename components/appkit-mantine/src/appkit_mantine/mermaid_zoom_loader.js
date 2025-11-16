import { useEffect } from "react";

export const ZOOMABLE_SELECTORS = [
    'code[data-name="mermaid"] svg',
    '.wmde-markdown svg[id^="mermaid-"]',
    '.markdown svg[id^="mermaid-"]',
    '.wmde-markdown img',
    '.markdown img',
];

export function MermaidZoomLoader() {
    useEffect(() => {
        if (typeof window === "undefined" || typeof document === "undefined") {
            return undefined;
        }

        let activeModal = null;
        let originalBodyOverflow = null;
        let isInitialized = false;

        function markZoomableElements(root = document) {
            ZOOMABLE_SELECTORS.forEach((selector) => {
                const elements = root.querySelectorAll?.(selector) ?? [];
                elements.forEach((element) => {
                    if (!element.hasAttribute("data-mermaid-zoomable")) {
                        element.setAttribute("data-mermaid-zoomable", "true");
                    }
                });
            });
        }

        function openZoom(originalElement) {
            if (activeModal) return;

            const clone = originalElement.cloneNode(true);
            const modal = document.createElement("div");
            modal.setAttribute("data-mermaid-zoom-modal", "opening");
            modal.setAttribute("role", "dialog");
            modal.setAttribute("aria-modal", "true");
            modal.setAttribute("aria-label", "Zoomed diagram");

            const content = document.createElement("div");
            content.setAttribute("data-mermaid-zoom-content", "");
            content.appendChild(clone);
            modal.appendChild(content);

            originalBodyOverflow = document.body.style.overflow;
            document.body.style.overflow = "hidden";

            document.body.appendChild(modal);
            activeModal = modal;

            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    modal.setAttribute("data-mermaid-zoom-modal", "visible");
                });
            });
        }

        function closeZoom() {
            if (!activeModal) return;

            const modal = activeModal;
            modal.setAttribute("data-mermaid-zoom-modal", "closing");
            const duration = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 10 : 300;

            window.setTimeout(() => {
                modal.remove();
                if (originalBodyOverflow !== null) {
                    document.body.style.overflow = originalBodyOverflow;
                    originalBodyOverflow = null;
                }
                activeModal = null;
            }, duration);
        }

        function handleClick(event) {
            const target = event.target;

            let zoomable = target.closest?.('code[data-name="mermaid"] svg');
            if (!zoomable) {
                zoomable = target.closest?.('.wmde-markdown svg[id^="mermaid-"], .markdown svg[id^="mermaid-"]');
            }
            if (!zoomable) {
                zoomable = target.closest?.('svg[id^="mermaid-"]');
            }
            if (!zoomable) {
                zoomable = target.closest?.('.wmde-markdown img, .markdown img');
            }

            if (zoomable && !activeModal) {
                event.preventDefault();
                event.stopPropagation();
                openZoom(zoomable);
            } else if (activeModal && (target === activeModal || target.closest?.('[data-mermaid-zoom-modal]'))) {
                event.preventDefault();
                event.stopPropagation();
                closeZoom();
            }
        }

        function handleKeydown(event) {
            if (event.key === "Escape" && activeModal) {
                event.preventDefault();
                closeZoom();
            }
        }

        function init() {
            if (isInitialized) {
                return;
            }
            isInitialized = true;

            document.addEventListener("click", handleClick, true);
            document.addEventListener("keydown", handleKeydown, true);
            markZoomableElements();

            window.setTimeout(() => {
                const diagrams = document.querySelectorAll(
                    `${ZOOMABLE_SELECTORS[0]}, ${ZOOMABLE_SELECTORS[1]}, ${ZOOMABLE_SELECTORS[2]}`,
                );
                const images = document.querySelectorAll(`${ZOOMABLE_SELECTORS[3]}, ${ZOOMABLE_SELECTORS[4]}`);
                console.log("[Mermaid Zoom] Found diagrams:", diagrams.length, "images:", images.length);
            }, 500);
        }

        function cleanup() {
            document.removeEventListener("click", handleClick, true);
            document.removeEventListener("keydown", handleKeydown, true);
            closeZoom();
        }

        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (mutation.addedNodes.length > 0) {
                    const hasZoomableContent = Array.from(mutation.addedNodes).some((node) => {
                        if (node.nodeType === 1) {
                            return (
                                node.querySelector?.('svg[id^="mermaid-"]') ||
                                node.querySelector?.('code[data-name="mermaid"] svg') ||
                                node.querySelector?.('.wmde-markdown img, .markdown img')
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
                        console.log("[Mermaid Zoom] New zoomable content detected");
                    }
                }
            }
        });

        function startObserver() {
            if (document.body) {
                observer.observe(document.body, { childList: true, subtree: true });
                console.log("[Mermaid Zoom] MutationObserver started");
            } else {
                window.setTimeout(startObserver, 100);
            }
        }

        window._mermaidZoomReinit = function _mermaidZoomReinit() {
            console.log("[Mermaid Zoom] Manual reinit requested");
            markZoomableElements();
            const diagrams = document.querySelectorAll(
                `${ZOOMABLE_SELECTORS[0]}, ${ZOOMABLE_SELECTORS[1]}, ${ZOOMABLE_SELECTORS[2]}`,
            );
            const images = document.querySelectorAll(`${ZOOMABLE_SELECTORS[3]}, ${ZOOMABLE_SELECTORS[4]}`);
            console.log("[Mermaid Zoom] After reinit - Found diagrams:", diagrams.length, "images:", images.length);
        };

        console.log("[Mermaid Zoom] Script loaded successfully");

        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", init, { once: true });
        } else {
            init();
        }

        if (document.readyState !== "complete") {
            window.addEventListener("load", init, { once: true });
        }

        startObserver();

        return () => {
            cleanup();
            observer.disconnect();
            if (window._mermaidZoomReinit === _mermaidZoomReinit) {
                delete window._mermaidZoomReinit;
            }
        };
    }, []);

    return null;
}

export default MermaidZoomLoader;
