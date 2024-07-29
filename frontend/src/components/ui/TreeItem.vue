<template>
  <div>
    <div class=" flex justify-between" :class="{'border border-gray-200 dark:border-gray-500 p-3 rounded-lg mb-3': item.children?.length}">
      <UiCheckbox v-model="item.checked" @change="toggle(item.checked)">{{ item.label }}</UiCheckbox>
      <UiIcon class="stroke-primary-600 border-gray-200 dark:border-gray-500 dark:stroke-gray-300 w-12 h-12 -m-3 p-3.5" :class="{'-rotate-90 border-t': item.collapsed, 'border-l': !item.collapsed}" @click="toggleCollapse" v-if="item.children" style="cursor: pointer;" name="chevron-down" filled />
    </div>
    <div v-if="item.children && !item.collapsed" class="grid grid-cols-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-500 p-3 rounded-lg gap-3 mb-3">
      <TreeItem
          v-for="child in item.children"
          :key="child.id"
          :item="child"
          @toggle="$emit('toggle', $event)"
      />
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from 'vue';
import UiCheckbox from "@components/ui/Checkbox.vue";
import UiIcon from "@components/ui/Icon.vue";

interface TreeNode {
  key: number;
  id: number | undefined;
  label: string;
  checked: boolean;
  collapsed: boolean;
  children?: TreeNode[];
}

export default defineComponent({
  name: 'TreeItem',
  components: {UiIcon, UiCheckbox},
  props: {
    item: {
      type: Object as PropType<TreeNode>,
      required: true,
    },
  },
  emits: ['toggle'],
  setup(props, { emit }) {
    const toggle = (value: Boolean) => {
      emit('toggle', {id: props.item.key, checked:value});
    };
    const toggleCollapse = () => {
      props.item.collapsed = !props.item.collapsed;
    };

    return {
      toggle,
      toggleCollapse
    };
  },
});
</script>
