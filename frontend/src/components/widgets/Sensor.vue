<template>
  <div class="sensor">
    <div class="sensor__list">
      <SensorItem v-for="(item, key) in values.controls" :entity-id="storeConfigurationDashboard.getAliasIsEqual(values.ws_args)" :scope="values.ws_args?.scope" :key="key" :item="item" />
    </div>
  </div>
</template>
<script setup lang="ts">
import SensorItem from "@components/widgets/SensorItem.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
defineProps(['values'])
const storeConfigurationDashboard = useConfigurationDashboardStore()
</script>