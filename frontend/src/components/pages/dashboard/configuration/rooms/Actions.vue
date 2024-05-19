<template>
  <div class="rooms__buttons">
    <UiIcon name="search" filled @click.prevent="search = !search"/>
    <UiIcon name="filter-lines" filled/>
    <UiIcon name="copy" filled @click.prevent="openAddRoom"/>
    <UiIcon name="download" class="rotate-180" filled @click.prevent="openExportRoom"/>
    <UiIcon name="download" @click.prevent="openImportRoom" filled/>
    <UiIcon name="eye" filled/>
  </div>
  <ModalAddRoom ref="add_room"/>
  <ModalEditRoom ref="edit_room"/>
  <ModalExportRooms ref="export_room"/>
  <ModalImportRooms ref="import_room"/>
</template>
<script setup lang="ts">
import {defineComponent, ref} from "vue";
import ModalAddRoom from "@components/pages/dashboard/configuration/rooms/ModalAddRoom.vue";
import UiIcon from "@components/ui/Icon.vue";
import ModalEditRoom from "@components/pages/dashboard/configuration/rooms/ModalEditRoom.vue";
import ModalExportRooms from "@components/pages/dashboard/configuration/rooms/ModalExportRooms.vue";
import ModalImportRooms from "@components/pages/dashboard/configuration/rooms/ModalImportRooms.vue";
const add_room = ref<IModal | null>(null)
const edit_room = ref<IModal | null>(null)
const export_room = ref<IModal | null>(null)
const import_room = ref<IModal | null>(null)
const search = defineModel('search')

const openAddRoom = () => add_room.value?.open()
const openExportRoom = () => export_room.value?.open()
const openImportRoom = () => import_room.value?.open()

defineExpose({
  add_room,
  edit_room
})
defineComponent({name: 'ConfigurationRoomsActions'})
</script>