<template>
  <CheckboxTree v-if="data" v-model="data"/>
</template>
<script setup lang="ts">
import CheckboxTree from "@components/ui/CheckboxTree.vue";
import {onMounted, ref, watch} from "vue";
const model = defineModel<any[]>()
const data = ref<TreeNode[]>([])
const props = defineProps(['options'])
onMounted(() => {
  data.value = transformPermissionsToTreeData(props.options, model.value || [])
})
interface IConfigurationPermissions {
  id: number;
  name: string;
  codename: string;
  content_type: number;
}

interface TreeNode {
  key: number
  id: number | undefined;
  label: string;
  checked: boolean;
  collapsed: boolean;
  children?: TreeNode[];
}
function transformPermissionsToTreeData(permissions: { name: string, permissions: IConfigurationPermissions[] }[], model: any[]): TreeNode[] {
  let key = 0;
  const actionMap: { [key: string]: string } = {
    add: 'Create',
    change: 'Update',
    delete: 'Delete',
    view: 'Read'
  };

  return permissions.map((group) => {
    const children = group.permissions.map(permission => {
      const match = permission.name.match(/Can (add|change|delete|view) (.+)/);
      const action = match ? actionMap[match[1]] : permission.name;
      const isChecked = !!model.find(el => el.id === permission.id)
      return {
        key: key++,
        id: permission.id,
        label: action,
        checked: isChecked,
        collapsed: false
      };
    });

    return {
      id: undefined,
      key: key++,
      label: group.name,
      checked: children.every(child => child.checked),
      collapsed: !children.find(child => child.checked),
      children
    };
  });
}

watch(data, async value => {
  let arrayNew: any = []
  value?.map(el => arrayNew = [...arrayNew, ...(el.children || [])])
  model.value = arrayNew.filter((el: TreeNode) => el.checked).map((el: TreeNode) => el.id)
}, {deep: true})
</script>