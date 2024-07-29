<template>
  <div class="page">
    <div class="page__content">
      <UiLoader v-if="itemLoading"/>
      <PageHead
          v-if="room"
          back-to="/rooms/room-list"
          :back="$t('dashboard.rooms.back_to_rooms')"
          :title="`${$t('dashboard.rooms.table.room_number')} ${room.room_number}, ${$t('dashboard.rooms.table.floor')} ${room.floor}, ${$t('dashboard.rooms.table.block')} ${room.block}`"
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
import {computed, onMounted, onUnmounted} from "vue";
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
  if (room.value?.type?.dashboard){
    await storeConfigurationDashboard.getItem(room.value?.type.dashboard.id as string, false)
    await storeConfigurationDashboard.getDashboardInnerHelpers()
  }
})
onUnmounted(() => {
  storeConfigurationDashboard.$reset()
  storeConfigurationDashboard.$resetData()
})
</script>