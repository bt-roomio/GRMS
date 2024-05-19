<template>
  <UiCheckbox v-model="isChecked" @change="checkboxHandle"/>
</template>
<script setup lang="ts">
import UiCheckbox from "@components/ui/Checkbox.vue";
import {computed} from "vue";

const model = defineModel<ICheckAll[]>()
const isChecked = computed({
  get: () => model.value?.every(value => value.select),
  set: (val) => val
})
const checkboxHandle = () => {
  model.value = model.value?.map(item => ({ ...item, select: !isChecked.value }))
}
</script>