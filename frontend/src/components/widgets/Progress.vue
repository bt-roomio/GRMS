<template>
  <UiProgress
      :config="value" :value="getProgressValue(value.tag)"
  />
</template>
<script setup lang="ts">
import UiProgress from "@components/ui/Progress.vue";
import {useWS} from "@store/dashboard/ws";
import {storeToRefs} from "pinia";
const storeWs = useWS()
const {state} = storeToRefs(storeWs)
const props = defineProps(['value'])
const getProgressValue = (tag: string) => {
  const { entityId, scope } = props.value.ws_args || {};
  const eventKey = `${entityId}_${scope}`;
  return state.value.events?.get(eventKey)?.data?.[tag]?.[0]?.[1] || 0;
}
</script>