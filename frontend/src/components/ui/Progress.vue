<template>
  <div class="flex gap-3 items-center">
    <div class="ui-progress">
      <div :style="`width: ${value || 0}%; background:${color};`"></div>
    </div>
    {{value}}%
  </div>
</template>
<script setup lang="ts">
import {defineComponent} from "vue";
defineProps<{
  color: string,
  value: string
}>()
defineComponent({name: 'UiProgress'})
</script>