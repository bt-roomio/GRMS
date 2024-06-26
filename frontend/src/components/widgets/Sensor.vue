<template>
  <div class="sensor">
    <ul>
      <li  v-for="(item, key) in values" :key="key">
        <UiSensorItem>{{ item.title || '&nbsp;' }}</UiSensorItem>
      </li>
    </ul>
  </div>
</template>
<script setup lang="ts">
import UiSensorItem from "@components/ui/SensorItem.vue";
defineProps(['values'])
</script>