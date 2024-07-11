<template>
  <div class="flex gap-3 items-center">
    <div class="ui-progress" v-if="getValue !== 'not-number'">
      <div :style="`width: ${getValue >= 100 ? 100 : (getValue || 0)}%; background:${config.color};`"></div>
    </div>
    <div class="ui-progress" v-else>
      <div :style="`width: 0%; background:${config.color};`"></div>
    </div>
    <p class="ui-progress__value">
      {{value}} {{ config.unit !== 'Custom Units' ? units[config.unit as string] : config.unit_value }}
    </p>
  </div>
</template>
<script setup lang="ts">
import {computed, defineComponent} from "vue";
const props = defineProps<{
  config: any
  value: any
}>()
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
  if (typeof props.value === 'number') {
    return ((props.value - props.config.min) / (props.config.max - props.config.min)) * 100;
  }else {
    return 'not-number'
  }

})

defineComponent({name: 'UiProgress'})
</script>