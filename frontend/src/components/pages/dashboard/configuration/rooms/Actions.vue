<template>
  <div class="rooms__buttons">
    <UiIcon name="search" v-tooltip="$t('dashboard.search')" filled @click.prevent="search = !search"/>
    <UiIcon name="download" v-tooltip="$t('dashboard.configuration.rooms.modals.export_new_rooms.title')" class="rotate-180" filled @click.prevent="openExportRoom"/>
    <UiIcon name="download" v-tooltip="$t('dashboard.configuration.rooms.modals.import_new_rooms.title')" @click.prevent="openImportRoom" filled/>
    <UiDropdown>
      <template #trigger>
        <UiIcon name="settings" v-tooltip="$t('dashboard.settings.title')" filled/>
      </template>
      <template #content>
        <div class="dropdown__menu">
          <UiCheckbox
              v-for="(header, i) in sortTable"
              :key="`${header}${i}`"
              class="w-full"
              @change="changeSort"
              v-model="header.active"
          >
            {{header.name}}
          </UiCheckbox>
        </div>
      </template>
    </UiDropdown>
  </div>
  <ModalAddRoom ref="add_room"/>
  <ModalEditRoom ref="edit_room"/>
  <ModalExportRooms ref="export_room"/>
  <ModalImportRooms ref="import_room"/>
</template>
<script setup lang="ts" generic="T">
import {defineComponent, onMounted, ref, watch} from "vue";
import ModalAddRoom from "@components/pages/dashboard/configuration/rooms/ModalAddRoom.vue";
import UiIcon from "@components/ui/Icon.vue";
import ModalEditRoom from "@components/pages/dashboard/configuration/rooms/ModalEditRoom.vue";
import ModalExportRooms from "@components/pages/dashboard/configuration/rooms/ModalExportRooms.vue";
import ModalImportRooms from "@components/pages/dashboard/configuration/rooms/ModalImportRooms.vue";
import UiDropdown from "@components/ui/Dropdown.vue";
import {useI18n} from "vue-i18n";
import UiCheckbox from "@components/ui/Checkbox.vue";
const props = defineProps(['filters'])
const add_room = ref<IModal | null>(null)
const edit_room = ref<IModal | null>(null)
const export_room = ref<IModal | null>(null)
const import_room = ref<IModal | null>(null)
const search = defineModel('search')
const {t} = useI18n()
const emits = defineEmits(['theadSort'])
const openExportRoom = () => export_room.value?.open()
const openImportRoom = () => import_room.value?.open()

defineExpose({
  add_room,
  edit_room
})
onMounted(() => {
  sortTable.value.map(el => {
    el.active = Object.values(props.filters).includes(el.name)
    return el
  })
})
watch(props, value => {
  sortTable.value.map(el => {
    el.active = Object.values(value.filters).includes(el.name)
    return el
  })
}, {deep: true})
const sortTable = ref([
    {
      name: t('dashboard.configuration.rooms.room'),
      active: true
    },
    {
      name: t('dashboard.configuration.rooms.type'),
      active: true
    },
    {
      name: t('dashboard.configuration.rooms.floor'),
      active: true
    },
    {
      name: t('dashboard.configuration.rooms.block'),
      active: true
    },
    {
      name: t('dashboard.configuration.rooms.devices'),
      active: true
    },
    {
      name: t('dashboard.configuration.rooms.status'),
      active: true
    },
])
const changeSort = () => {
  emits('theadSort', sortTable.value.filter(el => el.active).map(el => el.name))
}
defineComponent({name: 'ConfigurationRoomsActions'})
</script>