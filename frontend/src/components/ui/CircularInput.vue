<template>
  <round-slider
      ref="roundSliderRef"
      class="ui-circular-input"
      v-model="value"
      :min="min"
      :max="max"
      step="0.5"
      rangeColor="#475467"
      :tooltipFormat="tooltipFormat"
      handleSize="24"
      :diameter="200"
  />
</template>

<script setup lang="ts">
// @ts-ignore
import RoundSlider from 'vue-three-round-slider'
import {ref, watch} from "vue";
const value = defineModel()
const props = defineProps<{temperature_type: string, min: number, max: number}>()
const roundSliderRef = ref()

watch(props,() => {
  if (roundSliderRef.value) {
    roundSliderRef.value.updateProp('model-value', parseInt(<string>value.value))
  }
});
const tooltipFormat = (e: any) => {
  return `<div class="label">MAX Temperature</div>${e.value}${props.temperature_type}`;
}
</script>