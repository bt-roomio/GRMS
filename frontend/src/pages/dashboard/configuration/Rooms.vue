<template>
  <div class="page">
    <div class="page__content">
      <PageHead
          :title="$t('dashboard.configuration.rooms.title')"
          :description="$t('dashboard.configuration.rooms.subtitle')"
          :button="$t('dashboard.configuration.rooms.add_room')"
          button-icon="plus"
          @click-button="openAddRoom"
      />
    </div>
    <div class="rooms__actions">
      <Tabs :list="tabList"/>
      <ConfigurationRoomsActions v-model:search="isSearchOpen" ref="actions"/>
    </div>

    <UiTable
        v-model:searchType="searchType"
        v-model:searchValue="searchValue"
        :is-search-open="isSearchOpen"
        :search-types="searchTypes"
        :headers="headers"
        :data="tableData"
    >
      <template #header-select>
          <CheckAll v-model="tableData" />
      </template>
      <template #select="{entity}">
        <UiCheckbox v-model="entity.select"/>
      </template>
      <template #status="{entity}">
        <UiStatus :status="entity.status as string" />
      </template>
      <template #actions>
        <UiButton class="secondary" @click.prevent="openEditRoom">
          <UiIcon name="edit" filled />
        </UiButton>
        <UiButton class="text">
          <UiIcon name="trash" filled />
        </UiButton>
      </template>
    </UiTable>
  </div>
</template>
<script setup lang="ts">
import PageHead from "../../../components/pages/dashboard/PageHead.vue";
import Tabs from "@components/ui/Tabs.vue";
import {useI18n} from "vue-i18n";
import {computed, onMounted, ref, watch} from "vue";
import UiTable from "@components/ui/Table.vue";
import CheckAll from "@components/ui/CheckAll.vue";
import UiCheckbox from "@components/ui/Checkbox.vue";
import UiButton from "@components/ui/Button.vue";
import UiIcon from "@components/ui/Icon.vue";
import UiStatus from "@components/ui/Status.vue";
import {useConfigurationRoomsStore} from "@store/dashboard/configuration/rooms.ts";
import ConfigurationRoomsActions from "@components/pages/dashboard/configuration/rooms/Actions.vue";
import {useRouter} from "vue-router";
const {t} = useI18n()
const storeConfigurationRooms = useConfigurationRoomsStore()
const router = useRouter()
const tabList = computed(() => [
  {
    name: t('dashboard.configuration.tabs.all'),
    to: {name: 'configuration-rooms'},
    badge: '3'
  },
  {
    name: t('dashboard.configuration.tabs.on'),
    to: {name: 'configuration-rooms', query: { status: 'on' }},
    badge: '1'
  },
  {
    name: t('dashboard.configuration.tabs.off'),
    to: {name: 'configuration-rooms', query: { status: 'off' }},
    badge: '1'
  },
  {
    name: t('dashboard.configuration.tabs.error'),
    to: {name: 'configuration-rooms', query: { status: 'error' }},
    badge: '1'
  }
])
const actions = ref<IConfigurationRoomsActions | null>(null)
const searchValue = ref('')
const searchType = ref('Room')
const isSearchOpen = ref(false)

watch(searchType, value => {
  console.log(value)
})
watch(searchValue, value => {
  console.log(value)
})
onMounted(async () => {
  await storeConfigurationRooms.getList({})
})
const openAddRoom = () => {
  actions.value?.add_room.open()
}
const openEditRoom = () => {
  actions.value?.edit_room.open()
}

const searchTypes = computed(() => [
  {name: t('dashboard.configuration.rooms.room')},
  {name: t('dashboard.configuration.rooms.type')},
  {name: t('dashboard.configuration.rooms.floor')},
  {name: t('dashboard.configuration.rooms.block')},
  {name: t('dashboard.configuration.rooms.mac_address')},
  {name: t('dashboard.configuration.rooms.ip_address')},
])
const headers = computed<IConfigurationRoomsHead>(() => ({
  select: true,
  room_id: t('dashboard.configuration.rooms.room'),
  type: t('dashboard.configuration.rooms.type'),
  floor: t('dashboard.configuration.rooms.floor'),
  block: t('dashboard.configuration.rooms.block'),
  mac_address: t('dashboard.configuration.rooms.mac_address'),
  ip_address: t('dashboard.configuration.rooms.ip_address'),
  status: "Status",
  actions: ''
}))

const tableData = computed<IConfigurationRoomsData[]>(() =>[
  {
    id: '223',
    select: false,
    room_id: "223",
    type: "Deluxe room",
    floor: "1",
    block: "1",
    mac_address: "98:72:3С:70:51:3D",
    ip_address: "192.112.34.56",
    status: "On",
    actions: ''
  },
  {
    id: '345',
    select: false,
    room_id: "345",
    type: "Standart room",
    floor: "2",
    block: "2",
    mac_address: "98:72:3С:70:51:3D",
    ip_address: "192.112.34.56",
    status: "Error",
    actions: ''
  },
  {
    id: '456',
    select: false,
    room_id: "456",
    type: "Superiror room",
    floor: "2",
    block: "3",
    mac_address: "",
    ip_address: "",
    status: "Off",
    actions: ''
  }
].filter(el => router.currentRoute.value.query.status ? el.status.toLowerCase() === (router.currentRoute.value.query.status as string).toLowerCase() : el))
</script>