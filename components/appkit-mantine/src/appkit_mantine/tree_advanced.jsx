import React, { memo } from 'react';
import { Tree, Group, Text, Checkbox, useTree } from '@mantine/core';
import { SquarePlus, SquareMinus } from 'lucide-react';

function ExpandIcon({ hasChildren, expanded }) {
    if (!hasChildren) return <span style={{ width: 14 }} />;
    return expanded ? <SquareMinus size={14} /> : <SquarePlus size={14} />;
}

function renderCheckboxNode({ node, expanded, hasChildren, elementProps, tree }) {
    const checked = tree.isNodeChecked(node.value);
    const indeterminate = tree.isNodeIndeterminate(node.value);
    return (
        <Group wrap="nowrap" gap="xs" {...elementProps}>
            <Checkbox.Indicator
                size="xs"
                checked={checked}
                indeterminate={indeterminate}
                onClick={(event) => {
                    event.stopPropagation();
                    checked ? tree.uncheckNode(node.value) : tree.checkNode(node.value);
                }}
            />
            <ExpandIcon hasChildren={hasChildren} expanded={expanded} />
            <Text size="sm">{node.label}</Text>
        </Group>
    );
}

function renderCustomNode({ node, expanded, hasChildren, elementProps }) {
    return (
        <Group wrap="nowrap" gap="xs" {...elementProps}>
            <ExpandIcon hasChildren={hasChildren} expanded={expanded} />
            <Text size="sm">{node.label}</Text>
        </Group>
    );
}

export const EnhancedTree = memo(function EnhancedTree({
    search,
    withCheckbox,
    withCustomNode,
    multiple,
    initialSelectedState,
    initialCheckedState,
    initialExpandedState,
    checkStrictly,
    onSelect,
    onCheck,
    onExpand,
    onCollapse,
    ...props
}) {
    // The Tree controller owns selection/check state; its change callbacks are
    // the only way to observe them, so the wrapper always creates one.
    const tree = useTree({
        multiple,
        initialSelectedState,
        initialCheckedState,
        initialExpandedState,
        checkStrictly,
        onSelectedStateChange: onSelect,
        onCheckedStateChange: onCheck,
        onNodeExpand: onExpand,
        onNodeCollapse: onCollapse,
    });

    let renderNode = props.renderNode;
    if (withCheckbox) renderNode = renderCheckboxNode;
    else if (withCustomNode) renderNode = renderCustomNode;

    return <Tree tree={tree} {...props} renderNode={renderNode} />;
});
