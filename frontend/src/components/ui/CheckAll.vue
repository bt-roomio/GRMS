<template>
  <UiCheckbox v-model="isChecked" @change="checkboxHandle"/>
</template>
<script setup lang="ts">
import UiCheckbox from "@components/ui/Checkbox.vue";
import {computed, ref, watch} from "vue";

const model = defineModel<ICheckAll[]>()
const isChecked = ref(false)

const checkAllChecked = computed(() => model.value?.every(value => value.select))

watch(checkAllChecked, value => isChecked.value = value as boolean)
const checkboxHandle = () => {
  model.value = model.value?.map(item => ({ ...item, select: isChecked.value }))
}
</script>