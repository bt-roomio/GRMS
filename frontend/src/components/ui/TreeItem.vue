<template>
  <div>
    <div class="flex">
      <UiCheckbox v-model="item.checked" @change="toggle(item.checked)">{{ item.label }}</UiCheckbox>
      <UiIcon class="stroke-primary-600" :class="{'-rotate-90': item.collapsed}" @click="toggleCollapse" v-if="item.children" style="cursor: pointer;" name="chevron-down" filled />
    </div>
    <div v-if="item.children && !item.collapsed" style="margin-left: 20px;">
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
  id: number;
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
      emit('toggle', {id: props.item.id, checked:value});
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
