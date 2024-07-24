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
          :sort="['room_number','status', 'temp']"
          @sorted="storeConfigurationRooms.sortList"
          @more="moreHandle"
          :is-pagination="rooms.count > rooms.results.length"
          @click="toPage"
          pointer
      >
        <template #header-select>
          <CheckAll v-model="rooms.results" />
        </template>
        <template #select="{entity}">
          <UiCheckbox @click.stop v-model="entity.select"/>
        </template>
        <template #room_number="{entity}">
          <p class="font-bold">{{(entity as IRoom).room_number}}</p>
        </template>
        <template #temp="{entity}">
          <UiBadge class="text" :class="{'error': ((entity as IRoom).temp || 0) < 17 || ((entity as IRoom).temp || 0) > 30}">{{(entity as IRoom).temp || 0 + '°C'}}</UiBadge>
        </template>
        <template #header-cln="{entity}">
          <div class="flex items-center gap-1">
            {{entity}}
            <UiIcon v-tooltip="'This indicator reflects the current status of room cleaning'" class="cursor-pointer" name="help-circle" filled/>
          </div>
        </template>
        <template #header-dnd="{entity}">
          <div class="flex items-center gap-1">
            {{entity}}
            <UiIcon v-tooltip="'This indicator reflects the current status of room cleaning'" class="cursor-pointer" name="help-circle" filled/>
          </div>
        </template>
        <template #header-device="{entity}">
          <div class="flex items-center gap-1">
            {{entity}}
            <UiIcon v-tooltip="'This indicator reflects the current status of room cleaning'" class="cursor-pointer" name="help-circle" filled/>
          </div>
        </template>
        <template #cln>
          <UiSmallButton class="inactive">
            <UiIcon name="check" filled/>
          </UiSmallButton>
        </template>
        <template #dnd>
          <UiSmallButton class="warning">
            <UiIcon name="alarm-clock-off" filled/>
          </UiSmallButton>
        </template>
        <template #device="{entity}">
          <UiSmallButton :class="{active: entity.status === 'OFF'}">
            <UiIcon name="alert-circle" filled/>
          </UiSmallButton>
        </template>
        <template #actions>
          <div class="ui-table__actions">
            <UiDropdown @click.stop>
              <template #trigger>
                <div class="flex gap-2 items-center text-primary-600 dark:text-white">
                  {{ $t('dashboard.rooms.table.actions') }}
                  <UiIcon class="stroke-primary-600 dark:stroke-white" name="chevron-down" filled />
                </div>
              </template>
              <template #content>
                <div class="dropdown__menu">
                  <div>{{ $t('dashboard.rooms.table.delete_room') }}</div>
                  <div>{{ $t('dashboard.rooms.table.edit_room') }}</div>
                  <div>{{ $t('dashboard.rooms.table.activate_cleaning') }}</div>
                  <div>{{ $t('dashboard.rooms.table.activate_dnd') }}</div>
                </div>
              </template>
            </UiDropdown>
          </div>
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
      <div class="ui-table__pagination" v-if="rooms.count > rooms.results.length">
        <UiButton :loading="loading" class="primary" @click="moreHandle">{{ $t('dashboard.table.load_more') }}</UiButton>
      </div>
    </template>
  </div>


</template>
<script setup lang="ts">
import UiSearch from "@components/ui/Search.vue";
import RoomsList from "@components/pages/dashboard/rooms/RoomsList.vue";
import UiTable from "@components/ui/Table.vue";
import {useConfigurationRoomsStore} from "@store/dashboard/configuration/rooms.ts";
import {storeToRefs} from "pinia";
import {computed} from "vue";
import {useI18n} from "vue-i18n";
import UiSmallButton from "@components/ui/ButtonSmall.vue";
import UiIcon from "@components/ui/Icon.vue";
import UiLoader from "@components/ui/Loader.vue";
import {useRouter} from "vue-router";
import UiButton from "@components/ui/Button.vue";
import CheckAll from "@components/ui/CheckAll.vue";
import UiCheckbox from "@components/ui/Checkbox.vue";
import UiBadge from "@components/ui/Badge.vue";
import UiDropdown from "@components/ui/Dropdown.vue";
defineProps(['isTable', 'isSearchOpen', 'headers'])
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

const moreHandle = async () => {
  await storeConfigurationRooms.loadMore()
}
const toPage = async (entity: any) => {
  await push({name: 'room-inner', params: {id: entity.id}})
}

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