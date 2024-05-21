<template>
  <UiInput name="search" :placeholder="$t('dashboard.search')" v-model="searchQuery"/>
</template>
<script setup lang="ts">
import UiInput from "@components/ui/Input.vue";
import {defineComponent, ref, watch} from "vue";

const model = defineModel()
const searchQuery = ref<string>('');

const performSearch = debounce(async (query: string) => {
  model.value = query
}, 500);

watch(searchQuery, (newQuery) => {
    performSearch(newQuery);
})

function debounce<T extends (...args: any[]) => void>(func: T, wait: number): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>): void => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}
defineComponent({name: 'UiSearch'})
</script>