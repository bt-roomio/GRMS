<template>
  <UiInput
      label="Title*"
      name="title"
      v-model="state.title"
      placeholder="Write the title"
  />
  <UiInput
      label="Description"
      name="description"
      v-model="state.description"
      placeholder="Write the description"
  />
  <UiInput
      type="color"
      label="Choose a color"
      name="color"
      v-model="state.color"
      placeholder="Choose a color"
  />
</template>
<script setup lang="ts">
import UiInput from "@components/ui/Input.vue";
import {ref, watch} from "vue";
const emit = defineEmits(['input'])
const state = ref({
  title: "",
  description: "",
  color: "",
})

watch(state.value, value => {
  performState(value as any)
})

const performState = debounce(async (query: any) => {
  emit('input', query)
}, 500);
function debounce<T extends (...args: any[]) => void>(func: T, wait: number): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>): void => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}
</script>