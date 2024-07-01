<template>
  <div class="page">
    <div class="page__content">
      <UiLoader v-if="itemLoading"/>

      <PageHead
          v-if="room"
          back-to="/rooms/room-list"
          back="Back to rooms"
          :title="`Room ${room.room_number}, floor ${room.floor}, block ${room.block}`"
      />
      <RoomActions :item="room"/>
      <Tabs :list="tabList"/>
      <WidgetContainer
          v-if="viewModel"
          :isSettings="false"
          v-model="viewModel"
          :widgets="viewWidgets"
      />
    </div>
  </div>
</template>
<script setup lang="ts">
import PageHead from "@components/pages/dashboard/PageHead.vue";
import RoomActions from "@components/pages/dashboard/rooms/RoomActions.vue";
import Tabs from "@components/ui/Tabs.vue";
import {computed, onMounted} from "vue";
import {useI18n} from "vue-i18n";
import WidgetContainer from "@components/widgets/WidgetContainer.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import {storeToRefs} from "pinia";
import {useConfigurationRoomsStore} from "@store/dashboard/configuration/rooms.ts";
import {useRoute} from "vue-router";
import UiLoader from "@components/ui/Loader.vue";
const storeConfigurationDashboard = useConfigurationDashboardStore()
const storeConfigurationRooms = useConfigurationRoomsStore()
const {itemLoading, room} = storeToRefs(storeConfigurationRooms)
const {
  viewModel,
  viewWidgets,
} = storeToRefs(storeConfigurationDashboard)
const {t} = useI18n()
const {params} = useRoute()
const tabList = computed(() => [
  {
    name: 'Room controls',
    to: {name: 'room-inner'},
  },
  {
    name: t('dashboard.menu.backlog'),
    to: {name: 'room-inner', query: { tab: 'backlog' }},
  },
  {
    name: 'HVAC',
    to: {name: 'room-inner', query: { tab: 'HVAC' }},
  }
])

onMounted(async () => {
  await storeConfigurationRooms.getItem(params.id as string, false)
  await storeConfigurationDashboard.getItem('e91dd3e9-d109-4924-b82d-95262d4ceece' as string, false),
  await storeConfigurationDashboard.getDashboardInnerHelpers()
})
// const dashboardSettings = ref([
//   {
//     "i": "2d07b30f",
//     "type": "fan-speed",
//     "x": 0,
//     "y": 0,
//     "w": 6,
//     "h": 39,
//     "config": {
//       "title": "Current Fan Speed",
//       "description": "You can manage current Fan Speed",
//     }
//   },
//   {
//     "i": "2d0das7b30f",
//     "type": "mode",
//     "x": 6,
//     "y": 0,
//     "w": 6,
//     "h": 32,
//     "config": {
//       "title": "System Mode",
//       "description": "Select one of the operating modes",
//     },
//   },
//   {
//     "i": "2d0das72b30f",
//     "type": "sensor",
//     "x": 0,
//     "y": 0,
//     "w": 6,
//     "h": 23,
//     "config": {
//       "title": "General sensor",
//       "description": "Select one of the operating modes",
//     },
//   },
//   {
//     "i": "2d0das7asd2b30f",
//     "type": "slider",
//     "x": 6,
//     "y": 0,
//     "w": 6,
//     "h": 42,
//     "config": {
//       "title": "Lighting settings",
//       "description": "Select one of the operating modes",
//     },
//   }
// ])
</script>