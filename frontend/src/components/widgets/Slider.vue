<template>
  <div class="slider__wrap">
    <div class="slider">
      <UiSliderItem
          v-for="(item, key) in values.controls"
          :key="key"
          :index="key"
          :args="{min: item.min, max: item.max}"
          :model-value="getSliderValue(item.tag)"
          @change="changeSlider($event, item.tag)"
      >
        {{ item.title || $t('dashboard.widget.form.title_empty') }}
      </UiSliderItem>
    </div>
  </div>
</template>
<script setup lang="ts">
import UiSliderItem from "@components/ui/SlliderItem.vue";
import {useWS} from "@store/dashboard/ws";
import {storeToRefs} from "pinia";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
const storeConfigurationDashboard = useConfigurationDashboardStore()
const storeConfigurationDevice = useConfigurationDeviceStore()
const storeWs = useWS()
const {state} = storeToRefs(storeWs)
const props = defineProps(['values'])
const getSliderValue = (tag: string) => {
  const entityId = storeConfigurationDashboard.getAliasIsEqual(props.values.ws_args)
  const { scope } = props.values.ws_args || {};
  const eventKey = `${entityId}_${scope}`;
  return state.value.events?.get(eventKey)?.data?.[tag]?.[0]?.[1] || 0;
}

const changeSlider = async (value: any, tag: string) => {
  const entityId = storeConfigurationDashboard.getAliasIsEqual(props.values.ws_args)
  const { scope } = props.values.ws_args || {};
  if (entityId && scope) {
    let obj: any = {};
    obj[tag] = value;
    await storeConfigurationDevice.setAttr(entityId, scope, obj);
  }
}
</script>