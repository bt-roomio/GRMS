<template>
  <div class="page" v-if="rooms">
    <div class="page__content" >
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
      <ConfigurationRoomsActions
          v-model:search="isSearchOpen"
          ref="actions"
          @theadSort="theadSortHandle"
      />
    </div>
    <UiTable
        :loading="loading"
        :error="error"
        v-model:searchType="searchType"
        v-model:searchValue="searchValue"
        :is-search-open="isSearchOpen"
        :search-types="searchTypes"
        :headers="sortedHeaders ? sortedHeaders : headers"
        :data="rooms.results"
        :sort="['room_number','floor','block','device']"
        @sorted="storeConfigurationRooms.sortList"
        @more="moreHandle"
        :is-pagination="rooms.count > rooms.results.length"
    >
      <template #header-select>
          <CheckAll v-model="rooms.results" />
      </template>
      <template #select="{entity}">
        <UiCheckbox v-model="entity.select"/>
      </template>
      <template #devices="{entity}" >
        <template v-if="(entity.devices as []).length">
          <div class="flex flex-wrap gap-1">
            <div class="ui_badge" v-for="i in entity.devices" :key="i">{{i}}</div>
          </div>
        </template>
        <template v-else>-</template>
      </template>
      <template #status="{entity}">
        <UiStatus :status="entity.status as string" />
      </template>
      <template #actions="{entity}">
        <div class="ui-table__actions col-2">
          <UiButton class="secondary" @click.prevent="openEditRoom(entity.id as string)">
            <UiIcon name="edit" filled />
          </UiButton>
          <UiButton class="text" @click.prevent="storeConfigurationRooms.deleteItem(entity.id as string)">
            <UiIcon name="trash" filled />
          </UiButton>
        </div>

      </template>
    </UiTable>
  </div>
</template>
<script setup lang="ts">
import ConfigurationRoomsActions from "@components/pages/dashboard/configuration/rooms/Actions.vue";
import PageHead from "@components/pages/dashboard/PageHead.vue";
import Tabs from "@components/ui/Tabs.vue";
import UiTable from "@components/ui/Table.vue";
import CheckAll from "@components/ui/CheckAll.vue";
import UiCheckbox from "@components/ui/Checkbox.vue";
import UiButton from "@components/ui/Button.vue";
import UiIcon from "@components/ui/Icon.vue";
import UiStatus from "@components/ui/Status.vue";
import {computed, onMounted, ref} from "vue";
import {useConfigurationRoomsStore} from "@store/dashboard/configuration/rooms.ts";
import {storeToRefs} from "pinia";
import {useI18n} from "vue-i18n";

const {t} = useI18n()
const storeConfigurationRooms = useConfigurationRoomsStore()
const {rooms, error, searchType, searchValue, loading} = storeToRefs(storeConfigurationRooms)

const actions = ref<IConfigurationRoomsActions | null>(null)
const isSearchOpen = ref(false)
const tabList = computed(() => [
  {
    name: t('dashboard.configuration.tabs.all'),
    to: {name: 'configuration-rooms'},
  },
  {
    name: t('dashboard.configuration.tabs.on'),
    to: {name: 'configuration-rooms', query: { status: 'on' }},
  },
  {
    name: t('dashboard.configuration.tabs.off'),
    to: {name: 'configuration-rooms', query: { status: 'off' }},
  }
])

onMounted(async () => {
  await storeConfigurationRooms.getList({})
})

const openAddRoom = () => {
  actions.value?.add_room.open()
}
const openEditRoom = async (id: string) => {
  try {
    await storeConfigurationRooms.getItem(id, true)
    actions.value?.edit_room.open()
  }catch (e){
    console.log(e)
  }
}

const searchTypes = computed(() => [
  {
    name: t('dashboard.configuration.rooms.room'),
    key: 'room_number'
  },
  {
    name: t('dashboard.configuration.rooms.type'),
    key: 'type'
  },
  {
    name: t('dashboard.configuration.rooms.floor'),
    key: 'floor'
  },
  {
    name: t('dashboard.configuration.rooms.block'),
    key: 'block'
  },
  {
    name: t('dashboard.configuration.rooms.devices'),
    key: 'devices'
  },
])
const headers = computed<IConfigurationRoomsHead>(() => ({
  select: true,
  room_number: t('dashboard.configuration.rooms.room'),
  type: t('dashboard.configuration.rooms.type'),
  floor: t('dashboard.configuration.rooms.floor'),
  block: t('dashboard.configuration.rooms.block'),
  devices: t('dashboard.configuration.rooms.devices'),
  status: t('dashboard.configuration.rooms.status'),
  actions: ''
}))

const sortedHeaders = ref(null)
const theadSortHandle = (array: string[]) => {
  let results: any = {}
  results.select = true
  for (const headersKey in headers.value) {
    if (array.includes(headers.value[headersKey] as string)){
      results[headersKey] = headers.value[headersKey]
    }
  }
  results.actions = ''
  sortedHeaders.value = results
}

const moreHandle = async () => {
  await storeConfigurationRooms.loadMore()
}
</script>