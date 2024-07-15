<template>
  <div class="ui_status" :class="status.toLocaleLowerCase()">{{status}}</div>
</template>

<script setup lang="ts">
defineProps<{
  status: string
}>()
defineOptions({
  name: 'UiStatus',
  inheritAttrs: true
})
</script>