<template>
  <div class="rooms__buttons">
    <div>
      <UiIcon name="search" v-tooltip="$t('dashboard.search')" filled @click.prevent="search = !search"/>
    </div>
    <div>
      <UiIcon name="filter-lines" v-tooltip="'Filter lines'" filled/>
    </div>
    <div>
      <UiIcon name="download" v-tooltip="$t('dashboard.configuration.rooms.modals.export_new_rooms.title')" class="rotate-180" filled @click.prevent="openExportRoom"/>
    </div>
    <div>
      <UiIcon name="download" v-tooltip="$t('dashboard.configuration.rooms.modals.import_new_rooms.title')" @click.prevent="openImportRoom" filled/>
    </div>
    <div v-if="isTable" @click.prevent="isTable = !isTable">
      <UiIcon name="dots-grid" v-tooltip="$t('dashboard.rooms.change_grid')" filled/>
    </div>
    <div v-else @click.prevent="isTable = !isTable">
      <UiIcon name="list" v-tooltip="$t('dashboard.rooms.change_list')" filled/>
    </div>
  </div>
  <ModalExportRooms ref="export_room"/>
  <ModalImportRooms ref="import_room"/>
</template>
<script setup lang="ts" generic="T">
import {defineComponent, ref} from "vue";
import UiIcon from "@components/ui/Icon.vue";
import ModalExportRooms from "@components/pages/dashboard/configuration/rooms/ModalExportRooms.vue";
import ModalImportRooms from "@components/pages/dashboard/configuration/rooms/ModalImportRooms.vue";
const export_room = ref<IModal | null>(null)
const import_room = ref<IModal | null>(null)
const search = defineModel('search')
const isTable = defineModel('isTable')
const emits = defineEmits(['theadSort'])
const openExportRoom = () => export_room.value?.open()
const openImportRoom = () => import_room.value?.open()
defineComponent({name: 'RoomsActions'})
</script>