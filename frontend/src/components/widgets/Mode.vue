<template>
  <div class="mode">
    <ul>
      <li v-for="(item, key) in values.controls" :key="key">
        {{ item.title || $t('dashboard.widget.form.title_empty') }}
        <UiToggle
            :model-value="getToggleValue(item.tag)"
            @change="changeMode($event, item.tag)"
        />
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import UiToggle from "@components/ui/Toggle.vue";
import {useWS} from "@store/dashboard/ws";
import {storeToRefs} from "pinia";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
const storeWs = useWS()
const {state} = storeToRefs(storeWs)
const storeConfigurationDevice = useConfigurationDeviceStore()
const props = defineProps(['values'])

const getToggleValue = (tag: string) => {
  const { entityId, scope } = props.values.ws_args || {};
  const eventKey = `${entityId}_${scope}`;
  return state.value.events?.get(eventKey)?.data?.[tag]?.[0]?.[1] || false;
}

const changeMode = async (e: any, tag: string) => {
  const { entityId, scope } = props.values.ws_args || {};
  if (entityId && scope) {
    let obj: any = {};
    obj[tag] = e.target.checked;
    await storeConfigurationDevice.setAttr(entityId, scope, obj);
  }
}
</script>
