<template>
  <span ref="target">
    <template v-if="type === 'temp'">
    <UiBadge v-if="wsValueTemp !== 'error'" class="text" :class="{'error': wsValueTemp < 17 || wsValueTemp > 30}">{{wsValueTemp + '°C'}}</UiBadge>
    <UiBadge v-else class="text error" v-tooltip="'No connection'">NC</UiBadge>
  </template>
    <template v-if="type === 'cln'">
      <UiSmallButton :class="wsValueMur ? 'warning' : 'inactive'" v-if="wsValueMur !== 'error'">
        <UiIcon name="check" filled/>
      </UiSmallButton>
      <UiBadge v-else class="text error" v-tooltip="'No connection'">NC</UiBadge>
    </template>
    <template v-if="type === 'dnd'">
      <UiSmallButton :class="wsValueDnd ? 'warning' : 'inactive'" v-if="wsValueDnd !== 'error'">
        <UiIcon name="alarm-clock-off" filled/>
      </UiSmallButton>
      <UiBadge v-else class="text error" v-tooltip="'No connection'">NC</UiBadge>
    </template>
    <template v-if="type === 'actions'">
      <UiDropdown @click.stop v-if="wsValueMur !== 'error' || wsValueDnd !== 'error'">
        <template #trigger>
          <div class="flex gap-2 items-center text-primary-600 dark:text-white">
            {{ $t('dashboard.rooms.table.actions') }}
            <UiIcon class="stroke-primary-600 dark:stroke-white" name="chevron-down" filled />
          </div>
        </template>
        <template #content>
          <div class="dropdown__menu">
            <div v-if="wsValueMur !== 'error'" @click.prevent="activateMur">{{ $t('dashboard.rooms.table.activate_cleaning') }}</div>
            <div v-if="wsValueDnd !== 'error'" @click.prevent="activateDnd">{{ $t('dashboard.rooms.table.activate_dnd') }}</div>
          </div>
        </template>
      </UiDropdown>
    </template>
  </span>
</template>
<script setup lang="ts">
import UiIcon from "@components/ui/Icon.vue";
import UiBadge from "@components/ui/Badge.vue";
import UiSmallButton from "@components/ui/ButtonSmall.vue";
import {computed, onMounted, onUnmounted, ref, watch} from "vue";
import {useWS} from "@store/dashboard/ws";
import {storeToRefs} from "pinia";
import UiDropdown from "@components/ui/Dropdown.vue";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
import {useElementVisibility} from "@vueuse/core";
const storeConfigurationDevice = useConfigurationDeviceStore()
const storeWs = useWS()
const {send, unSubscription} = storeWs
const {state} = storeToRefs(storeWs)
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
const props = defineProps(['type', 'entity'])
const entityId = computed(() => (props.entity as IRoom).devices?.[0]?.id || null)

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
const target = ref(null)
const targetIsVisible = useElementVisibility(target)
watch(targetIsVisible, (newValue) => {
  const wsArgs = {
    entityType: 'DEVICE',
    entityId: entityId.value,
    scope: "SHARED_SCOPE",
    type: "ATTRIBUTES"
  }
  const isFilled = Object.values(wsArgs).every(arg => !!arg);
  if (newValue && entityId.value) {
    if (isFilled) {
      send(wsArgs)
    }
  }else {
    if (isFilled) {
      unSubscription(wsArgs)
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
const activateMur = async () => {
  if (entityId.value) {
    let obj: any = {};
    obj['mur'] = !wsValueMur.value;
    await storeConfigurationDevice.setAttr(entityId.value, 'SHARED_SCOPE', obj);
  }
}
const activateDnd = async () => {
  if (entityId.value) {
    let obj: any = {};
    obj['dnd'] = !wsValueDnd.value;
    await storeConfigurationDevice.setAttr(entityId.value, 'SHARED_SCOPE', obj);
  }
}
</script>