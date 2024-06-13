<template>
  <round-slider
      class="ui-circular-input"
      v-model="value"
      :min="min"
      :max="max"
      step="0.1"
      rangeColor="#475467"
      :tooltipFormat="tooltipFormat"
      handleSize="24"
  />
</template>

<script setup lang="ts">
// @ts-ignore
import RoundSlider from 'vue-three-round-slider'
const value = defineModel()
const props = defineProps<{temperature_type: string, min: number, max: number}>()
const tooltipFormat = (e: any) => {
  return '<div class="label">MAX Temperature</div>' + e.value + props.temperature_type;
}
</script>
