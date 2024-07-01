<template>
  <div class="slider">
    <UiSliderItem v-for="(item, key) in values" :key="key" :args="{min: item.min, max: item.max}">{{ item.title || 'There should be a title here' }}</UiSliderItem>
  </div>
</template>
<script setup lang="ts">
import UiSliderItem from "@components/ui/SlliderItem.vue";
defineProps(['values'])
</script>