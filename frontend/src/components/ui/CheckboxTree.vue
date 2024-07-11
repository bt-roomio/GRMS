<template>
  <div>
    <TreeItem
        v-for="item in treeData"
        :key="item.id"
        :item="item"
        @toggle="handleToggle"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, ref } from 'vue';
import TreeItem from './TreeItem.vue';

interface TreeNode {
  id: number;
  label: string;
  checked: boolean;
  collapsed: boolean;
  children?: TreeNode[];
}

export default defineComponent({
  name: 'CheckboxTree',
  components: {
    TreeItem,
  },
  setup() {
    const treeData = ref<TreeNode[]>([
      {
        id: 1,
        label: 'Rooms',
        checked: false,
        collapsed: true,
        children: [
          { id: 2, label: 'Create', checked: false, collapsed: false },
          { id: 3, label: 'Read', checked: false, collapsed: false },
          { id: 4, label: 'Update', checked: false, collapsed: false },
          { id: 5, label: 'Delete', checked: false, collapsed: false },
        ],
      },
      {
        id: 6,
        label: 'Public Space',
        checked: false,
        collapsed: true,
        children: [
          { id: 7, label: 'Create', checked: false, collapsed: false },
          { id: 8, label: 'Read', checked: false, collapsed: false },
          { id: 9, label: 'Update', checked: false, collapsed: false },
          { id: 10, label: 'Delete', checked: false, collapsed: false },
        ],
      },
      {
        id: 11,
        label: 'Scenario',
        checked: false,
        collapsed: true,
        children: [
          { id: 12, label: 'Create', checked: false, collapsed: false },
          { id: 13, label: 'Read', checked: false, collapsed: false },
          { id: 14, label: 'Update', checked: false, collapsed: false },
          { id: 15, label: 'Delete', checked: false, collapsed: false },
        ],
      }
    ]);

    const handleToggle = ({id, checked}: {id: number, checked: boolean}) => {
      const toggleNode = (nodes: TreeNode[], id: number, checked: boolean) => {
        for (const node of nodes) {
          if (node.id === id) {
            node.checked = checked;
            if (node.children) {
              toggleChildren(node.children, checked);
            }
          }
          if (node.children) {
            toggleNode(node.children, id, checked);
          }
        }
      };

      const toggleChildren = (nodes: TreeNode[], checked: boolean) => {
        for (const node of nodes) {
          node.checked = checked;
          if (node.children) {
            toggleChildren(node.children, checked);
          }
        }
      };

      const updateParentState = (nodes: TreeNode[]) => {
        for (const node of nodes) {
          if (node.children) {
            node.checked = node.children.every(child => child.checked);
            updateParentState(node.children);
          }
        }
      };

      toggleNode(treeData.value, id, checked);
      updateParentState(treeData.value);
    };

    return {
      treeData,
      handleToggle,
    };
  },
});
</script>
