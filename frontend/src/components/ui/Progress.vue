<template>
  <div class="flex gap-3 items-center">
    <div class="ui-progress">
      <div :style="`width: ${getValue >= 100 ? 100 : (getValue || 0)}%; background:${value.color};`"></div>
    </div>
    <p class="ui-progress__value">
      {{progressValue}} {{ value.unit !== 'Custom Units' ? units[value.unit as string] : value.unit_value }}
    </p>
  </div>
</template>
<script setup lang="ts">
import {computed, defineComponent, ref} from "vue";
const props = defineProps<{
  value: any
}>()
const progressValue = ref(34)
const units = {
  "Percent": '%',
  "Bytes": 'B',
  "Kilobytes": 'KB',
  "Megabytes": 'MB',
  "Gigabytes": 'GB',
  "Time (seconds)": 's',
  "Time (minutes)": 'min',
  "Time (hours)": 'h',
} as {[key: string]: any}
const getValue = computed(() => {
  return ((progressValue.value - props.value.min) / (props.value.max - props.value.min)) * 100;
})

defineComponent({name: 'UiProgress'})
</script>