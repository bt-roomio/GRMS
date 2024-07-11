<template>
  <div class="sensor__item">
    <UiSensorItem :unit="item.unit" :model-value="wsValue" :precision="item.precision">{{ item.title || $t('dashboard.widget.form.title_empty') }}</UiSensorItem>
  </div>
</template>
<script setup lang="ts">
import UiSensorItem from "@components/ui/SensorItem.vue";
import {useWS} from "@store/dashboard/ws";
import {storeToRefs} from "pinia";
import {computed} from "vue";
const props = defineProps(['item', 'entityId', 'scope'])
const storeWs = useWS()
const {state} = storeToRefs(storeWs)
const wsValue = computed(() => {
  if (props.item.tag && props.entityId && state.value.events.get(props.entityId + '_' + props.scope)?.data[props.item.tag]){
    return state.value.events.get(props.entityId + '_' + props.scope).data[props.item.tag][0][1]
  }else {
    return 0
  }
})
</script>