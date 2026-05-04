import React, { memo } from 'react';
import { Tree, Group, Text } from '@mantine/core';
import { SquarePlus, SquareMinus } from 'lucide-react';

export const EnhancedTree = memo(function EnhancedTree({ search, withCheckbox, withCustomNode, ...props }) {
    // If not using custom nodes, render normal Mantine tree
    if (!withCustomNode) {
        return <Tree {...props} />;
    }

    return (
        <Tree
            {...props}
            renderNode={({ node, expanded, hasChildren, elementProps }) => (
                <Group wrap="nowrap" gap="xs" {...elementProps}>
                    {hasChildren && (
                        expanded ? <SquareMinus size={14} /> : <SquarePlus size={14} />
                    )}
                    {!hasChildren && <span style={{ width: 14 }} />}
                    <Text size="sm">{node.label}</Text>
                </Group>
            )}
        />
    );
});
