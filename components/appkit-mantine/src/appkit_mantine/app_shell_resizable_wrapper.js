import '@mantine/core/styles.css';

import { createElement, memo } from 'react';
import { AppShell, useAppShellResize } from '@mantine/core';

// Calls the `useAppShellResize` hook (Mantine 9.7) and hands the controller to
// AppShell, so Reflex can enable resizing with plain props.
export const AppShellResizable = memo(function AppShellResizable(props) {
  const {
    resizeOptions,
    initialSizes,
    onResize,
    onResizeEnd,
    onCollapseChange,
    children,
    ...rest
  } = props;

  const resize = useAppShellResize({
    ...(resizeOptions || {}),
    initialSizes,
    onResize,
    onResizeEnd,
    onCollapseChange,
  });

  return createElement(AppShell, { resize, ...rest }, children);
});

export default AppShellResizable;
