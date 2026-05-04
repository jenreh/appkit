import { createElement, useContext } from "react";
import { MantineProvider as MantineCoreProvider } from "@mantine/core";
import { ColorModeContext } from "$/utils/context";

// Forwards every supported MantineProvider prop, while keeping the
// color-scheme synced with Reflex's color mode unless the caller passes an
// explicit forceColorScheme value.
export default function MantineProvider({
  children,
  theme,
  defaultColorScheme,
  forceColorScheme,
  cssVariablesSelector,
  withCssVariables,
  deduplicateCssVariables,
  deduplicateInlineStyles,
  classNamesPrefix,
  withStaticClasses,
  withGlobalClasses,
}) {
  const { resolvedColorMode } = useContext(ColorModeContext) || {};
  const resolvedForceScheme = forceColorScheme ?? resolvedColorMode ?? "light";

  const props = { forceColorScheme: resolvedForceScheme };
  if (theme !== undefined) props.theme = theme;
  if (defaultColorScheme !== undefined) props.defaultColorScheme = defaultColorScheme;
  if (cssVariablesSelector !== undefined) props.cssVariablesSelector = cssVariablesSelector;
  if (withCssVariables !== undefined) props.withCssVariables = withCssVariables;
  if (deduplicateCssVariables !== undefined) props.deduplicateCssVariables = deduplicateCssVariables;
  if (deduplicateInlineStyles !== undefined) props.deduplicateInlineStyles = deduplicateInlineStyles;
  if (classNamesPrefix !== undefined) props.classNamesPrefix = classNamesPrefix;
  if (withStaticClasses !== undefined) props.withStaticClasses = withStaticClasses;
  if (withGlobalClasses !== undefined) props.withGlobalClasses = withGlobalClasses;

  return createElement(MantineCoreProvider, props, children);
}
