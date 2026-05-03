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
      theme: {
        primaryColor: "alloqWarm",
        primaryShade: { light: 5, dark: 6 },
        colors: {
          alloqWarm: [
            "#fffef8",
            "#fbf8ed",
            "#f7efd1",
            "#f8eaa8",
            "#f6d94d",
            "#f1ca45",
            "#d99f18",
            "#a97811",
            "#6f4f0f",
            "#3e2d0b",
          ],
        },
      },
    },
    children
  );
}
