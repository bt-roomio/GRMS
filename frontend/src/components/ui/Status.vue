<template>
  <div class="ui_status" :class="status.toLocaleLowerCase()">{{status}}</div>
</template>

<script setup lang="ts">
import {defineComponent} from "vue";

defineProps<{
  status: string
}>()

defineComponent({name: 'UiStatus'})
</script>