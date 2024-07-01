<template>
  <div class="sensor">
    <ul>
      <li  v-for="(item, key) in values" :key="key">
        <UiSensorItem :unit="item.unit" :model-value="123.1237862187638" :precision="item.precision">{{ item.title || 'There should be a title here' }}</UiSensorItem>
      </li>
    </ul>
  </div>
</template>
<script setup lang="ts">
import UiSensorItem from "@components/ui/SensorItem.vue";
defineProps(['values'])
</script>