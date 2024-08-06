<template>
  <div class="page">
    <div class="page__content">
      <PageHead
          :title="$t('dashboard.menu.rooms')"
          :description="$t('dashboard.rooms.subtitle')"
          button=""
          button-icon="list"
          button-class="text"
      />
      <StatisticsCardList />
      <div class="rooms__actions">
        <Tabs :list="tabList"/>
        <RoomsActions
            v-model:search="isSearchOpen"
            :filters="sortedHeaders ? sortedHeaders : headers"
            v-model:isTable="isTable"
            ref="actions"
            @theadSort="theadSortHandle"
        />
      </div>
      <RoomContent :is-search-open="isSearchOpen" :headers="sortedHeaders ? sortedHeaders : headers" :is-table="isTable"/>
    </div>
  </div>
</template>
<script setup lang="ts">
import PageHead from "@components/pages/dashboard/PageHead.vue";
import StatisticsCardList from "@components/pages/dashboard/main/StatisticsCardList.vue";
import Tabs from "@components/ui/Tabs.vue";
import {computed, onMounted, onUnmounted, ref, watch} from "vue";
import RoomsActions from "@components/pages/dashboard/rooms/Actions.vue";
import {onBeforeRouteUpdate} from "vue-router";
import {useI18n} from "vue-i18n";
import {useConfigurationRoomsStore} from "@store/dashboard/configuration/rooms.ts";
import RoomContent from "@components/pages/dashboard/rooms/RoomContent.vue";
import {storeToRefs} from "pinia";
import router from "@/router";
import {useUserStore} from "@store/dashboard/user";
const isSearchOpen = ref(false)
const isTable = ref(true)
const {t} = useI18n()
const storeUser = useUserStore()
const {profile} = storeToRefs(storeUser)
const profileIsTable = computed(() =>
    (typeof profile.value?.additional_info?.[router.currentRoute.value.path]?.isTable === 'boolean') ?
        profile.value?.additional_info?.[router.currentRoute.value.path]?.isTable :
        true
)
const storeConfigurationRooms = useConfigurationRoomsStore()
const {sortedData, searchValue} = storeToRefs(storeConfigurationRooms)
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
    name: t('dashboard.rooms.tabs.make_up_room'),
    to: {name: 'room-list', query: { state: 'MakeUpRoom' }},
  }
])
watch(profileIsTable, value => {
    isTable.value = value
})
watch(isSearchOpen, value => {
  if (!value) {
    searchValue.value = ''
  }
})
onMounted(async () => {
  isTable.value = profileIsTable.value
  sortedData.value = {sort_by: ['block', 'floor']}
  await storeConfigurationRooms.getList({sort_by: ['block', 'floor'], ...router.currentRoute.value.query})
})
onBeforeRouteUpdate(async (to) => {
  await storeConfigurationRooms.getList({sort_by: ['block', 'floor'], ...to.query})
})
onUnmounted(() => {
  storeConfigurationRooms.$reset()
  storeConfigurationRooms.$resetData()
})
const sortedHeaders = computed(() => {
  const columns = profile.value?.additional_info?.[router.currentRoute.value.path]?.columnFilters || null
  if (columns) {
    const importantKeys = ['select', 'actions']
    const results: any = {}

    for (const headersKey in headers.value) {
      if ([...columns, ...importantKeys].includes(headersKey as string)){
        results[headersKey] = headers.value[headersKey]
      }
    }
    return results
  } else {
    return null
  }
});

const headers = computed<IConfigurationRoomsHead>(() => ({
  select: false,
  room_number: t('dashboard.rooms.table.room_number'),
  floor: t('dashboard.rooms.table.floor'),
  block: t('dashboard.rooms.table.block'),
  type: t('dashboard.rooms.table.type'),
  temp: t('dashboard.rooms.table.temp'),
  cln: 'MUR',
  dnd: 'DND',
  device: t('dashboard.rooms.table.device'),
  actions: '',
}))
const theadSortHandle = (array: string[]) => {
  let results: any = {}
  results.select = true
  for (const headersKey in headers.value) {
    if (array.includes(headers.value[headersKey] as string)){
      results[headersKey] = headers.value[headersKey]
    }
  }
  results.actions = ''
  const key = Object.keys(results)
  storeUser.saveUserConfiguration(router.currentRoute.value.path, { columnFilters: key });
}
</script>