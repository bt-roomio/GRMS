<template>
  <round-slider
      ref="roundSliderRef"
      class="ui-circular-input"
      v-model="value"
      :min="min"
      :max="max"
      step="1"
      rangeColor="#475467"
      :tooltipFormat="tooltipFormat"
      handleSize="24"
      :diameter="200"
      :change="changeRoundSlider"
  />
</template>

<script setup lang="ts">
// @ts-ignore
import RoundSlider from 'vue-three-round-slider'
import {nextTick, ref, watch} from "vue";
const emits = defineEmits(['change'])
const value = defineModel()
const props = defineProps<{temperature_type: string, min: number, max: number}>()
const roundSliderRef = ref()

watch(props,() => {
  if (roundSliderRef.value) {
    const oldValue = JSON.parse(JSON.stringify(value.value))
    value.value = 0
    nextTick(() => {
      value.value = oldValue
    })
  }
});
const tooltipFormat = (e: any) => {
  return `<div class="label">MAX Temperature</div>${e.value}${props.temperature_type}`;
}
const changeRoundSlider = (e: any) => {
  emits('change', e)
}
</script>