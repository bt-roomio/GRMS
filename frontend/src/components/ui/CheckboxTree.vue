<template>
  <div class="flex justify-between border p-3 rounded-lg">
    <UiCheckbox v-model="checkAll" @change="handleToggleAll(model)">{{ $t('dashboard.configuration.roles.form.checked_all') }}</UiCheckbox>
  </div>
  <div>
    <TreeItem
        v-for="item in model"
        :key="item.key"
        :item="item"
        @toggle="handleToggle"
    />
  </div>
</template>

<script setup lang="ts">
import {defineComponent, ref} from 'vue';
import TreeItem from './TreeItem.vue';
import UiCheckbox from "@components/ui/Checkbox.vue";
const checkAll = ref(false)
interface TreeNode {
  key: number;
  id: number | undefined;
  label: string;
  checked: boolean;
  collapsed: boolean;
  children?: TreeNode[];
}
const model = defineModel<TreeNode[]>({default: []})
const handleToggleAll = (nodes: TreeNode[]) => {
  for (const node of nodes) {
      node.checked = checkAll.value;
      handleToggleAll(node.children || []);
  }
}
const handleToggle = ({id, checked}: {id: number, checked: boolean}) => {
  const toggleNode = (nodes: TreeNode[], id: number, checked: boolean) => {
    for (const node of nodes) {
      if (node.key === id) {
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
  const checkCheckedAll = (nodes: TreeNode[]) => {
    checkAll.value = nodes.every(child => child.checked)
  };


  toggleNode(model.value, id, checked);
  updateParentState(model.value);
  checkCheckedAll(model.value);
};

defineComponent({
  name: 'CheckboxTree'
});
</script>
