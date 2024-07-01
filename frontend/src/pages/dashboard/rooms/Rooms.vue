<template>
  <div class="page">
    <div class="page__content">
      <PageHead
          title="Rooms"
          description="Track and manage your room list"
          button=""
          button-icon="list"
          button-class="text"
      />
      <StatisticsCardList />

      <div class="rooms__actions">
        <Tabs :list="tabList"/>
        <RoomsActions
            v-model:search="isSearchOpen"
            v-model:isTable="isTable"
            ref="actions"
        />
      </div>
      <RoomContent :is-search-open="isSearchOpen" :is-table="isTable"/>
    </div>
  </div>
</template>
<script setup lang="ts">
import PageHead from "@components/pages/dashboard/PageHead.vue";
import StatisticsCardList from "@components/pages/dashboard/main/StatisticsCardList.vue";
import Tabs from "@components/ui/Tabs.vue";
import {computed, onMounted, ref} from "vue";
import RoomsActions from "@components/pages/dashboard/rooms/Actions.vue";
import {onBeforeRouteUpdate} from "vue-router";
import {useI18n} from "vue-i18n";
import {useConfigurationRoomsStore} from "@store/dashboard/configuration/rooms.ts";
import RoomContent from "@components/pages/dashboard/rooms/RoomContent.vue";
const isSearchOpen = ref(false)
const isTable = ref(false)
const {t} = useI18n()
const storeConfigurationRooms = useConfigurationRoomsStore()

const tabList = computed(() => [
  {
    name: t('dashboard.rooms.tabs.all'),
    to: {name: 'room-list'},
  },
  {
    name: t('dashboard.rooms.tabs.available'),
    to: {name: 'room-list', query: { state: 'Available' }},
  },
  {
    name: t('dashboard.rooms.tabs.checked_in'),
    to: {name: 'room-list', query: { state: 'CheckedIn' }},
  },
  {
    name: t('dashboard.rooms.tabs.occupied'),
    to: {name: 'room-list', query: { state: 'Occupied' }},
  },
  {
    name: t('dashboard.rooms.tabs.do_not_disturb'),
    to: {name: 'room-list', query: { state: 'DoNotDistrub' }},
  },
  {
    name: t('dashboard.rooms.tabs.available'),
    to: {name: 'room-list', query: { state: 'MakeUpRoom' }},
  }
])


onMounted(async () => {
  await storeConfigurationRooms.getList({sort_by: ['block', 'floor']})
})
onBeforeRouteUpdate(async (to) => {
  await storeConfigurationRooms.getList({sort_by: ['block', 'floor'], ...to.query})
})
</script>