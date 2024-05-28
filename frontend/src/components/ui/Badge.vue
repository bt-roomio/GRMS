<template>
  <div class="ui_badge">{{text}}</div>
</template>

<script setup lang="ts">
import {defineComponent} from "vue";

defineProps<{
  text: string
}>()

defineComponent({name: 'UiBadge'})
</script>