/**
 * MantineAlertDialog — a Radix-style compound AlertDialog built on Mantine Modal.
 *
 * Provides the same compound API as @radix-ui/react-alert-dialog so existing
 * Reflex code using rx.alert_dialog.* can be migrated to mn.alert_dialog.*
 * with minimal changes:
 *
 *   Root        – context provider; holds open state (controlled or uncontrolled)
 *   Trigger     – wraps any child; opens dialog on click
 *   Content     – Modal.Content (renders overlay + modal shell)
 *   Title       – Modal.Title (sticky header slot)
 *   Description – body content slot
 *   Cancel      – closes the dialog on click; default "Abbrechen" variant
 *   Action      – fires onAction callback and closes; default "Löschen" variant
 *
 * Usage (Reflex / Python side):
 *   mn.alert_dialog.root(
 *       mn.alert_dialog.trigger(mn.action_icon(rx.icon("trash-2"))),
 *       mn.alert_dialog.content(
 *           mn.alert_dialog.title("Bestätigung"),
 *           mn.alert_dialog.description("Wirklich löschen?"),
 *           mn.alert_dialog.cancel(),
 *           mn.alert_dialog.action(on_action=State.delete_item),
 *       ),
 *   )
 */

import '@mantine/core/styles.css';

import {
  createElement,
  createContext,
  useContext,
  useState,
} from 'react';
import {
  Modal,
  Button,
  Group,
  Text,
  Title,
} from '@mantine/core';

// ─── Context ────────────────────────────────────────────────────────────────

const AlertDialogContext = createContext(null);

function useAlertDialog() {
  const ctx = useContext(AlertDialogContext);
  if (!ctx) {
    throw new Error('AlertDialog compound component used outside of AlertDialogRoot');
  }
  return ctx;
}

// ─── Root ────────────────────────────────────────────────────────────────────

/**
 * Context provider. Supports both controlled (open + onOpenChange) and
 * uncontrolled (internal state) modes.
 */
export function AlertDialogRoot({
  children,
  open,           // controlled open state
  onOpenChange,   // controlled change callback
  defaultOpen = false,
  size = 'sm',
}) {
  const [internalOpen, setInternalOpen] = useState(defaultOpen);
  const isControlled = open !== undefined && open !== null;
  const isOpen = isControlled ? !!open : internalOpen;

  const setOpen = (value) => {
    if (!isControlled) {
      setInternalOpen(value);
    }
    onOpenChange?.(value);
  };

  return createElement(
    AlertDialogContext.Provider,
    { value: { isOpen, setOpen, size } },
    children,
  );
}

// ─── Trigger ─────────────────────────────────────────────────────────────────

/**
 * Wraps any child element and opens the dialog when clicked.
 * Uses a transparent <span display:contents> wrapper to preserve layout.
 */
export function AlertDialogTrigger({ children }) {
  const { setOpen } = useAlertDialog();
  return createElement(
    'span',
    {
      style: { display: 'contents' },
      onClick: (e) => {
        e.stopPropagation();
        setOpen(true);
      },
    },
    children,
  );
}

// ─── Content ─────────────────────────────────────────────────────────────────

/**
 * The modal shell. Renders Modal.Root + Modal.Overlay + Modal.Content.
 * All Modal props can be forwarded via ...rest.
 */
export function AlertDialogContent({
  children,
  centered = true,
  ...rest
}) {
  const { isOpen, setOpen, size } = useAlertDialog();

  return createElement(
    Modal.Root,
    {
      opened: isOpen,
      onClose: () => setOpen(false),
      centered,
      size,
      ...rest,
    },
    createElement(Modal.Overlay, { backgroundOpacity: 0.5, blur: 3 }),
    createElement(Modal.Content, null, children),
  );
}

// ─── Title ───────────────────────────────────────────────────────────────────

/**
 * Renders inside a Modal.Header with a close button.
 * Accepts plain text children or a component.
 */
export function AlertDialogTitle({ children, style, className, ...rest }) {
  const { setOpen } = useAlertDialog();
  return createElement(
    Modal.Header,
    { style, className, ...rest },
    createElement(Modal.Title, null, children),
    createElement(Modal.CloseButton, { onClick: () => setOpen(false) }),
  );
}

// ─── Description ─────────────────────────────────────────────────────────────

/**
 * Renders the body content inside Modal.Body.
 */
export function AlertDialogDescription({ children, style, className, ...rest }) {
  return createElement(Modal.Body, { style, className, ...rest }, children);
}

// ─── Cancel ──────────────────────────────────────────────────────────────────

/**
 * Closes the dialog. Renders a Mantine Button with variant="default" by default.
 * Any children override the default label.
 */
export function AlertDialogCancel({
  children,
  variant = 'default',
  onCancel,
  ...rest
}) {
  const { setOpen } = useAlertDialog();
  return createElement(
    Button,
    {
      variant,
      onClick: (e) => {
        e.stopPropagation();
        onCancel?.();
        setOpen(false);
      },
      ...rest,
    },
    children ?? 'Abbrechen',
  );
}

// ─── Action ──────────────────────────────────────────────────────────────────

/**
 * Fires onAction then closes the dialog.
 * Renders a Mantine Button with color="red" by default.
 * Any children override the default label.
 */
export function AlertDialogAction({
  children,
  color = 'red',
  variant = 'filled',
  onAction,
  loading = false,
  closeOnAction = true,
  ...rest
}) {
  const { setOpen } = useAlertDialog();
  return createElement(
    Button,
    {
      color,
      variant,
      loading,
      onClick: (e) => {
        e.stopPropagation();
        onAction?.();
        if (closeOnAction) {
          setOpen(false);
        }
      },
      ...rest,
    },
    children ?? 'Löschen',
  );
}

// ─── Footer ──────────────────────────────────────────────────────────────────

/**
 * Convenience wrapper that renders Cancel + Action in a justified Group.
 * Props: cancelLabel, actionLabel, onCancel, onAction, actionLoading,
 *        cancelProps, actionProps.
 */
export function AlertDialogFooter({
  cancelLabel = 'Abbrechen',
  actionLabel = 'Löschen',
  onCancel,
  onAction,
  actionLoading = false,
  cancelProps = {},
  actionProps = {},
  style,
  className,
  ...rest
}) {
  const { setOpen } = useAlertDialog();
  return createElement(
    Group,
    {
      justify: 'flex-end',
      style: {
        padding: 'var(--mantine-spacing-md)',
        borderTop: '1px solid var(--mantine-color-default-border)',
        ...style,
      },
      className,
      ...rest,
    },
    createElement(
      AlertDialogCancel,
      { onCancel, ...cancelProps },
      cancelLabel,
    ),
    createElement(
      AlertDialogAction,
      { onAction, loading: actionLoading, ...actionProps },
      actionLabel,
    ),
  );
}
