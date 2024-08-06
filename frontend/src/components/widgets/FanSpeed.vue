<template>
  <div class="fan-speed">
    <div class="fan-speed__tablet">
      <div class="fan-speed__control" :class="{disabled: getRangeValue(value.tag) === value.min}">
        <UiIcon name="minus-circle-control" filled @click.prevent="minus"/>
      </div>
      <div class="fan-speed__dashboard">
        <UiCircularInput
            :model-value="getRangeValue(value.tag)"
            :temperature_type="units[value.unit]"
            :min="value.min"
            :max="value.max"
            @change="setRangeValue($event, value.tag)"
        />
      </div>
      <div class="fan-speed__control" :class="{disabled: getRangeValue(value.tag) === value.max}">
        <UiIcon name="plus-circle-control" filled @click.prevent="plus"/>
      </div>
    </div>
    <div class="fan-speed__buttons"
         :class="{'col-2': value.controls_type !== 'line'}"
         v-if="value.controls.length && value.fan_tag"
    >
      <UiButton
          v-for="item in value.controls"
          :class="getFanValue(value.fan_tag) === item.value ? 'primary': 'secondary'"
          @click.prevent="setFanValue(item.value, value.fan_tag)"
      >
        {{ item.power_level_name || $t('dashboard.widget.form.power_level_empty') }}
      </UiButton>
    </div>
    <div class="fan-speed__buttons"
         :class="{'col-2': value.controls_type !== 'line'}"
         v-else-if="value.controls.length && !value.fan_tag"
    >
      <UiButton
          v-for="item in value.controls"
          :class="'secondary'"
      >
        {{ item.power_level_name || $t('dashboard.widget.form.power_level_empty') }}
      </UiButton>
    </div>
    <div class="fan-speed__toggles">
      <ul>
        <li v-if="value.master_off">
          {{ $t('dashboard.widget.form.master_off') }}
          <UiToggle
              :model-value="getToggleValue(value.master_off_tag)"
              @change="changeMode($event, value.master_off_tag)"
          />
        </li>
        <li v-if="value.fan_valve">
          {{ $t('dashboard.widget.form.fan_valve') }}
          <UiToggle
              :model-value="getToggleValue(value.fan_valve_tag)"
              @change="changeMode($event, value.fan_valve_tag)"
          />
        </li>
      </ul>
    </div>
  </div>

</template>
<script setup lang="ts">
import UiIcon from "@components/ui/Icon.vue";
import {computed, ref} from "vue";
import UiCircularInput from "@components/ui/CircularInput.vue";
import UiButton from "@components/ui/Button.vue";
import UiToggle from "@components/ui/Toggle.vue";
import {useWS} from "@store/dashboard/ws";
import {storeToRefs} from "pinia";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
const storeWs = useWS()
const storeConfigurationDashboard = useConfigurationDashboardStore()
const storeConfigurationDevice = useConfigurationDeviceStore()
const {state} = storeToRefs(storeWs)
const props = defineProps(['value'])
const rangeValue = ref(props.value.default_temperature)

const plus = () => {
  if (rangeValue.value !== undefined) {
    setRangeValue({value: getRangeValue(props.value.tag) + 1}, props.value.tag)
  }
}
const minus = () => {
  if (rangeValue.value !== undefined && rangeValue.value > 0) {
    setRangeValue({value: getRangeValue(props.value.tag) - 1}, props.value.tag)
  }
}

const units = computed(() => ({
  "Celsius": '°C',
  "Fahrenheit": '°F',
}) as { [key: string]: any })

const getRangeValue = (tag: string) => {
  const entityId = storeConfigurationDashboard.getAliasIsEqual(props.value.ws_args)
  const { scope } = props.value.ws_args || {};
  const eventKey = `${entityId}_${scope}`;
  return state.value.events?.get(eventKey)?.data?.[tag]?.[0]?.[1] || 0;
}
const setRangeValue = async ({value}: any, tag: string) => {
  const entityId = storeConfigurationDashboard.getAliasIsEqual(props.value.ws_args)
  const { scope } = props.value.ws_args || {};
  if (entityId && scope) {
    let obj: any = {};
    obj[tag] = value;
    await storeConfigurationDevice.setAttr(entityId, scope, obj);
  }
}
const getFanValue = (tag: string) => {
  const entityId = storeConfigurationDashboard.getAliasIsEqual(props.value.ws_args)
  const { scope } = props.value.ws_args || {};
  const eventKey = `${entityId}_${scope}`;
  return state.value.events?.get(eventKey)?.data?.[tag]?.[0]?.[1] || 0;
}
const setFanValue = async (value: any, tag: string) => {
  const entityId = storeConfigurationDashboard.getAliasIsEqual(props.value.ws_args)
  const { scope } = props.value.ws_args || {};
  if (entityId && scope) {
    let obj: any = {};
    obj[tag] = value;
    await storeConfigurationDevice.setAttr(entityId, scope, obj);
  }
}

const getToggleValue = (tag: string) => {
  const entityId = storeConfigurationDashboard.getAliasIsEqual(props.value.ws_args)
  const { scope } = props.value.ws_args || {};
  const eventKey = `${entityId}_${scope}`;
  return state.value.events?.get(eventKey)?.data?.[tag]?.[0]?.[1] || false;
}

const changeMode = async (e: any, tag: string) => {
  const entityId = storeConfigurationDashboard.getAliasIsEqual(props.value.ws_args)
  const { scope } = props.value.ws_args || {};
  if (entityId && scope) {
    let obj: any = {};
    obj[tag] = e.target.checked;
    await storeConfigurationDevice.setAttr(entityId, scope, obj);
  }
}
</script>