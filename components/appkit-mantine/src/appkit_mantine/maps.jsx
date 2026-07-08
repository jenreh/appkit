import MapLibreGL from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  createContext,
  forwardRef,
  useCallback,
  useContext,
  useEffect,
  useId,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";

// ---------------------------------------------------------------------------
// Ported from https://mapcn.dev (src/registry/map.tsx) for Reflex.
//
// Differences from the upstream shadcn/Tailwind source:
// - Stripped TypeScript types/generics (this is a plain .jsx asset).
// - Tailwind utility classes replaced with a small injected stylesheet
//   (`akm-*` class names) since consuming apps may not have Tailwind.
// - lucide-react icons replaced with tiny inline SVGs to avoid an extra
//   npm dependency.
// ---------------------------------------------------------------------------

function cn(...parts) {
  return parts.filter(Boolean).join(" ");
}

let stylesInjected = false;
function injectStyles() {
  if (stylesInjected || typeof document === "undefined") return;
  stylesInjected = true;
  const style = document.createElement("style");
  style.setAttribute("data-akm-map-styles", "true");
  style.textContent = `
    /* Strip MapLibre GL's own default popup chrome (background, shadow,
       padding, and the triangular tip) so our own .akm-popup / .akm-tooltip
       elements supply all visual styling instead of nesting inside it. */
    .maplibregl-popup-content {
      background: transparent !important;
      box-shadow: none !important;
      padding: 0 !important;
      border-radius: 0 !important;
    }
    .maplibregl-popup-tip { display: none !important; }

    .akm-map-container { position: relative; height: 100%; width: 100%; }
    .akm-map-loader {
      position: absolute; inset: 0; z-index: 10; display: flex;
      align-items: center; justify-content: center;
      background: rgba(255, 255, 255, 0.5); backdrop-filter: blur(2px);
    }
    .akm-map-loader-dots { display: flex; gap: 4px; }
    .akm-map-loader-dot {
      width: 6px; height: 6px; border-radius: 9999px;
      background: rgba(100, 100, 100, 0.6);
      animation: akm-pulse 1s ease-in-out infinite;
    }
    .akm-map-loader-dot:nth-child(2) { animation-delay: 150ms; }
    .akm-map-loader-dot:nth-child(3) { animation-delay: 300ms; }
    @keyframes akm-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

    .akm-marker-dot {
      width: 16px; height: 16px; border-radius: 50%;
      border: 2px solid #fff; background: #3b82f6;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
    }
    .akm-marker-content { position: relative; cursor: pointer; }

    .akm-popup {
      background: #fff; color: #111; position: relative;
      min-width: 140px; max-width: 280px; box-sizing: border-box;
      border-radius: 6px; border: 1px solid #e5e5e5; padding: 12px;
      font-size: 13px; line-height: 1.4;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      animation: akm-fade-in 0.15s ease-out;
    }
    .akm-popup-with-close { padding-right: 28px; }
    .akm-tooltip {
      background: #171717; color: #fff; padding: 4px 8px; border-radius: 6px;
      font-size: 12px; white-space: nowrap; pointer-events: none;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
      animation: akm-fade-in 0.15s ease-out;
    }
    @keyframes akm-fade-in {
      from { opacity: 0; transform: scale(0.95); }
      to { opacity: 1; transform: scale(1); }
    }
    .akm-popup-close {
      position: absolute; top: 4px; right: 4px; z-index: 10;
      display: inline-flex; align-items: center; justify-content: center;
      width: 20px; height: 20px; border-radius: 4px; background: transparent;
      border: none; cursor: pointer; color: inherit;
    }
    .akm-popup-close:hover { background: rgba(0, 0, 0, 0.06); }

    .akm-marker-label {
      position: absolute; left: 50%; transform: translateX(-50%);
      white-space: nowrap; font-size: 10px; font-weight: 500; color: #171717;
    }
    .akm-marker-label-top { bottom: 100%; margin-bottom: 4px; }
    .akm-marker-label-bottom { top: 100%; margin-top: 4px; }

    .akm-controls { position: absolute; z-index: 10; display: flex; flex-direction: column; gap: 6px; }
    .akm-controls-top-left { top: 8px; left: 8px; }
    .akm-controls-top-right { top: 8px; right: 8px; }
    .akm-controls-bottom-left { bottom: 8px; left: 8px; }
    .akm-controls-bottom-right { bottom: 40px; right: 8px; }

    .akm-control-group {
      display: flex; flex-direction: column; overflow: hidden;
      border-radius: 6px; border: 1px solid #e5e5e5; background: #fff;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
    }
    .akm-control-group > button:not(:last-child) { border-bottom: 1px solid #e5e5e5; }
    .akm-control-button {
      display: flex; align-items: center; justify-content: center;
      width: 32px; height: 32px; background: transparent; border: none;
      cursor: pointer; color: #171717; transition: background-color 0.15s ease;
    }
    .akm-control-button:hover { background: rgba(0, 0, 0, 0.05); }
    .akm-control-button:disabled { opacity: 0.5; cursor: not-allowed; }
    .akm-spin { animation: akm-spin 1s linear infinite; }
    @keyframes akm-spin { to { transform: rotate(360deg); } }

    .akm-directions-panel {
      position: absolute; z-index: 10; background: #fff; color: #171717;
      border-radius: 8px; border: 1px solid #e5e5e5; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
      font-size: 13px; overflow: hidden;
    }
    .akm-directions-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 12px; font-weight: 600; user-select: none;
    }
    .akm-directions-title { font-size: 14px; }
    .akm-directions-chevron { transition: transform 0.15s ease; font-size: 11px; opacity: 0.6; }
    .akm-directions-chevron-collapsed { transform: rotate(180deg); }
    .akm-directions-body { padding: 0 12px 12px; overflow-y: auto; }
    .akm-directions-loading, .akm-directions-empty { color: #737373; padding: 4px 0; }
    .akm-directions-error { color: #dc2626; padding: 4px 0; }
    .akm-directions-profiles { display: flex; gap: 6px; margin-bottom: 8px; }
    .akm-directions-profile-btn {
      flex: 1; padding: 5px 8px; border-radius: 6px; border: 1px solid #e5e5e5;
      background: #fafafa; color: #171717; cursor: pointer; font-size: 12px;
      text-transform: capitalize;
    }
    .akm-directions-profile-btn-active { background: #171717; color: #fff; border-color: #171717; }
    .akm-directions-alternatives { display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }
    .akm-directions-alt-btn {
      padding: 6px 8px; border-radius: 6px; border: 1px solid #e5e5e5;
      background: #fafafa; color: #171717; cursor: pointer; font-size: 12px; text-align: left;
    }
    .akm-directions-alt-btn-active { background: #eef2ff; border-color: #6366f1; color: #4338ca; }
    .akm-directions-summary {
      display: flex; gap: 10px; align-items: baseline; margin-bottom: 8px;
      font-weight: 600; font-size: 15px;
    }
    .akm-directions-summary-distance { font-weight: 400; font-size: 13px; color: #737373; }
    .akm-directions-steps { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
    .akm-directions-step { display: flex; gap: 8px; align-items: flex-start; }
    .akm-directions-step-index {
      flex-shrink: 0; width: 18px; height: 18px; border-radius: 50%;
      background: #171717; color: #fff; font-size: 10px; font-weight: 600;
      display: flex; align-items: center; justify-content: center; margin-top: 1px;
    }
    .akm-directions-step-text { line-height: 1.4; }
  `;
  document.head.appendChild(style);
}

const defaultStyles = {
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  light: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
};

// A tile-less, dependency-free style with a transparent background. Use it
// for data visualizations (choropleths, world arcs, dot maps) where you draw
// your own layers and don't need a street basemap.
const blankMapStyle = {
  version: 8,
  sources: {},
  layers: [
    {
      id: "background",
      type: "background",
      paint: { "background-color": "rgba(0, 0, 0, 0)" },
    },
  ],
};

function mergeHoverPaint(paint, hoverPaint) {
  if (!hoverPaint) return paint;
  const merged = { ...paint };
  for (const [key, hoverValue] of Object.entries(hoverPaint)) {
    if (hoverValue === undefined) continue;
    const baseValue = merged[key];
    merged[key] =
      baseValue === undefined
        ? hoverValue
        : ["case", ["boolean", ["feature-state", "hover"], false], hoverValue, baseValue];
  }
  return merged;
}

// Check document class for theme (works with next-themes-style toggles).
function getDocumentTheme() {
  if (typeof document === "undefined") return null;
  if (document.documentElement.classList.contains("dark")) return "dark";
  if (document.documentElement.classList.contains("light")) return "light";
  return null;
}

function getSystemTheme() {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function useResolvedTheme(themeProp) {
  const [detectedTheme, setDetectedTheme] = useState(
    () => getDocumentTheme() ?? getSystemTheme(),
  );

  useEffect(() => {
    if (themeProp) return;

    const observer = new MutationObserver(() => {
      const docTheme = getDocumentTheme();
      if (docTheme) {
        setDetectedTheme(docTheme);
      }
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleSystemChange = (e) => {
      if (!getDocumentTheme()) {
        setDetectedTheme(e.matches ? "dark" : "light");
      }
    };
    mediaQuery.addEventListener("change", handleSystemChange);

    return () => {
      observer.disconnect();
      mediaQuery.removeEventListener("change", handleSystemChange);
    };
  }, [themeProp]);

  return themeProp ?? detectedTheme;
}

const MapContext = createContext(null);

function useMap() {
  const context = useContext(MapContext);
  if (!context) {
    throw new Error("useMap must be used within a Map component");
  }
  return context;
}

function DefaultLoader() {
  return (
    <div className="akm-map-loader">
      <div className="akm-map-loader-dots">
        <span className="akm-map-loader-dot" />
        <span className="akm-map-loader-dot" />
        <span className="akm-map-loader-dot" />
      </div>
    </div>
  );
}

function getViewport(map) {
  const center = map.getCenter();
  return {
    center: [center.lng, center.lat],
    zoom: map.getZoom(),
    bearing: map.getBearing(),
    pitch: map.getPitch(),
  };
}

/** Root map container. Initializes MapLibre GL and provides context to children. */
const Map = forwardRef(function Map(
  {
    children,
    className,
    theme: themeProp,
    styles,
    blank = false,
    projection,
    viewport,
    onViewportChange,
    loading = false,
    center,
    zoom,
    ...props
  },
  ref,
) {
  injectStyles();

  const containerRef = useRef(null);
  const [mapInstance, setMapInstance] = useState(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [isStyleLoaded, setIsStyleLoaded] = useState(false);
  const currentStyleRef = useRef(null);
  const styleTimeoutRef = useRef(null);
  const internalUpdateRef = useRef(false);
  const resolvedTheme = useResolvedTheme(themeProp);

  const isControlled = viewport !== undefined && onViewportChange !== undefined;

  const onViewportChangeRef = useRef(onViewportChange);
  onViewportChangeRef.current = onViewportChange;

  const mapStyles = useMemo(() => {
    if (styles) {
      return {
        dark: styles.dark ?? defaultStyles.dark,
        light: styles.light ?? defaultStyles.light,
      };
    }
    if (blank) {
      return { dark: blankMapStyle, light: blankMapStyle };
    }
    return defaultStyles;
  }, [styles, blank]);

  useImperativeHandle(ref, () => mapInstance, [mapInstance]);

  const clearStyleTimeout = useCallback(() => {
    if (styleTimeoutRef.current) {
      clearTimeout(styleTimeoutRef.current);
      styleTimeoutRef.current = null;
    }
  }, []);

  // Initialize the map.
  useEffect(() => {
    if (!containerRef.current) return;

    const initialStyle = resolvedTheme === "dark" ? mapStyles.dark : mapStyles.light;
    currentStyleRef.current = initialStyle;

    const initialCenter = center ?? viewport?.center;
    const initialZoom = zoom ?? viewport?.zoom;

    const map = new MapLibreGL.Map({
      container: containerRef.current,
      style: initialStyle,
      renderWorldCopies: false,
      attributionControl: { compact: true },
      ...props,
      ...(initialCenter ? { center: initialCenter } : {}),
      ...(initialZoom !== undefined ? { zoom: initialZoom } : {}),
      ...viewport,
    });

    const styleDataHandler = () => {
      clearStyleTimeout();
      styleTimeoutRef.current = setTimeout(() => {
        setIsStyleLoaded(true);
        if (projection) {
          map.setProjection(projection);
        }
      }, 100);
    };
    const loadHandler = () => setIsLoaded(true);

    const handleMove = () => {
      if (internalUpdateRef.current) return;
      onViewportChangeRef.current?.(getViewport(map));
    };

    map.on("load", loadHandler);
    map.on("styledata", styleDataHandler);
    map.on("move", handleMove);
    setMapInstance(map);

    return () => {
      clearStyleTimeout();
      map.off("load", loadHandler);
      map.off("styledata", styleDataHandler);
      map.off("move", handleMove);
      map.remove();
      setIsLoaded(false);
      setIsStyleLoaded(false);
      setMapInstance(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep MapLibre's internal transform (width/height) in sync with the
  // container's actual on-screen size. `new MapLibreGL.Map({container})`
  // reads the container's size synchronously at construction time — if the
  // container is still 0x0 then (e.g. it hasn't been laid out yet, is
  // inside a flex/grid box, or a parent tab/collapse is still animating),
  // the map's transform stays zero-sized until something calls
  // `map.resize()`. A zero-sized transform makes pixel<->LngLat conversions
  // (used by `fitBounds`/`cameraForBounds`) divide by zero, which throws
  // "Invalid LngLat object: (NaN, NaN)" even though the bounds themselves
  // are perfectly valid coordinates.
  useEffect(() => {
    if (!mapInstance || !containerRef.current) return;
    const observer = new ResizeObserver(() => mapInstance.resize());
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [mapInstance]);

  // Sync controlled viewport to map.
  useEffect(() => {
    if (!mapInstance || !isControlled || !viewport) return;
    if (mapInstance.isMoving()) return;

    const current = getViewport(mapInstance);
    const next = {
      center: viewport.center ?? current.center,
      zoom: viewport.zoom ?? current.zoom,
      bearing: viewport.bearing ?? current.bearing,
      pitch: viewport.pitch ?? current.pitch,
    };

    if (
      next.center[0] === current.center[0] &&
      next.center[1] === current.center[1] &&
      next.zoom === current.zoom &&
      next.bearing === current.bearing &&
      next.pitch === current.pitch
    ) {
      return;
    }

    internalUpdateRef.current = true;
    mapInstance.jumpTo(next);
    internalUpdateRef.current = false;
  }, [mapInstance, isControlled, viewport]);

  // Sync uncontrolled center/zoom props (no onViewportChange handler).
  useEffect(() => {
    if (!mapInstance || isControlled || internalUpdateRef.current) return;
    if (center === undefined && zoom === undefined) return;
    if (mapInstance.isMoving()) return;

    const current = getViewport(mapInstance);
    const nextCenter = center ?? current.center;
    const nextZoom = zoom ?? current.zoom;
    if (
      nextCenter[0] === current.center[0] &&
      nextCenter[1] === current.center[1] &&
      nextZoom === current.zoom
    ) {
      return;
    }
    mapInstance.jumpTo({ center: nextCenter, zoom: nextZoom });
  }, [mapInstance, isControlled, center, zoom]);

  // Handle style change.
  useEffect(() => {
    if (!mapInstance || !resolvedTheme) return;

    const newStyle = resolvedTheme === "dark" ? mapStyles.dark : mapStyles.light;

    if (currentStyleRef.current === newStyle) return;

    clearStyleTimeout();
    currentStyleRef.current = newStyle;
    setIsStyleLoaded(false);

    mapInstance.setStyle(newStyle, { diff: true });
  }, [mapInstance, resolvedTheme, mapStyles, clearStyleTimeout]);

  // Sync projection when the prop changes after mount.
  useEffect(() => {
    if (!mapInstance || !isStyleLoaded || !projection) return;
    mapInstance.setProjection(projection);
  }, [mapInstance, isStyleLoaded, projection]);

  const [navigation, setNavigation] = useState(null);

  const contextValue = useMemo(
    () => ({
      map: mapInstance,
      isLoaded: isLoaded && isStyleLoaded,
      resolvedTheme,
      navigation,
      setNavigation,
    }),
    [mapInstance, isLoaded, isStyleLoaded, resolvedTheme, navigation],
  );

  return (
    <MapContext.Provider value={contextValue}>
      <div ref={containerRef} className={cn("akm-map-container", className)}>
        {(!isLoaded || loading) && <DefaultLoader />}
        {mapInstance && children}
      </div>
    </MapContext.Provider>
  );
});

const MarkerContext = createContext(null);

function useMarkerContext() {
  const context = useContext(MarkerContext);
  if (!context) {
    throw new Error("Marker components must be used within MapMarker");
  }
  return context;
}

/** A container for marker-related components (positioning + drag/click events). */
function MapMarker({
  longitude,
  latitude,
  children,
  onClick,
  onMouseEnter,
  onMouseLeave,
  onDragStart,
  onDrag,
  onDragEnd,
  draggable = false,
  ...markerOptions
}) {
  const { map } = useMap();

  const callbacksRef = useRef({
    onClick,
    onMouseEnter,
    onMouseLeave,
    onDragStart,
    onDrag,
    onDragEnd,
  });
  callbacksRef.current = {
    onClick,
    onMouseEnter,
    onMouseLeave,
    onDragStart,
    onDrag,
    onDragEnd,
  };

  const marker = useMemo(() => {
    const markerInstance = new MapLibreGL.Marker({
      ...markerOptions,
      element: document.createElement("div"),
      draggable,
    }).setLngLat([longitude, latitude]);

    const handleClick = (e) => callbacksRef.current.onClick?.(e);
    const handleMouseEnter = (e) => callbacksRef.current.onMouseEnter?.(e);
    const handleMouseLeave = (e) => callbacksRef.current.onMouseLeave?.(e);

    markerInstance.getElement()?.addEventListener("click", handleClick);
    markerInstance.getElement()?.addEventListener("mouseenter", handleMouseEnter);
    markerInstance.getElement()?.addEventListener("mouseleave", handleMouseLeave);

    const handleDragStart = () => {
      const lngLat = markerInstance.getLngLat();
      callbacksRef.current.onDragStart?.({ lng: lngLat.lng, lat: lngLat.lat });
    };
    const handleDrag = () => {
      const lngLat = markerInstance.getLngLat();
      callbacksRef.current.onDrag?.({ lng: lngLat.lng, lat: lngLat.lat });
    };
    const handleDragEnd = () => {
      const lngLat = markerInstance.getLngLat();
      callbacksRef.current.onDragEnd?.({ lng: lngLat.lng, lat: lngLat.lat });
    };

    markerInstance.on("dragstart", handleDragStart);
    markerInstance.on("drag", handleDrag);
    markerInstance.on("dragend", handleDragEnd);

    return markerInstance;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!map) return;

    marker.addTo(map);

    return () => {
      marker.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]);

  const { offset, rotation, rotationAlignment, pitchAlignment } = markerOptions;

  useEffect(() => {
    const current = marker.getLngLat();
    if (current.lng !== longitude || current.lat !== latitude) {
      marker.setLngLat([longitude, latitude]);
    }

    if (marker.isDraggable() !== draggable) {
      marker.setDraggable(draggable);
    }

    const currentOffset = marker.getOffset();
    const newOffset = offset ?? [0, 0];
    const [newOffsetX, newOffsetY] = Array.isArray(newOffset)
      ? newOffset
      : [newOffset.x, newOffset.y];
    if (currentOffset.x !== newOffsetX || currentOffset.y !== newOffsetY) {
      marker.setOffset(newOffset);
    }

    if (marker.getRotation() !== (rotation ?? 0)) {
      marker.setRotation(rotation ?? 0);
    }
    if (marker.getRotationAlignment() !== (rotationAlignment ?? "auto")) {
      marker.setRotationAlignment(rotationAlignment ?? "auto");
    }
    if (marker.getPitchAlignment() !== (pitchAlignment ?? "auto")) {
      marker.setPitchAlignment(pitchAlignment ?? "auto");
    }
  }, [marker, longitude, latitude, draggable, offset, rotation, rotationAlignment, pitchAlignment]);

  return <MarkerContext.Provider value={{ marker, map }}>{children}</MarkerContext.Provider>;
}

function DefaultMarkerIcon() {
  return <div className="akm-marker-dot" />;
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
    </svg>
  );
}

function PopupCloseButton({ onClick }) {
  return (
    <button type="button" onClick={onClick} aria-label="Close popup" className="akm-popup-close">
      <CloseIcon />
    </button>
  );
}

/** Renders the visual content of a marker. Defaults to a blue dot if no children given. */
function MarkerContent({ children, className }) {
  const { marker } = useMarkerContext();

  return createPortal(
    <div className={cn("akm-marker-content", className)}>{children || <DefaultMarkerIcon />}</div>,
    marker.getElement(),
  );
}

/** Popup attached to a marker, opens on click. */
function MarkerPopup({ children, className, closeButton = false, ...popupOptions }) {
  const { marker, map } = useMarkerContext();
  const container = useMemo(() => document.createElement("div"), []);
  const { offset, maxWidth } = popupOptions;

  const popup = useMemo(() => {
    const popupInstance = new MapLibreGL.Popup({ offset: 16, ...popupOptions, closeButton: false })
      .setMaxWidth("none")
      .setDOMContent(container);

    return popupInstance;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!map) return;

    popup.setDOMContent(container);
    marker.setPopup(popup);

    return () => {
      marker.setPopup(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]);

  useEffect(() => {
    popup.setOffset(offset ?? 16);
    if (maxWidth) {
      popup.setMaxWidth(maxWidth);
    }
  }, [popup, offset, maxWidth]);

  const handleClose = () => popup.remove();

  return createPortal(
    <div className={cn("akm-popup", closeButton && "akm-popup-with-close", className)}>
      {closeButton && <PopupCloseButton onClick={handleClose} />}
      {children}
    </div>,
    container,
  );
}

/** Tooltip that appears on hover over a marker. */
function MarkerTooltip({ children, className, ...popupOptions }) {
  const { marker, map } = useMarkerContext();
  const container = useMemo(() => document.createElement("div"), []);
  const { offset, maxWidth } = popupOptions;

  const tooltip = useMemo(() => {
    const tooltipInstance = new MapLibreGL.Popup({
      offset: 16,
      ...popupOptions,
      closeOnClick: true,
      closeButton: false,
    }).setMaxWidth("none");

    return tooltipInstance;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!map) return;

    tooltip.setDOMContent(container);

    const handleMouseEnter = () => {
      tooltip.setLngLat(marker.getLngLat()).addTo(map);
    };
    const handleMouseLeave = () => tooltip.remove();

    marker.getElement()?.addEventListener("mouseenter", handleMouseEnter);
    marker.getElement()?.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      marker.getElement()?.removeEventListener("mouseenter", handleMouseEnter);
      marker.getElement()?.removeEventListener("mouseleave", handleMouseLeave);
      tooltip.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]);

  useEffect(() => {
    tooltip.setOffset(offset ?? 16);
    if (maxWidth) {
      tooltip.setMaxWidth(maxWidth);
    }
  }, [tooltip, offset, maxWidth]);

  return createPortal(<div className={cn("akm-tooltip", className)}>{children}</div>, container);
}

/** Text label above or below a marker. Must be used inside MarkerContent. */
function MarkerLabel({ children, className, position = "top" }) {
  const positionClass = position === "bottom" ? "akm-marker-label-bottom" : "akm-marker-label-top";

  return <div className={cn("akm-marker-label", positionClass, className)}>{children}</div>;
}

const positionClasses = {
  "top-left": "akm-controls-top-left",
  "top-right": "akm-controls-top-right",
  "bottom-left": "akm-controls-bottom-left",
  "bottom-right": "akm-controls-bottom-right",
};

function ControlGroup({ children }) {
  return <div className="akm-control-group">{children}</div>;
}

function ControlButton({ onClick, label, children, disabled = false }) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      type="button"
      className="akm-control-button"
      disabled={disabled}
    >
      {children}
    </button>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function MinusIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function LocateIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3" strokeLinecap="round" />
    </svg>
  );
}

function MaximizeIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
      <path
        d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M21 16v3a2 2 0 0 1-2 2h-3M3 16v3a2 2 0 0 0 2 2h3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function LoaderIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" className="akm-spin">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round" />
    </svg>
  );
}

function CompassButton({ onClick }) {
  const { map } = useMap();
  const compassRef = useRef(null);

  useEffect(() => {
    if (!map || !compassRef.current) return;

    const compass = compassRef.current;

    const updateRotation = () => {
      const bearing = map.getBearing();
      const pitch = map.getPitch();
      compass.style.transform = `rotateX(${pitch}deg) rotateZ(${-bearing}deg)`;
    };

    map.on("rotate", updateRotation);
    map.on("pitch", updateRotation);
    updateRotation();

    return () => {
      map.off("rotate", updateRotation);
      map.off("pitch", updateRotation);
    };
  }, [map]);

  return (
    <ControlButton onClick={onClick} label="Reset bearing to north">
      <svg
        ref={compassRef}
        viewBox="0 0 24 24"
        width="18"
        height="18"
        style={{ transformStyle: "preserve-3d", transition: "transform 0.2s" }}
      >
        <path d="M12 2L16 12H12V2Z" fill="#ef4444" />
        <path d="M12 2L8 12H12V2Z" fill="#fca5a5" />
        <path d="M12 22L16 12H12V22Z" fill="#737373" />
        <path d="M12 22L8 12H12V22Z" fill="#a3a3a3" />
      </svg>
    </ControlButton>
  );
}

/** Zoom, compass, locate, and fullscreen controls. Must be used inside Map. */
function MapControls({
  position = "bottom-right",
  showZoom = true,
  showCompass = false,
  showLocate = false,
  showFullscreen = false,
  className,
  onLocate,
}) {
  const { map } = useMap();
  const [waitingForLocation, setWaitingForLocation] = useState(false);

  const handleZoomIn = useCallback(() => {
    map?.zoomTo(map.getZoom() + 1, { duration: 300 });
  }, [map]);

  const handleZoomOut = useCallback(() => {
    map?.zoomTo(map.getZoom() - 1, { duration: 300 });
  }, [map]);

  const handleResetBearing = useCallback(() => {
    map?.resetNorthPitch({ duration: 300 });
  }, [map]);

  const handleLocate = useCallback(() => {
    setWaitingForLocation(true);
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const coords = { longitude: pos.coords.longitude, latitude: pos.coords.latitude };
          map?.flyTo({ center: [coords.longitude, coords.latitude], zoom: 14, duration: 1500 });
          onLocate?.(coords);
          setWaitingForLocation(false);
        },
        () => {
          setWaitingForLocation(false);
        },
      );
    } else {
      setWaitingForLocation(false);
    }
  }, [map, onLocate]);

  const handleFullscreen = useCallback(() => {
    const container = map?.getContainer();
    if (!container) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      container.requestFullscreen();
    }
  }, [map]);

  return (
    <div className={cn("akm-controls", positionClasses[position], className)}>
      {showZoom && (
        <ControlGroup>
          <ControlButton onClick={handleZoomIn} label="Zoom in">
            <PlusIcon />
          </ControlButton>
          <ControlButton onClick={handleZoomOut} label="Zoom out">
            <MinusIcon />
          </ControlButton>
        </ControlGroup>
      )}
      {showCompass && (
        <ControlGroup>
          <CompassButton onClick={handleResetBearing} />
        </ControlGroup>
      )}
      {showLocate && (
        <ControlGroup>
          <ControlButton onClick={handleLocate} label="Find my location" disabled={waitingForLocation}>
            {waitingForLocation ? <LoaderIcon /> : <LocateIcon />}
          </ControlButton>
        </ControlGroup>
      )}
      {showFullscreen && (
        <ControlGroup>
          <ControlButton onClick={handleFullscreen} label="Toggle fullscreen">
            <MaximizeIcon />
          </ControlButton>
        </ControlGroup>
      )}
    </div>
  );
}

/** Standalone popup, not attached to a marker. */
function MapPopup({ longitude, latitude, onClose, children, className, closeButton = false, ...popupOptions }) {
  const { map } = useMap();
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const container = useMemo(() => document.createElement("div"), []);
  const { offset, maxWidth } = popupOptions;

  const popup = useMemo(() => {
    const popupInstance = new MapLibreGL.Popup({ offset: 16, ...popupOptions, closeButton: false })
      .setMaxWidth("none")
      .setLngLat([longitude, latitude]);

    return popupInstance;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!map) return;

    const onCloseProp = () => onCloseRef.current?.();

    popup.on("close", onCloseProp);

    popup.setDOMContent(container);
    popup.addTo(map);

    return () => {
      popup.off("close", onCloseProp);
      if (popup.isOpen()) {
        popup.remove();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]);

  useEffect(() => {
    const current = popup.getLngLat();
    if (!current || current.lng !== longitude || current.lat !== latitude) {
      popup.setLngLat([longitude, latitude]);
    }
    popup.setOffset(offset ?? 16);
    if (maxWidth) {
      popup.setMaxWidth(maxWidth);
    }
  }, [popup, longitude, latitude, offset, maxWidth]);

  const handleClose = () => popup.remove();

  return createPortal(
    <div className={cn("akm-popup", closeButton && "akm-popup-with-close", className)}>
      {closeButton && <PopupCloseButton onClick={handleClose} />}
      {children}
    </div>,
    container,
  );
}

/** Line/route on the map connecting coordinate points. */
function MapRoute({
  id: propId,
  coordinates,
  color = "#4285F4",
  width = 3,
  opacity = 0.8,
  dashArray,
  onClick,
  onMouseEnter,
  onMouseLeave,
  interactive = true,
}) {
  const { map, isLoaded } = useMap();
  const autoId = useId();
  const id = propId ?? autoId;
  const sourceId = `route-source-${id}`;
  const layerId = `route-layer-${id}`;

  useEffect(() => {
    if (!isLoaded || !map) return;

    map.addSource(sourceId, {
      type: "geojson",
      data: { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [] } },
    });

    map.addLayer({
      id: layerId,
      type: "line",
      source: sourceId,
      layout: { "line-join": "round", "line-cap": "round" },
      paint: {
        "line-color": color,
        "line-width": width,
        "line-opacity": opacity,
        ...(dashArray && { "line-dasharray": dashArray }),
      },
    });

    return () => {
      try {
        if (map.getLayer(layerId)) map.removeLayer(layerId);
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      } catch {
        // style may be mid-reload
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, map]);

  useEffect(() => {
    if (!isLoaded || !map || coordinates.length < 2) return;

    const source = map.getSource(sourceId);
    if (source) {
      source.setData({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates } });
    }
  }, [isLoaded, map, coordinates, sourceId]);

  useEffect(() => {
    if (!isLoaded || !map || !map.getLayer(layerId)) return;

    map.setPaintProperty(layerId, "line-color", color);
    map.setPaintProperty(layerId, "line-width", width);
    map.setPaintProperty(layerId, "line-opacity", opacity);
    map.setPaintProperty(layerId, "line-dasharray", dashArray);
  }, [isLoaded, map, layerId, color, width, opacity, dashArray]);

  useEffect(() => {
    if (!isLoaded || !map || !interactive) return;

    const handleClick = () => onClick?.();
    const handleMouseEnter = () => {
      map.getCanvas().style.cursor = "pointer";
      onMouseEnter?.();
    };
    const handleMouseLeave = () => {
      map.getCanvas().style.cursor = "";
      onMouseLeave?.();
    };

    map.on("click", layerId, handleClick);
    map.on("mouseenter", layerId, handleMouseEnter);
    map.on("mouseleave", layerId, handleMouseLeave);

    return () => {
      map.off("click", layerId, handleClick);
      map.off("mouseenter", layerId, handleMouseEnter);
      map.off("mouseleave", layerId, handleMouseLeave);
    };
  }, [isLoaded, map, layerId, onClick, onMouseEnter, onMouseLeave, interactive]);

  return null;
}

const GEOJSON_DEFAULT_COLORS = {
  light: { fill: "#d4d4d4", line: "#ffffff" },
  dark: { fill: "#404040", line: "#171717" },
};

/** Renders arbitrary GeoJSON as fill + outline layers. Typically used with `blank`. */
function MapGeoJSON({
  data,
  id: propId,
  promoteId,
  fillPaint,
  linePaint,
  fillHoverPaint,
  onClick,
  onHover,
  interactive = false,
  beforeId,
}) {
  const { map, isLoaded, resolvedTheme } = useMap();
  const autoId = useId();
  const id = propId ?? autoId;
  const sourceId = `geojson-source-${id}`;
  const fillLayerId = `geojson-fill-${id}`;
  const lineLayerId = `geojson-line-${id}`;

  const defaults = GEOJSON_DEFAULT_COLORS[resolvedTheme] ?? GEOJSON_DEFAULT_COLORS.light;

  const showFill = fillPaint !== false;
  const showLine = linePaint !== false;

  const mergedFillPaint = useMemo(
    () => mergeHoverPaint({ "fill-color": defaults.fill, ...(fillPaint || {}) }, fillHoverPaint),
    [defaults.fill, fillPaint, fillHoverPaint],
  );
  const mergedLinePaint = useMemo(
    () => ({ "line-color": defaults.line, "line-width": 0.5, ...(linePaint || {}) }),
    [defaults.line, linePaint],
  );
  const latestRef = useRef({ onClick, onHover });
  latestRef.current = { onClick, onHover };

  useEffect(() => {
    if (!isLoaded || !map) return;

    map.addSource(sourceId, { type: "geojson", data, ...(promoteId ? { promoteId } : {}) });

    return () => {
      try {
        if (map.getLayer(lineLayerId)) map.removeLayer(lineLayerId);
        if (map.getLayer(fillLayerId)) map.removeLayer(fillLayerId);
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      } catch {
        // style may be mid-reload
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, map]);

  useEffect(() => {
    if (!isLoaded || !map) return;
    const source = map.getSource(sourceId);
    source?.setData(data);
  }, [isLoaded, map, data, sourceId]);

  useEffect(() => {
    if (!isLoaded || !map) return;

    const source = map.getSource(sourceId);
    if (!source) return;

    if (showFill && !map.getLayer(fillLayerId)) {
      map.addLayer({ id: fillLayerId, type: "fill", source: sourceId, paint: mergedFillPaint }, beforeId);
    } else if (!showFill && map.getLayer(fillLayerId)) {
      map.removeLayer(fillLayerId);
    }

    if (showLine && !map.getLayer(lineLayerId)) {
      map.addLayer({ id: lineLayerId, type: "line", source: sourceId, paint: mergedLinePaint }, beforeId);
    } else if (!showLine && map.getLayer(lineLayerId)) {
      map.removeLayer(lineLayerId);
    }

    if (showFill && map.getLayer(fillLayerId)) {
      for (const [key, value] of Object.entries(mergedFillPaint)) {
        map.setPaintProperty(fillLayerId, key, value);
      }
    }
    if (showLine && map.getLayer(lineLayerId)) {
      for (const [key, value] of Object.entries(mergedLinePaint)) {
        map.setPaintProperty(lineLayerId, key, value);
      }
    }
  }, [isLoaded, map, sourceId, fillLayerId, lineLayerId, showFill, showLine, mergedFillPaint, mergedLinePaint, beforeId]);

  useEffect(() => {
    if (!isLoaded || !map || !interactive || !showFill) return;

    let hoveredId = null;

    const setHover = (next) => {
      if (next === hoveredId) return;
      const sourceExists = !!map.getSource(sourceId);
      if (hoveredId != null && sourceExists) {
        map.setFeatureState({ source: sourceId, id: hoveredId }, { hover: false });
      }
      hoveredId = next;
      if (next != null && sourceExists) {
        map.setFeatureState({ source: sourceId, id: next }, { hover: true });
      }
    };

    const handleMouseMove = (e) => {
      const feature = e.features?.[0];
      if (!feature) return;
      map.getCanvas().style.cursor = "pointer";

      const featureId = feature.id;
      if (featureId === hoveredId) return;
      setHover(featureId ?? null);
      latestRef.current.onHover?.({
        feature,
        longitude: e.lngLat.lng,
        latitude: e.lngLat.lat,
        originalEvent: e,
      });
    };

    const handleMouseLeave = () => {
      setHover(null);
      map.getCanvas().style.cursor = "";
      latestRef.current.onHover?.(null);
    };

    const handleClick = (e) => {
      const feature = e.features?.[0];
      if (!feature) return;
      latestRef.current.onClick?.({
        feature,
        longitude: e.lngLat.lng,
        latitude: e.lngLat.lat,
        originalEvent: e,
      });
    };

    map.on("mousemove", fillLayerId, handleMouseMove);
    map.on("mouseleave", fillLayerId, handleMouseLeave);
    map.on("click", fillLayerId, handleClick);

    return () => {
      map.off("mousemove", fillLayerId, handleMouseMove);
      map.off("mouseleave", fillLayerId, handleMouseLeave);
      map.off("click", fillLayerId, handleClick);
      setHover(null);
      map.getCanvas().style.cursor = "";
    };
  }, [isLoaded, map, fillLayerId, sourceId, interactive, showFill]);

  return null;
}

const DEFAULT_ARC_CURVATURE = 0.2;
const DEFAULT_ARC_SAMPLES = 64;
const ARC_HIT_MIN_WIDTH = 12;
const ARC_HIT_PADDING = 6;

const DEFAULT_ARC_PAINT = { "line-color": "#4285F4", "line-width": 2, "line-opacity": 0.85 };
const DEFAULT_ARC_LAYOUT = { "line-join": "round", "line-cap": "round" };

function buildArcCoordinates(from, to, curvature, samples) {
  const [x0, y0] = from;
  const [xTo, y2] = to;
  const rawDx = xTo - x0;
  const x2 = rawDx > 180 ? xTo - 360 : rawDx < -180 ? xTo + 360 : xTo;
  const dx = x2 - x0;
  const dy = y2 - y0;
  const distance = Math.hypot(dx, dy);

  if (distance === 0 || curvature === 0) return [from, [x2, y2]];

  const mx = (x0 + x2) / 2;
  const my = (y0 + y2) / 2;
  const nx = -dy / distance;
  const ny = dx / distance;
  const offset = distance * curvature;
  const cx = mx + nx * offset;
  const cy = my + ny * offset;

  const points = [];
  const segments = Math.max(2, Math.floor(samples));
  for (let i = 0; i <= segments; i += 1) {
    const t = i / segments;
    const inv = 1 - t;
    const x = inv * inv * x0 + 2 * inv * t * cx + t * t * x2;
    const y = inv * inv * y0 + 2 * inv * t * cy + t * t * y2;
    points.push([x, y]);
  }
  return points;
}

/** Curved connection arcs between coordinate pairs. */
function MapArc({
  data,
  id: propId,
  curvature = DEFAULT_ARC_CURVATURE,
  samples = DEFAULT_ARC_SAMPLES,
  paint,
  layout,
  hoverPaint,
  onClick,
  onHover,
  interactive = true,
  beforeId,
}) {
  const { map, isLoaded } = useMap();
  const autoId = useId();
  const id = propId ?? autoId;
  const sourceId = `arc-source-${id}`;
  const layerId = `arc-layer-${id}`;
  const hitLayerId = `arc-hit-layer-${id}`;

  const mergedPaint = useMemo(() => mergeHoverPaint({ ...DEFAULT_ARC_PAINT, ...paint }, hoverPaint), [paint, hoverPaint]);
  const mergedLayout = useMemo(() => ({ ...DEFAULT_ARC_LAYOUT, ...layout }), [layout]);

  const hitWidth = useMemo(() => {
    const w = paint?.["line-width"] ?? DEFAULT_ARC_PAINT["line-width"];
    const base = typeof w === "number" ? w : ARC_HIT_MIN_WIDTH;
    return Math.max(base + ARC_HIT_PADDING, ARC_HIT_MIN_WIDTH);
  }, [paint]);

  const geoJSON = useMemo(
    () => ({
      type: "FeatureCollection",
      features: data.map((arc) => {
        const { from, to, ...properties } = arc;
        return {
          type: "Feature",
          properties,
          geometry: { type: "LineString", coordinates: buildArcCoordinates(from, to, curvature, samples) },
        };
      }),
    }),
    [data, curvature, samples],
  );

  const latestRef = useRef({ data, onClick, onHover });
  latestRef.current = { data, onClick, onHover };

  useEffect(() => {
    if (!isLoaded || !map) return;

    map.addSource(sourceId, { type: "geojson", data: geoJSON, promoteId: "id" });

    map.addLayer(
      {
        id: hitLayerId,
        type: "line",
        source: sourceId,
        layout: DEFAULT_ARC_LAYOUT,
        paint: { "line-color": "rgba(0, 0, 0, 0)", "line-width": hitWidth, "line-opacity": 1 },
      },
      beforeId,
    );

    map.addLayer({ id: layerId, type: "line", source: sourceId, layout: mergedLayout, paint: mergedPaint }, beforeId);

    return () => {
      try {
        if (map.getLayer(layerId)) map.removeLayer(layerId);
        if (map.getLayer(hitLayerId)) map.removeLayer(hitLayerId);
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      } catch {
        // ignore
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, map]);

  useEffect(() => {
    if (!isLoaded || !map) return;
    const source = map.getSource(sourceId);
    source?.setData(geoJSON);
  }, [isLoaded, map, geoJSON, sourceId]);

  useEffect(() => {
    if (!isLoaded || !map || !map.getLayer(layerId)) return;
    for (const [key, value] of Object.entries(mergedPaint)) {
      map.setPaintProperty(layerId, key, value);
    }
    for (const [key, value] of Object.entries(mergedLayout)) {
      map.setLayoutProperty(layerId, key, value);
    }
    if (map.getLayer(hitLayerId)) {
      map.setPaintProperty(hitLayerId, "line-width", hitWidth);
    }
  }, [isLoaded, map, layerId, hitLayerId, mergedPaint, mergedLayout, hitWidth]);

  useEffect(() => {
    if (!isLoaded || !map || !interactive) return;

    let hoveredId = null;

    const setHover = (next) => {
      if (next === hoveredId) return;
      const sourceExists = !!map.getSource(sourceId);
      if (hoveredId != null && sourceExists) {
        map.setFeatureState({ source: sourceId, id: hoveredId }, { hover: false });
      }
      hoveredId = next;
      if (next != null && sourceExists) {
        map.setFeatureState({ source: sourceId, id: next }, { hover: true });
      }
    };

    const findArc = (featureId) =>
      featureId == null ? undefined : latestRef.current.data.find((arc) => String(arc.id) === String(featureId));

    const handleMouseMove = (e) => {
      const featureId = e.features?.[0]?.id;
      if (featureId == null || featureId === hoveredId) return;

      setHover(featureId);
      map.getCanvas().style.cursor = "pointer";

      const arc = findArc(featureId);
      if (arc) {
        latestRef.current.onHover?.({ arc, longitude: e.lngLat.lng, latitude: e.lngLat.lat, originalEvent: e });
      }
    };

    const handleMouseLeave = () => {
      setHover(null);
      map.getCanvas().style.cursor = "";
      latestRef.current.onHover?.(null);
    };

    const handleClick = (e) => {
      const arc = findArc(e.features?.[0]?.id);
      if (!arc) return;
      latestRef.current.onClick?.({ arc, longitude: e.lngLat.lng, latitude: e.lngLat.lat, originalEvent: e });
    };

    map.on("mousemove", hitLayerId, handleMouseMove);
    map.on("mouseleave", hitLayerId, handleMouseLeave);
    map.on("click", hitLayerId, handleClick);

    return () => {
      map.off("mousemove", hitLayerId, handleMouseMove);
      map.off("mouseleave", hitLayerId, handleMouseLeave);
      map.off("click", hitLayerId, handleClick);
      setHover(null);
      map.getCanvas().style.cursor = "";
    };
  }, [isLoaded, map, hitLayerId, sourceId, interactive]);

  return null;
}

const DEFAULT_CLUSTER_COLORS = ["#22c55e", "#eab308", "#ef4444"];
const DEFAULT_CLUSTER_THRESHOLDS = [100, 750];

/** Clustered point layer using MapLibre GL's native clustering. */
function MapClusterLayer({
  data,
  clusterMaxZoom = 14,
  clusterRadius = 50,
  clusterColors = DEFAULT_CLUSTER_COLORS,
  clusterThresholds = DEFAULT_CLUSTER_THRESHOLDS,
  pointColor = "#3b82f6",
  onPointClick,
  onClusterClick,
}) {
  const { map, isLoaded } = useMap();
  const id = useId();
  const sourceId = `cluster-source-${id}`;
  const clusterLayerId = `clusters-${id}`;
  const clusterCountLayerId = `cluster-count-${id}`;
  const unclusteredLayerId = `unclustered-point-${id}`;

  const stylePropsRef = useRef({ clusterColors, clusterThresholds, pointColor });

  useEffect(() => {
    if (!isLoaded || !map) return;

    map.addSource(sourceId, { type: "geojson", data, cluster: true, clusterMaxZoom, clusterRadius });

    map.addLayer({
      id: clusterLayerId,
      type: "circle",
      source: sourceId,
      filter: ["has", "point_count"],
      paint: {
        "circle-color": [
          "step",
          ["get", "point_count"],
          clusterColors[0],
          clusterThresholds[0],
          clusterColors[1],
          clusterThresholds[1],
          clusterColors[2],
        ],
        "circle-radius": ["step", ["get", "point_count"], 20, clusterThresholds[0], 30, clusterThresholds[1], 40],
        "circle-stroke-width": 1,
        "circle-stroke-color": "#fff",
        "circle-opacity": 0.85,
      },
    });

    map.addLayer({
      id: clusterCountLayerId,
      type: "symbol",
      source: sourceId,
      filter: ["has", "point_count"],
      // CARTO's public glyphs endpoint (used by the default positron/dark-matter
      // styles) only hosts specific named font stacks — "Open Sans" alone 404s;
      // the weight suffix is required (confirmed against the style's own glyphs).
      layout: {
        "text-field": "{point_count_abbreviated}",
        "text-font": ["Open Sans Regular"],
        "text-size": 12,
      },
      paint: { "text-color": "#fff" },
    });

    map.addLayer({
      id: unclusteredLayerId,
      type: "circle",
      source: sourceId,
      filter: ["!", ["has", "point_count"]],
      paint: {
        "circle-color": pointColor,
        "circle-radius": 5,
        "circle-stroke-width": 2,
        "circle-stroke-color": "#fff",
      },
    });

    return () => {
      try {
        if (map.getLayer(clusterCountLayerId)) map.removeLayer(clusterCountLayerId);
        if (map.getLayer(unclusteredLayerId)) map.removeLayer(unclusteredLayerId);
        if (map.getLayer(clusterLayerId)) map.removeLayer(clusterLayerId);
        if (map.getSource(sourceId)) map.removeSource(sourceId);
      } catch {
        // ignore
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, map, sourceId]);

  useEffect(() => {
    if (!isLoaded || !map || typeof data === "string") return;

    const source = map.getSource(sourceId);
    if (source) {
      source.setData(data);
    }
  }, [isLoaded, map, data, sourceId]);

  useEffect(() => {
    if (!isLoaded || !map) return;

    const prev = stylePropsRef.current;
    const colorsChanged = prev.clusterColors !== clusterColors || prev.clusterThresholds !== clusterThresholds;

    if (map.getLayer(clusterLayerId) && colorsChanged) {
      map.setPaintProperty(clusterLayerId, "circle-color", [
        "step",
        ["get", "point_count"],
        clusterColors[0],
        clusterThresholds[0],
        clusterColors[1],
        clusterThresholds[1],
        clusterColors[2],
      ]);
      map.setPaintProperty(clusterLayerId, "circle-radius", [
        "step",
        ["get", "point_count"],
        20,
        clusterThresholds[0],
        30,
        clusterThresholds[1],
        40,
      ]);
    }

    if (map.getLayer(unclusteredLayerId) && prev.pointColor !== pointColor) {
      map.setPaintProperty(unclusteredLayerId, "circle-color", pointColor);
    }

    stylePropsRef.current = { clusterColors, clusterThresholds, pointColor };
  }, [isLoaded, map, clusterLayerId, unclusteredLayerId, clusterColors, clusterThresholds, pointColor]);

  useEffect(() => {
    if (!isLoaded || !map) return;

    const handleClusterClick = async (e) => {
      const features = map.queryRenderedFeatures(e.point, { layers: [clusterLayerId] });
      if (!features.length) return;

      const feature = features[0];
      const clusterId = feature.properties?.cluster_id;
      const pointCount = feature.properties?.point_count;
      const coordinates = feature.geometry.coordinates;

      if (onClusterClick) {
        onClusterClick(clusterId, coordinates, pointCount);
      } else {
        const source = map.getSource(sourceId);
        const zoom = await source.getClusterExpansionZoom(clusterId);
        map.easeTo({ center: coordinates, zoom });
      }
    };

    const handlePointClick = (e) => {
      if (!onPointClick || !e.features?.length) return;

      const feature = e.features[0];
      const coordinates = feature.geometry.coordinates.slice();

      while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
        coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
      }

      onPointClick(feature, coordinates);
    };

    const handleMouseEnterCluster = () => {
      map.getCanvas().style.cursor = "pointer";
    };
    const handleMouseLeaveCluster = () => {
      map.getCanvas().style.cursor = "";
    };
    const handleMouseEnterPoint = () => {
      if (onPointClick) {
        map.getCanvas().style.cursor = "pointer";
      }
    };
    const handleMouseLeavePoint = () => {
      map.getCanvas().style.cursor = "";
    };

    map.on("click", clusterLayerId, handleClusterClick);
    map.on("click", unclusteredLayerId, handlePointClick);
    map.on("mouseenter", clusterLayerId, handleMouseEnterCluster);
    map.on("mouseleave", clusterLayerId, handleMouseLeaveCluster);
    map.on("mouseenter", unclusteredLayerId, handleMouseEnterPoint);
    map.on("mouseleave", unclusteredLayerId, handleMouseLeavePoint);

    return () => {
      map.off("click", clusterLayerId, handleClusterClick);
      map.off("click", unclusteredLayerId, handlePointClick);
      map.off("mouseenter", clusterLayerId, handleMouseEnterCluster);
      map.off("mouseleave", clusterLayerId, handleMouseLeaveCluster);
      map.off("mouseenter", unclusteredLayerId, handleMouseEnterPoint);
      map.off("mouseleave", unclusteredLayerId, handleMouseLeavePoint);
    };
  }, [isLoaded, map, clusterLayerId, unclusteredLayerId, sourceId, onClusterClick, onPointClick]);

  return null;
}

const DEFAULT_OSRM_URL = "https://router.project-osrm.org";

function buildOsrmUrl({
  routingUrl,
  profile,
  startLong,
  startLat,
  endLong,
  endLat,
  alternatives,
  overview,
  geometries,
  steps,
  continueStraight,
  annotations,
  exclude,
}) {
  const base = (routingUrl || DEFAULT_OSRM_URL).replace(/\/$/, "");
  const coords = `${startLong},${startLat};${endLong},${endLat}`;
  const params = new URLSearchParams();
  params.set("overview", overview ?? "full");
  params.set("geometries", geometries ?? "geojson");
  if (steps != null) params.set("steps", String(steps));
  if (alternatives != null) params.set("alternatives", String(alternatives));
  if (continueStraight != null) {
    params.set("continue_straight", String(continueStraight));
  }
  if (annotations != null) {
    params.set(
      "annotations",
      Array.isArray(annotations) ? annotations.join(",") : String(annotations),
    );
  }
  if (exclude && exclude.length) params.set("exclude", exclude.join(","));
  return `${base}/route/v1/${profile}/${coords}?${params.toString()}`;
}

function formatOsrmRoute(route, profile, includeGeometry, includeSteps) {
  const steps = (route.legs || []).flatMap((leg) => leg.steps || []);
  return {
    profile,
    coordinates: includeGeometry === false ? [] : route.geometry.coordinates,
    duration: route.duration,
    distance: route.distance,
    steps: includeSteps === false ? [] : steps,
  };
}

const MANEUVER_TEXT = {
  depart: "Head out",
  arrive: "Arrive at destination",
  turn: "Turn",
  "new name": "Continue",
  continue: "Continue straight",
  merge: "Merge",
  "on ramp": "Take the ramp",
  "off ramp": "Take the exit",
  fork: "Keep",
  "end of road": "Turn",
  roundabout: "Enter the roundabout",
  rotary: "Enter the rotary",
  "roundabout turn": "At the roundabout, turn",
  notification: "Continue",
};

function formatInstruction(step) {
  const type = step.maneuver?.type ?? "continue";
  const modifier = step.maneuver?.modifier;
  const base = MANEUVER_TEXT[type] ?? "Continue";
  const withModifier = modifier && type !== "depart" && type !== "arrive"
    ? `${base} ${modifier}`
    : base;
  const road = step.name ? ` onto ${step.name}` : "";
  return `${withModifier}${road}`;
}

function formatDuration(seconds) {
  const mins = Math.round(seconds / 60);
  if (mins < 60) return `${mins} min`;
  const hours = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  return `${hours}h ${remainingMins}m`;
}

function formatDistance(meters) {
  if (meters < 1000) return `${Math.round(meters)} m`;
  return `${(meters / 1000).toFixed(1)} km`;
}

const EMPTY_ROUTES = [];

/**
 * Fetches real routing data from an OSRM-compatible API and renders the
 * resulting route(s) as line layers, publishing the fetched state via
 * context for a sibling `MapDirectionsPanel` to consume.
 *
 * Note: Reflex renders unset ``Var.create(None)`` props as an explicit
 * `null` (not `undefined`), which ES6 default parameters do NOT catch —
 * every optional prop is therefore re-coalesced with `??` right after
 * destructuring instead of relying on `= defaultValue` in the signature.
 */
function VoyagerMapLibreNavigation(rawProps) {
  const {
    startLat,
    startLong,
    endLat,
    endLong,
    profile: profileProp,
    profiles: profilesProp,
    routingUrl,
    alternatives: alternativesProp,
    overview: overviewProp,
    geometries: geometriesProp,
    steps: stepsProp,
    lineColor: lineColorProp,
    lineWidth: lineWidthProp,
    lineOpacity: lineOpacityProp,
    lineDasharray,
    fitBounds: fitBoundsProp,
    fitBoundsPadding,
    fitBoundsMaxZoom,
    fitBoundsDurationMs,
    continueStraight,
    annotations,
    exclude,
    includeSteps: includeStepsProp,
    includeGeometry: includeGeometryProp,
    showEndMarkers: showEndMarkersProp,
    startMarkerColor: startMarkerColorProp,
    endMarkerColor: endMarkerColorProp,
    markerRadius: markerRadiusProp,
  } = rawProps;

  const profile = profileProp ?? "driving";
  const alternatives = alternativesProp ?? false;
  const overview = overviewProp ?? "full";
  const geometries = geometriesProp ?? "geojson";
  const steps = stepsProp ?? true;
  const lineColor = lineColorProp ?? "#4285F4";
  const lineWidth = lineWidthProp ?? 5;
  const lineOpacity = lineOpacityProp ?? 0.85;
  const fitBounds = fitBoundsProp ?? true;
  const resolvedFitBoundsPadding = fitBoundsPadding ?? 48;
  const resolvedFitBoundsDurationMs = fitBoundsDurationMs ?? 800;
  const includeSteps = includeStepsProp ?? true;
  const includeGeometry = includeGeometryProp ?? true;
  const showEndMarkers = showEndMarkersProp ?? true;
  const startMarkerColor = startMarkerColorProp ?? "#22c55e";
  const endMarkerColor = endMarkerColorProp ?? "#ef4444";
  const markerRadius = markerRadiusProp ?? 8;

  // Reflex may re-evaluate a static list-literal prop (e.g. `profiles=[...]`)
  // into a brand-new array on every parent render even though its contents
  // never change. Memoize on a content fingerprint (not the raw reference)
  // so `profiles` stays referentially stable — several effects below use it
  // in their dependency arrays, and an unstable reference there would
  // re-trigger `setNavigation` every render, cascading into repeated
  // MapLibre layer churn (and, in the worst case, a lost WebGL context).
  const profilesFingerprint =
    profilesProp && profilesProp.length ? profilesProp.join(",") : "";
  const profiles = useMemo(
    () => (profilesFingerprint ? profilesFingerprint.split(",") : null),
    [profilesFingerprint],
  );

  const { map, isLoaded, setNavigation } = useMap();
  const id = useId();
  const availableProfiles = useMemo(
    () => (profiles ? profiles : [profile]),
    [profiles, profile],
  );
  const [activeProfile, setActiveProfile] = useState(availableProfiles[0]);
  const [routesByProfile, setRoutesByProfile] = useState({});
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!availableProfiles.includes(activeProfile)) {
      setActiveProfile(availableProfiles[0]);
    }
  }, [availableProfiles, activeProfile]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [activeProfile]);

  // Fetch routes for every requested profile whenever inputs change.
  useEffect(() => {
    if (
      !Number.isFinite(startLat) ||
      !Number.isFinite(startLong) ||
      !Number.isFinite(endLat) ||
      !Number.isFinite(endLong)
    ) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);

    // Use allSettled (not all) so that one profile failing — e.g. the
    // public router.project-osrm.org demo server only actually serves the
    // "driving" profile, so "walking"/"cycling" 400 there — doesn't discard
    // routes that DID succeed for the other requested profiles.
    Promise.allSettled(
      availableProfiles.map((p) =>
        fetch(
          buildOsrmUrl({
            routingUrl,
            profile: p,
            startLong,
            startLat,
            endLong,
            endLat,
            alternatives,
            overview,
            geometries,
            steps: steps && includeSteps,
            continueStraight,
            annotations,
            exclude,
          }),
        )
          .then((res) => {
            if (!res.ok) throw new Error(`Routing request failed (${res.status})`);
            return res.json();
          })
          .then((data) => {
            if (!data.routes || !data.routes.length) {
              throw new Error("No route found");
            }
            return [
              p,
              data.routes.map((r) =>
                formatOsrmRoute(r, p, includeGeometry, includeSteps),
              ),
            ];
          }),
      ),
    ).then((results) => {
      if (cancelled) return;

      const fulfilled = results.filter((r) => r.status === "fulfilled");
      const entries = fulfilled.map((r) => r.value);
      setRoutesByProfile(Object.fromEntries(entries));

      if (!entries.length) {
        const firstError = results.find((r) => r.status === "rejected");
        setError(firstError?.reason?.message || String(firstError?.reason) || "No route found");
      } else if (entries.length < availableProfiles.length) {
        results
          .filter((r) => r.status === "rejected")
          .forEach((r) => {
            // eslint-disable-next-line no-console
            console.warn("MapNavigation: a profile failed to fetch", r.reason);
          });
      }
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    startLat,
    startLong,
    endLat,
    endLong,
    JSON.stringify(availableProfiles),
    routingUrl,
    alternatives,
    overview,
    geometries,
    steps,
    continueStraight,
    JSON.stringify(annotations),
    JSON.stringify(exclude),
    includeSteps,
    includeGeometry,
  ]);

  // Use a stable empty-array constant (not a fresh `[]` literal) so this
  // doesn't change reference on every render while the fetch is pending —
  // an unstable reference here would re-trigger the "publish state" effect
  // below every render, which calls setNavigation() and re-renders this
  // component (a context consumer), causing an infinite update loop.
  const routes = routesByProfile[activeProfile] ?? EMPTY_ROUTES;

  // Add/remove route line layers.
  useEffect(() => {
    if (!isLoaded || !map || !routes.length) return;

    const layerIds = routes.map((route, index) => ({
      sourceId: `nav-source-${id}-${index}`,
      layerId: `nav-layer-${id}-${index}`,
      route,
    }));

    layerIds.forEach(({ sourceId, layerId, route }) => {
      if (!map.getSource(sourceId)) {
        map.addSource(sourceId, {
          type: "geojson",
          data: {
            type: "Feature",
            properties: {},
            geometry: { type: "LineString", coordinates: route.coordinates },
          },
        });
      }
      if (!map.getLayer(layerId)) {
        map.addLayer({
          id: layerId,
          type: "line",
          source: sourceId,
          layout: { "line-join": "round", "line-cap": "round" },
          paint: {
            "line-color": lineColor,
            "line-width": lineWidth,
            "line-opacity": lineOpacity,
            ...(lineDasharray ? { "line-dasharray": lineDasharray } : {}),
          },
        });
      }
    });

    return () => {
      layerIds.forEach(({ sourceId, layerId }) => {
        try {
          if (map.getLayer(layerId)) map.removeLayer(layerId);
          if (map.getSource(sourceId)) map.removeSource(sourceId);
        } catch {
          // style may be mid-reload
        }
      });
    };
  }, [isLoaded, map, routes, id, lineColor, lineWidth, lineOpacity, lineDasharray]);

  // Highlight the selected alternative; mute the others.
  useEffect(() => {
    if (!isLoaded || !map || !routes.length) return;
    routes.forEach((_, index) => {
      const layerId = `nav-layer-${id}-${index}`;
      if (!map.getLayer(layerId)) return;
      const isSelected = index === selectedIndex;
      map.setPaintProperty(layerId, "line-color", isSelected ? lineColor : "#94a3b8");
      map.setPaintProperty(
        layerId,
        "line-width",
        isSelected ? lineWidth : Math.max(lineWidth - 2, 2),
      );
      map.setPaintProperty(layerId, "line-opacity", isSelected ? lineOpacity : 0.55);
    });
  }, [isLoaded, map, routes, selectedIndex, id, lineColor, lineWidth, lineOpacity]);

  // Click a route line to select it.
  useEffect(() => {
    if (!isLoaded || !map || !routes.length) return;
    const handlers = routes.map((_, index) => {
      const layerId = `nav-layer-${id}-${index}`;
      const handleClick = () => setSelectedIndex(index);
      const handleEnter = () => {
        map.getCanvas().style.cursor = "pointer";
      };
      const handleLeave = () => {
        map.getCanvas().style.cursor = "";
      };
      map.on("click", layerId, handleClick);
      map.on("mouseenter", layerId, handleEnter);
      map.on("mouseleave", layerId, handleLeave);
      return { layerId, handleClick, handleEnter, handleLeave };
    });
    return () => {
      handlers.forEach(({ layerId, handleClick, handleEnter, handleLeave }) => {
        map.off("click", layerId, handleClick);
        map.off("mouseenter", layerId, handleEnter);
        map.off("mouseleave", layerId, handleLeave);
      });
    };
  }, [isLoaded, map, routes, id]);

  // Start/end markers.
  useEffect(() => {
    if (!isLoaded || !map || !showEndMarkers) return;
    if (
      !Number.isFinite(startLat) ||
      !Number.isFinite(startLong) ||
      !Number.isFinite(endLat) ||
      !Number.isFinite(endLong)
    ) {
      return;
    }
    const scale = (markerRadius || 8) / 8;
    const startMarker = new MapLibreGL.Marker({ color: startMarkerColor, scale })
      .setLngLat([startLong, startLat])
      .addTo(map);
    const endMarker = new MapLibreGL.Marker({ color: endMarkerColor, scale })
      .setLngLat([endLong, endLat])
      .addTo(map);
    return () => {
      startMarker.remove();
      endMarker.remove();
    };
  }, [
    isLoaded,
    map,
    showEndMarkers,
    startLat,
    startLong,
    endLat,
    endLong,
    startMarkerColor,
    endMarkerColor,
    markerRadius,
  ]);

  // Fit the viewport to the selected route.
  useEffect(() => {
    if (!isLoaded || !map || !fitBounds || !routes.length) return;
    const coords = routes[selectedIndex]?.coordinates ?? routes[0].coordinates;
    if (!coords || !coords.length) return;

    // Defensively drop any malformed/non-finite coordinate pairs — a single
    // bad point would otherwise make MapLibre's fitBounds throw
    // "Invalid LngLat object: (NaN, NaN)" and crash the whole map.
    const validCoords = coords.filter(
      (c) => Array.isArray(c) && Number.isFinite(c[0]) && Number.isFinite(c[1]),
    );
    if (!validCoords.length) return;

    let cancelled = false;
    let retryTimer = null;

    const doFit = (isRetry) => {
      if (cancelled) return;
      try {
        map.resize();
        const bounds = validCoords.reduce(
          (b, c) => b.extend(c),
          new MapLibreGL.LngLatBounds(validCoords[0], validCoords[0]),
        );
        // IMPORTANT: MapLibre merges these options over its internal
        // defaults (`{ maxZoom: this.transform.maxZoom, ... }`) using a
        // plain `for...in` copy — an explicit `maxZoom: undefined` key is
        // still enumerable and therefore *overwrites* that default with
        // `undefined`. `Math.min(zoom, undefined)` is then `NaN`, which is
        // the actual source of "Invalid LngLat object: (NaN, NaN)" here —
        // completely independent of container size or bounds validity. Only
        // include the key at all when a real value was provided.
        map.fitBounds(bounds, {
          padding: resolvedFitBoundsPadding,
          ...(fitBoundsMaxZoom != null ? { maxZoom: fitBoundsMaxZoom } : {}),
          // Animating right after the map/layout has just settled can hit
          // MapLibre in a transient bad transform state; a plain jump is
          // more robust, and self-healing retries fall back to it below.
          duration: isRetry ? 0 : resolvedFitBoundsDurationMs,
        });
      } catch (err) {
        if (!isRetry) {
          // MapLibre's internal camera transform can momentarily be in a
          // bad numeric state right as a map first settles (independent of
          // container size/valid bounds — both are verified above). Retry
          // once, shortly after, before giving up and just logging.
          retryTimer = setTimeout(() => doFit(true), 300);
          return;
        }
        // eslint-disable-next-line no-console
        console.warn("MapNavigation: failed to fit bounds to route", err);
      }
    };

    // MapLibre computes the target camera from the map's CURRENT transform
    // (container width/height, zoom, bearing, pitch). A `Map` mounting
    // inside a card alongside several other maps can genuinely stay
    // zero-sized for a while (well beyond a single animation frame — plain
    // rAF polling isn't reliable here), which makes cameraForBounds produce
    // NaN even though the bounds themselves are perfectly valid. Use a
    // ResizeObserver to fit only once the container actually has a size,
    // with a capped fallback timer so we still attempt a fit even if the
    // container is (unexpectedly) never observed to resize.
    const container = map.getContainer();
    if (container.clientWidth > 0 && container.clientHeight > 0) {
      doFit(false);
      return () => {
        cancelled = true;
        clearTimeout(retryTimer);
      };
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry && entry.contentRect.width > 0 && entry.contentRect.height > 0) {
        observer.disconnect();
        doFit(false);
      }
    });
    observer.observe(container);

    const fallbackTimer = setTimeout(() => {
      observer.disconnect();
      doFit(false);
    }, 2000);

    return () => {
      cancelled = true;
      clearTimeout(retryTimer);
      observer.disconnect();
      clearTimeout(fallbackTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, map, fitBounds, routes, selectedIndex]);

  // Publish state for MapDirectionsPanel.
  useEffect(() => {
    setNavigation?.({
      loading,
      error,
      profile: activeProfile,
      profiles,
      setActiveProfile,
      routes,
      selectedIndex,
      setSelectedIndex,
      start: { lat: startLat, lng: startLong },
      end: { lat: endLat, lng: endLong },
    });
    return () => setNavigation?.(null);
  }, [
    loading,
    error,
    activeProfile,
    profiles,
    routes,
    selectedIndex,
    startLat,
    startLong,
    endLat,
    endLong,
    setNavigation,
  ]);

  return null;
}

const DIRECTIONS_POSITION_CLASSES = {
  "top-left": "akm-controls-top-left",
  "top-right": "akm-controls-top-right",
  "bottom-left": "akm-controls-bottom-left",
  "bottom-right": "akm-controls-bottom-right",
};

/**
 * Reads the navigation state published by a sibling `VoyagerMapLibreNavigation`
 * and renders a route summary / profile switch / alternatives / turn-by-turn
 * step list overlay.
 *
 * Note: unset ``Var.create(None)`` props arrive as an explicit `null` (not
 * `undefined`), so defaults are re-applied via `??` after destructuring
 * rather than relying solely on ES6 default parameters.
 */
function VoyagerMapLibreDirectionsPanel(rawProps) {
  const {
    title: titleProp,
    emptyText: emptyTextProp,
    showSummary: showSummaryProp,
    showSteps: showStepsProp,
    maxHeight,
    width,
    offsetTop,
    offsetLeft,
    dockBelowZoomControls,
    zoomControlsGapRem,
    collapsible: collapsibleProp,
    initiallyCollapsed,
    collapseDirection: collapseDirectionProp,
    position: positionProp,
  } = rawProps;

  const title = titleProp ?? "Directions";
  const emptyText = emptyTextProp ?? "Provide a route to see directions.";
  const showSummary = showSummaryProp ?? true;
  const showSteps = showStepsProp ?? true;
  const collapsible = collapsibleProp ?? true;
  const collapseDirection = collapseDirectionProp ?? "bottom";
  const position = positionProp ?? "top-left";

  const { navigation } = useMap();
  const [collapsed, setCollapsed] = useState(initiallyCollapsed ?? false);

  const style = {};
  if (width != null) {
    style.width = typeof width === "number" ? `${width}px` : width;
  }
  if (offsetTop != null) {
    style.top = typeof offsetTop === "number" ? `${offsetTop}px` : offsetTop;
  }
  if (offsetLeft != null) {
    style.left = typeof offsetLeft === "number" ? `${offsetLeft}px` : offsetLeft;
  }
  if (dockBelowZoomControls) {
    style.top = `calc(2.5rem + ${zoomControlsGapRem ?? 6}rem)`;
  }

  const positionClass = DIRECTIONS_POSITION_CLASSES[position] ?? "akm-controls-top-left";

  if (!navigation) {
    return (
      <div className={cn("akm-directions-panel", positionClass)} style={style}>
        <div className="akm-directions-header">
          <span className="akm-directions-title">{title}</span>
        </div>
        <div className="akm-directions-body">
          <div className="akm-directions-empty">{emptyText}</div>
        </div>
      </div>
    );
  }

  const {
    loading,
    error,
    routes,
    selectedIndex,
    setSelectedIndex,
    profiles,
    profile,
    setActiveProfile,
  } = navigation;
  const selected = routes[selectedIndex];

  return (
    <div className={cn("akm-directions-panel", positionClass)} style={style}>
      <div
        className="akm-directions-header"
        onClick={() => collapsible && setCollapsed((c) => !c)}
        style={{ cursor: collapsible ? "pointer" : "default" }}
      >
        <span className="akm-directions-title">{title}</span>
        {collapsible && (
          <span
            className={cn(
              "akm-directions-chevron",
              collapsed && "akm-directions-chevron-collapsed",
            )}
          >
            {collapseDirection === "top" ? "\u25B4" : "\u25BE"}
          </span>
        )}
      </div>

      {!collapsed && (
        <div
          className="akm-directions-body"
          style={{
            maxHeight:
              maxHeight != null
                ? typeof maxHeight === "number"
                  ? `${maxHeight}px`
                  : maxHeight
                : "320px",
          }}
        >
          {loading && <div className="akm-directions-loading">Loading route...</div>}
          {error && <div className="akm-directions-error">{error}</div>}

          {profiles && profiles.length > 1 && (
            <div className="akm-directions-profiles">
              {profiles.map((p) => (
                <button
                  key={p}
                  type="button"
                  className={cn(
                    "akm-directions-profile-btn",
                    p === profile && "akm-directions-profile-btn-active",
                  )}
                  onClick={() => setActiveProfile(p)}
                >
                  {p}
                </button>
              ))}
            </div>
          )}

          {routes.length > 1 && (
            <div className="akm-directions-alternatives">
              {routes.map((route, index) => (
                <button
                  key={index}
                  type="button"
                  className={cn(
                    "akm-directions-alt-btn",
                    index === selectedIndex && "akm-directions-alt-btn-active",
                  )}
                  onClick={() => setSelectedIndex(index)}
                >
                  {formatDuration(route.duration)} &middot; {formatDistance(route.distance)}
                </button>
              ))}
            </div>
          )}

          {showSummary && selected && (
            <div className="akm-directions-summary">
              <span>{formatDuration(selected.duration)}</span>
              <span className="akm-directions-summary-distance">
                {formatDistance(selected.distance)}
              </span>
            </div>
          )}

          {showSteps && selected?.steps?.length > 0 && (
            <ol className="akm-directions-steps">
              {selected.steps.map((step, index) => (
                <li key={index} className="akm-directions-step">
                  <span className="akm-directions-step-index">{index + 1}</span>
                  <span className="akm-directions-step-text">
                    {formatInstruction(step)}
                    {step.distance ? ` (${formatDistance(step.distance)})` : ""}
                  </span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}

export {
  Map,
  useMap,
  MapMarker,
  MarkerContent,
  MarkerPopup,
  MarkerTooltip,
  MarkerLabel,
  MapPopup,
  MapControls,
  MapRoute,
  MapArc,
  MapGeoJSON,
  MapClusterLayer,
  VoyagerMapLibreNavigation,
  VoyagerMapLibreDirectionsPanel,
};
