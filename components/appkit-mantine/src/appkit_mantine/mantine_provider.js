import { createElement, useContext } from "react";
import { MantineProvider as MantineCoreProvider } from "@mantine/core";
import { ColorModeContext } from "$/utils/context";

export default function MantineProvider({ children }) {
  const { resolvedColorMode } = useContext(ColorModeContext) || {};

  const mode = resolvedColorMode ?? "light";

  return createElement(
    MantineCoreProvider,
    {
      forceColorScheme: mode,
    },
    children
  );
}
