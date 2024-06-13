<template>
  <div class="sensor">
    <ul>
      <li>
        <UiSensorItem>Room sensor</UiSensorItem>
      </li>
      <li>
        <UiSensorItem>M sensor</UiSensorItem>
      </li>
      <li>
        <UiSensorItem>WS sensor</UiSensorItem>
      </li>
      <li>
        <UiSensorItem>Bath alarm</UiSensorItem>
      </li>
    </ul>
  </div>
</template>
<script setup lang="ts">
import UiSensorItem from "@components/ui/SensorItem.vue";
</script>