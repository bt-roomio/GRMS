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
            ref="actions"
        />
      </div>
      <div class="ui-table__search" v-if="isSearchOpen">
        <UiSearch v-model="searchValue"/>
      </div>
      <RoomsList/>
      <RoomsList/>
    </div>
  </div>
</template>
<script setup lang="ts">
import PageHead from "@components/pages/dashboard/PageHead.vue";
import StatisticsCardList from "@components/pages/dashboard/main/StatisticsCardList.vue";
import Tabs from "@components/ui/Tabs.vue";
import {computed, ref} from "vue";
import {useI18n} from "vue-i18n";
import RoomsList from "@components/pages/dashboard/rooms/RoomsList.vue";
import RoomsActions from "@components/pages/dashboard/rooms/Actions.vue";
import UiSearch from "@components/ui/Search.vue";
const {t} = useI18n()
const isSearchOpen = ref(false)
const searchValue = ref('')
const tabList = computed(() => [
  {
    name: t('dashboard.rooms.tabs.all'),
    to: {name: 'room-list'},
  },
  {
    name: t('dashboard.rooms.tabs.checked_in'),
    to: {name: 'room-list', query: { tab: 'checked_in' }},
  },
  {
    name: t('dashboard.rooms.tabs.occupied'),
    to: {name: 'room-list', query: { tab: 'occupied' }},
  },
  {
    name: t('dashboard.rooms.tabs.do_not_disturb'),
    to: {name: 'room-list', query: { tab: 'do_not_disturb' }},
  },
  {
    name: t('dashboard.rooms.tabs.available'),
    to: {name: 'room-list', query: { tab: 'available' }},
  }
])
</script>