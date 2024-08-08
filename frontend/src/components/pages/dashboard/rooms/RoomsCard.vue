<template>
  <router-link :to="{name: 'room-inner', params: {id: item.id}}" class="rooms-card" v-if="item" :class="{'error': item.status === 'OFF'}">
    <div class="rooms-card__info">
      <div class="rooms-card__number" :class="item.state.toLowerCase()">
        <p>{{ item.room_number }}</p>
      </div>
      <div class="rooms-card__degree" :class="{'text-error-500': wsValueTemp < 17 || wsValueTemp > 30}" v-if="wsValueTemp !== 'error'">
        t {{ wsValueTemp }} °C
      </div>
      <div class="rooms-card__degree" v-else>
        <span class="text-error-500"  v-tooltip="'No connection'"> NC </span>
      </div>
    </div>
    <div class="rooms-card__actions">
      <div class="actions__item">
        <UiSmallButton class="error" v-if="item.status === 'OFF'">
          <UiIcon name="alert-circle" filled/>
        </UiSmallButton>
        <UiSmallButton v-if="wsValueMur !== 'error'" :class="wsValueMur ? 'warning' : 'inactive'">
          <UiIcon name="check" filled/>
        </UiSmallButton>
        <UiSmallButton v-else class="error" v-tooltip="'No connection'">
          <span class="text-[8px] text-white"> NC </span>
        </UiSmallButton>
        <p>MUR</p>
      </div>
      <div class="actions__item">
        <UiSmallButton class="warning" v-if="item.state === 'DoNotDistrub'">
          <UiIcon name="alert-circle" filled/>
        </UiSmallButton>
        <UiSmallButton v-if="wsValueDnd !== 'error'" :class="wsValueDnd ? 'warning' : 'inactive'">
          <UiIcon name="alarm-clock-off" filled/>
        </UiSmallButton>
        <UiSmallButton v-else class="error" v-tooltip="'No connection'">
          <span class="text-[8px] text-white"> NC </span>
        </UiSmallButton>
        <p>DND</p>
      </div>
    </div>
  </router-link>
</template>
<script setup lang="ts">
import UiSmallButton from "@components/ui/ButtonSmall.vue";
import UiIcon from "@components/ui/Icon.vue";
import {computed, onMounted, onUnmounted} from "vue";
import {useWS} from "@store/dashboard/ws";
import {storeToRefs} from "pinia";
const props = defineProps(['item'])
const entityId = computed(() => (props.item as IRoom).devices?.[0]?.id || null)
const storeWs = useWS()
const {send, unSubscription} = storeWs
const {state} = storeToRefs(storeWs)
const wsValueTemp = computed(() => {
  if (entityId.value && state.value.events.get(entityId.value + '_SHARED_SCOPE')?.data['temp']){
    return state.value.events.get(entityId.value + '_SHARED_SCOPE').data['temp'][0][1]
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