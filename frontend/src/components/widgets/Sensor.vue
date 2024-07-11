<template>
  <div class="sensor">
    <div class="sensor__list">
      <SensorItem v-for="(item, key) in values.controls" :entity-id="values.ws_args?.entityId" :scope="values.ws_args?.scope" :key="key" :item="item" />
    </div>
  </div>
</template>
<script setup lang="ts">
import SensorItem from "@components/widgets/SensorItem.vue";
defineProps(['values'])
</script>