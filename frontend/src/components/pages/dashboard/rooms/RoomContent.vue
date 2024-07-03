<template>
  <div class="rooms__content">
    <template v-if="isTable">
      <UiTable
          :loading="loading"
          :error="error"
          v-model:searchType="searchType"
          v-model:searchValue="searchValue"
          :is-search-open="isSearchOpen"
          :search-types="searchTypes"
          :headers="headers"
          :data="rooms?.results"
          :sort="['room_number','status']"
          @sorted="storeConfigurationRooms.sortList"
          @more="moreHandle"
          :is-pagination="rooms.count > rooms.results.length"
          @click="toPage"
          pointer
      >
        <template #room_number="{entity}">
          <UiBadge>{{entity.room_number}}</UiBadge>
        </template>
        <template #temp="{entity}">
          <span class="font-semibold">{{entity.temp || 0 + '°C'}}</span>
        </template>
        <template #system_mode="{entity}">
          {{entity.system_mode || 'Off'}}
        </template>
        <template #indicators="{entity}">
          <div class="rooms-card__actions">
            <UiSmallButton :class="entity.state === 'MakeUpRoom' ? 'active' : 'inactive'">
              <UiIcon name="brush" filled/>
            </UiSmallButton>
            <UiSmallButton :class="entity.status === 'OFF' ? 'active' : 'inactive'">
              <UiIcon name="wifi" filled/>
            </UiSmallButton>
            <UiSmallButton class="inactive">
              <UiIcon name="alert-circle" filled/>
            </UiSmallButton>
          </div>
        </template>
        <template #status="{entity}">
          <UiStatus :status="entity.state as string" />
        </template>
      </UiTable>
    </template>
    <template v-else>
      <UiLoader v-if="loading"/>
      <div class="ui-table__search" v-if="isSearchOpen">
        <UiSearch v-model="searchValue"/>
      </div>
      <RoomsList v-for="(items, key) in sortedListResults" :key="key" :items="items"/>
      <div class="card ui-table__error" v-if="!sortedListResults?.length">
        <p class="error-title">{{ $t('dashboard.table.no_data_title') }}</p>
        <p class="error-subtitle">{{ $t('dashboard.table.no_data_subtitle') }}</p>
      </div>
    </template>
  </div>


</template>
<script setup lang="ts">
import UiSearch from "@components/ui/Search.vue";
import RoomsList from "@components/pages/dashboard/rooms/RoomsList.vue";
import UiTable from "@components/ui/Table.vue";
import UiStatus from "@components/ui/Status.vue";
import {useConfigurationRoomsStore} from "@store/dashboard/configuration/rooms.ts";
import {storeToRefs} from "pinia";
import {computed} from "vue";
import {useI18n} from "vue-i18n";
import UiSmallButton from "@components/ui/ButtonSmall.vue";
import UiIcon from "@components/ui/Icon.vue";
import UiBadge from "@components/ui/Badge.vue";
import UiLoader from "@components/ui/Loader.vue";
import {useRouter} from "vue-router";
defineProps(['isTable', 'isSearchOpen'])
const {t} = useI18n()
const {push} = useRouter()
const storeConfigurationRooms = useConfigurationRoomsStore()
const {rooms, error, searchType, searchValue, loading} = storeToRefs(storeConfigurationRooms)
const sortedListResults = computed(() => {
  if (!rooms.value) return
  rooms.value.results.sort((a, b) => {
    if (a.floor !== b.floor) {
      return a.floor - b.floor;
    } else if (a.block !== b.block) {
      return a.block - b.block;
    } else {
      return a.room_number - b.room_number;
    }
  });

// Разделение на подмассивы по блокам
  return rooms.value.results.reduce((acc: IConfigurationRoom[][], room) => {
    // Найти подмассив для текущего блока
    let blockArray = acc.find(subArray => subArray[0].block === room.block);

    // Если подмассив не найден, создать новый
    if (!blockArray) {
      blockArray = [];
      acc.push(blockArray);
    }

    // Добавить текущую комнату в подмассив
    blockArray.push(room);

    return acc;
  }, []);
})
const searchTypes = computed(() => [
  {
    name: t('dashboard.rooms.table.room_number'),
    key: 'room_number'
  },
  {
    name: t('dashboard.rooms.table.floor'),
    key: 'floor'
  },
  {
    name: t('dashboard.rooms.table.block'),
    key: 'block'
  },
])

const headers = computed<IConfigurationRoomsHead>(() => ({
  room_number: t('dashboard.rooms.table.room_number'),
  floor: t('dashboard.rooms.table.floor'),
  block: t('dashboard.rooms.table.block'),
  type: t('dashboard.rooms.table.type'),
  temp: t('dashboard.rooms.table.temp'),
  system_mode: t('dashboard.rooms.table.system_mode'),
  indicators: t('dashboard.rooms.table.indicators'),
  status: t('dashboard.rooms.table.status'),
}))
const moreHandle = async () => {
  await storeConfigurationRooms.loadMore()
}
const toPage = async (entity: any) => {
  await push({name: 'room-inner', params: {id: entity.id}})
}
</script>