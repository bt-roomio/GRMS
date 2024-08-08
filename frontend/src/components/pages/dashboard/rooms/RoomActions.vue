<template>
  <div class="flex gap-4 mb-6">
    <UiStatus :status="item.state" class="on h-8"/>
    <UiBadge class="bg-gray-200 font-medium h-8" v-if="item.type">{{ item.type.title }}</UiBadge>
    <UiBadge class="text font-bold h-8" :class="{'error': wsValueTemp < 17 || wsValueTemp > 30}" v-if="wsValueTemp !== 'error'">
      {{ wsValueTemp }} °C
    </UiBadge>
    <UiBadge v-else class="text error" v-tooltip="'No connection'">NC</UiBadge>
    <UiBadge class="bg-gray-200 font-medium h-8">
      <UiIcon name="wind" filled/>
      1
    </UiBadge>
    <UiBadge :class="wsValueMur ? 'warning' : ''" v-if="wsValueMur !== 'error'" :isDot="false" class="font-medium h-8">
      <UiIcon name="brush" filled/>
    </UiBadge>
    <UiBadge v-else class="text error" v-tooltip="'No connection'">NC</UiBadge>
    <UiBadge :class="wsValueDnd ? 'warning' : ''" v-if="wsValueDnd !== 'error'" :isDot="false" class="font-medium h-8">
      <UiIcon name="alarm-clock-off" filled/>
    </UiBadge>
    <UiBadge v-else class="text error" v-tooltip="'No connection'">NC</UiBadge>

    <UiBadge :isDot="false" :class="item.status === 'OFF' ? 'off' : ''">
      <UiIcon name="alert-circle" filled/>
    </UiBadge>
  </div>
</template>
<script setup lang="ts">
import UiStatus from "@components/ui/Status.vue";
import UiBadge from "@components/ui/Badge.vue";
import UiIcon from "@components/ui/Icon.vue";
import {computed, onMounted, onUnmounted} from "vue";
import {useWS} from "@store/dashboard/ws";
import {storeToRefs} from "pinia";
const props = defineProps(['item'])
const entityId = computed(() => (props.item as IRoom)?.devices?.[0]?.id || null)
const storeWs = useWS()
const {send, unSubscription} = storeWs
const {state} = storeToRefs(storeWs)
const wsValueTemp = computed(() => {
  if (entityId.value && state.value.events.get(entityId.value + '_SHARED_SCOPE')?.data['room_temp']){
    return state.value.events.get(entityId.value + '_SHARED_SCOPE').data['room_temp'][0][1]
  }else {
    return 'error'
  }
})
const wsValueMur = computed(() => {
  if (entityId.value && state.value.events.get(entityId.value + '_SHARED_SCOPE')?.data['mur']){
    return state.value.events.get(entityId.value + '_SHARED_SCOPE').data['mur'][0][1]
  }else {
    return 'error'
  }
})
const wsValueDnd = computed(() => {
  if (entityId.value && state.value.events.get(entityId.value + '_SHARED_SCOPE')?.data['dnd']){
    return state.value.events.get(entityId.value + '_SHARED_SCOPE').data['dnd'][0][1]
  }else {
    return 'error'
  }
})
onMounted(() => {
  if (entityId.value) {
    const wsArgs = {
      entityType: 'DEVICE',
      entityId: entityId.value,
      scope: "SHARED_SCOPE",
      type: "ATTRIBUTES"
    }
    const isFilled = Object.values(wsArgs).every(arg => !!arg);
    if (isFilled){
      send(wsArgs)
    }
  }
})
onUnmounted(() => {
  if (entityId.value) {
    const wsArgs = {
      entityType: 'DEVICE',
      entityId: entityId.value,
      scope: "SHARED_SCOPE",
      type: "ATTRIBUTES"
    }
    const isFilled = Object.values(wsArgs).every(arg => !!arg);
    if (isFilled){
      unSubscription(wsArgs)
    }
  }
})
interface IRoom {
  id?: any
  block: any
  devices?: any
  status?: any
  state?: any
  floor: any
  room_number: any
  temp?: any
  system_mode?: any
  type: IConfigurationRoomTypes | any
}
</script>