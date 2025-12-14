import '@mantine/core/styles.css';
import '@mantine/tiptap/styles.css';

import { createElement, memo, useEffect } from 'react';
import { useEditor } from '@tiptap/react';
import {
  RichTextEditor as MantineRichTextEditor,
  Link
} from '@mantine/tiptap';
import StarterKit from '@tiptap/starter-kit';
import Highlight from '@tiptap/extension-highlight';
import TextAlign from '@tiptap/extension-text-align';
import Subscript from '@tiptap/extension-subscript';
import Superscript from '@tiptap/extension-superscript';
import { Color } from '@tiptap/extension-color';
import TextStyle from '@tiptap/extension-text-style';
import Placeholder from '@tiptap/extension-placeholder';
import Image from "@tiptap/extension-image";


export const RichTextEditorWrapper = memo(function Wrapper(props) {
  // Destructure and filter out toolbar-related props
  const {
    content = '',
    onUpdate,
    editable = true,
    placeholder = '',
    variant,
    withTypographyStyles,
    labels,
    // NEW: Styles and classNames for Mantine Styles API
    styles,
    classNames,
    // Toolbar configuration props
    controlGroups,
    showToolbar,
    sticky,
    stickyOffset,
    // Legacy/snake_case variants to filter out
    control_groups,
    show_toolbar,
    sticky_offset,
    toolbar_config, // Old dict-based approach
    toolbarConfig,   // Old dict-based approach
    ...restProps
  } = props;
  const editor = useEditor({
    extensions: [
      StarterKit.configure({ link: false }),
      Link,
      Highlight,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Subscript,
      Superscript,
      TextStyle,
      Color,
      Image.configure({
        inline: true,
        allowBase64: true,
        HTMLAttributes: {
          class: 'tiptap-image',
        },
      }),
      ...(placeholder ? [Placeholder.configure({ placeholder })] : []),
    ],
    content: content,
    editable: editable,
    onUpdate: ({ editor }) => {
      if (onUpdate) {
        onUpdate(editor.getHTML());
      }
    },
  });

  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content);
    }
  }, [content, editor]);

  useEffect(() => {
    if (editor) {
      editor.setEditable(editable);
    }
  }, [editable, editor]);

  if (!editor) {
    return null;
  }

  // Control name to component mapping
  const controlMap = {
    bold: MantineRichTextEditor.Bold,
    italic: MantineRichTextEditor.Italic,
    underline: MantineRichTextEditor.Underline,
    strikethrough: MantineRichTextEditor.Strikethrough,
    clearFormatting: MantineRichTextEditor.ClearFormatting,
    code: MantineRichTextEditor.Code,
    highlight: MantineRichTextEditor.Highlight,
    h1: MantineRichTextEditor.H1,
    h2: MantineRichTextEditor.H2,
    h3: MantineRichTextEditor.H3,
    h4: MantineRichTextEditor.H4,
    blockquote: MantineRichTextEditor.Blockquote,
    hr: MantineRichTextEditor.Hr,
    bulletList: MantineRichTextEditor.BulletList,
    orderedList: MantineRichTextEditor.OrderedList,
    subscript: MantineRichTextEditor.Subscript,
    superscript: MantineRichTextEditor.Superscript,
    link: MantineRichTextEditor.Link,
    unlink: MantineRichTextEditor.Unlink,
    alignLeft: MantineRichTextEditor.AlignLeft,
    alignCenter: MantineRichTextEditor.AlignCenter,
    alignRight: MantineRichTextEditor.AlignRight,
    alignJustify: MantineRichTextEditor.AlignJustify,
    undo: MantineRichTextEditor.Undo,
    redo: MantineRichTextEditor.Redo,
    // image is handled specially (custom control)
    // colorPicker is handled specially (needs colors prop)
    // color is handled specially (needs color prop)
    unsetColor: MantineRichTextEditor.UnsetColor,
  };

  // Default toolbar configuration
  const defaultControlGroups = [
    ['bold', 'italic', 'underline', 'strikethrough', 'clearFormatting', 'code', 'highlight'],
    ['h1', 'h2', 'h3', 'h4'],
    ['blockquote', 'hr', 'bulletList', 'orderedList', 'subscript', 'superscript'],
    ['link', 'unlink'],
    ['alignLeft', 'alignCenter', 'alignRight', 'alignJustify'],
    ['undo', 'redo'],
  ];

  // Use camelCase version, fallback to snake_case if needed
  const config = toolbarConfig || toolbar_config;

  // Debug logging
  if (typeof window !== 'undefined') {
    console.log('[RichTextEditorWrapper] Received props:', {
      controlGroups,
      showToolbar,
      sticky,
      stickyOffset,
      editable,
      placeholder,
      variant,
      styles,
      classNames
    });
  }

  // Use destructured props with defaults
  const finalControlGroups = controlGroups || defaultControlGroups;
  const finalShowToolbar = showToolbar !== false;
  const finalSticky = sticky !== false;
  const finalStickyOffset = stickyOffset || '0px';

  // Build toolbar controls
  const toolbarContent = finalShowToolbar ? createElement(
    MantineRichTextEditor.Toolbar,
    { sticky: finalSticky, stickyOffset: finalStickyOffset },
    ...finalControlGroups.map((group, groupIndex) =>
      createElement(
        MantineRichTextEditor.ControlsGroup,
        { key: groupIndex },
        ...group.map((controlName, controlIndex) => {
          // Handle special controls that need props
          if (controlName === 'colorPicker') {
            return createElement(MantineRichTextEditor.ColorPicker, {
              key: `${groupIndex}-${controlIndex}`,
              colors: [
                '#25262b', '#868e96', '#fa5252', '#e64980',
                '#be4bdb', '#7950f2', '#4c6ef5', '#228be6',
                '#15aabf', '#12b886', '#40c057', '#82c91e',
                '#fab005', '#fd7e14',
              ]
            });
          }

          // Handle image control
          if (controlName === 'image') {
            return createElement(MantineRichTextEditor.Control, {
              key: `${groupIndex}-${controlIndex}`,
              onClick: () => {
                const url = window.prompt('Enter image URL:');
                if (url) {
                  editor.chain().focus().setImage({ src: url }).run();
                }
              },
              'aria-label': 'Insert image',
              title: 'Insert image',
            }, '🖼️');
          }

          // For regular controls, use the control map
          const ControlComponent = controlMap[controlName];
          return ControlComponent
            ? createElement(ControlComponent, { key: `${groupIndex}-${controlIndex}` })
            : null;
        }).filter(Boolean)
      )
    )
  ) : null;

  // NEW: Build mantine props with styles and classNames
  // Merge user styles with default overflow handling for content
  const mergedStyles = {
    ...styles,
    content: {
      ...(styles?.content || {}),
      overflow: 'auto',
    },
  };

  const mantineProps = {
    editor: editor,
    variant: variant,
    withTypographyStyles: withTypographyStyles,
    labels: labels,
    styles: mergedStyles,
    ...restProps,
  };

  // Add classNames if provided
  if (classNames) {
    mantineProps.classNames = classNames;
  }

  return createElement(
    MantineRichTextEditor,
    mantineProps,
    toolbarContent,
    createElement(MantineRichTextEditor.Content, null)
  );
});

export default RichTextEditorWrapper;
