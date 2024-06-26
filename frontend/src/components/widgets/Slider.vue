<template>
  <div class="sensor">
    <ul>
      <li  v-for="(item, key) in values" :key="key">
        <UiSliderItem :args="{min: item.min, max: item.max}">{{ item.title || '&nbsp;' }}</UiSliderItem>
      </li>
    </ul>
  </div>
</template>
<script setup lang="ts">
import UiSliderItem from "@components/ui/SlliderItem.vue";
defineProps(['values'])
</script>