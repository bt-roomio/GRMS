<template>
  <div class="rooms__buttons">
    <div>
      <UiIcon name="search" v-tooltip="$t('dashboard.search')" filled @click.prevent="search = !search"/>
    </div>
    <div>
      <UiIcon name="download" v-tooltip="$t('dashboard.configuration.rooms.modals.export_new_rooms.title')" class="rotate-180" filled @click.prevent="openExportRoom"/>
    </div>
    <div>
      <UiIcon name="download" v-tooltip="$t('dashboard.configuration.rooms.modals.import_new_rooms.title')" @click.prevent="openImportRoom" filled/>
    </div>
    <div v-if="isTable" @click.prevent="changeListToTable">
      <UiIcon name="dots-grid" v-tooltip="$t('dashboard.rooms.change_grid')" filled/>
    </div>
    <div v-else @click.prevent="changeListToTable">
      <UiIcon name="list" v-tooltip="$t('dashboard.rooms.change_list')" filled/>
    </div>
    <UiDropdown v-if="isTable">
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
  <ModalExportRooms ref="export_room"/>
  <ModalImportRooms ref="import_room"/>
</template>
<script setup lang="ts" generic="T">
import {defineComponent, onMounted, ref, watch} from "vue";
import UiIcon from "@components/ui/Icon.vue";
import ModalExportRooms from "@components/pages/dashboard/configuration/rooms/ModalExportRooms.vue";
import ModalImportRooms from "@components/pages/dashboard/configuration/rooms/ModalImportRooms.vue";
import router from "@/router";
import {useUserStore} from "@store/dashboard/user";
import UiCheckbox from "@components/ui/Checkbox.vue";
import UiDropdown from "@components/ui/Dropdown.vue";
import {useI18n} from "vue-i18n";
const props = defineProps(['filters'])
const {t} = useI18n()
const storeUser = useUserStore()
const export_room = ref<IModal | null>(null)
const import_room = ref<IModal | null>(null)
const search = defineModel('search')
const isTable = defineModel('isTable')
const emits = defineEmits(['theadSort'])
const openExportRoom = () => export_room.value?.open()
const openImportRoom = () => import_room.value?.open()
const changeListToTable = () => {
  storeUser.saveUserConfiguration(router.currentRoute.value.path, { isTable: !isTable.value });
}
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
    name: t('dashboard.rooms.table.room_number'),
    active: true
  },
  {
    name: t('dashboard.rooms.table.floor'),
    active: true
  },
  {
    name: t('dashboard.rooms.table.block'),
    active: true
  },
  {
    name: t('dashboard.rooms.table.type'),
    active: true
  },
  {
    name: t('dashboard.rooms.table.temp'),
    active: true
  },
  {
    name: 'MUR',
    active: true
  },
  {
    name: 'DND',
    active: true
  },
  {
    name: t('dashboard.rooms.table.device'),
    active: true
  },
])
const changeSort = () => {
  emits('theadSort', sortTable.value.filter(el => el.active).map(el => el.name))
}
defineComponent({name: 'RoomsActions'})
</script>