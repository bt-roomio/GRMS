<template>
  <div class="page">
    <div class="page__content">
      <UiLoader v-if="itemLoading"/>
      <PageHead
          v-if="room"
          back-to="/rooms/room-list"
          :back="$t('dashboard.rooms.back_to_rooms')"
          :title="`${$t('dashboard.rooms.table.room_number')} ${room.room_number}, ${$t('dashboard.rooms.table.floor')} ${room.floor}, ${$t('dashboard.rooms.table.block')} ${room.block}`"
      >
        <template #button>
          <div class="page-head__action row">
            <UiDropdown v-if="$route.query.tab === 'guests'">
              <template #trigger>
                <UiButton class="text">
                  {{ $t('dashboard.rooms.table.actions') }}
                  <UiIcon name="chevron-down" filled @click.prevent/>
                </UiButton>
              </template>
              <template #content>
                <div class="dropdown__menu">
                  <div @click.prevent="openCheckIn">Check-In guest</div>
                  <div @click.prevent="openMove">Move all guest</div>
                </div>
              </template>
            </UiDropdown>
            <Button @click.prevent class="text">
              <UiIcon name="settings" filled />
            </Button>
          </div>
        </template>
      </PageHead>
      <RoomActions v-if="room" :item="room"/>
      <Tabs :list="tabList"/>
      <WidgetContainer
          v-if="viewModel && !$route.query.tab"
          :isSettings="false"
          v-model="viewModel"
          :widgets="viewWidgets"
      />
      <GuestList v-if="$route.query.tab === 'guests'"/>
    </div>
  </div>
  <ModalCheckIn ref="modal_check_in"/>
  <ModalMove ref="modal_move"/>
</template>
<script setup lang="ts">
import PageHead from "@components/pages/dashboard/PageHead.vue";
import RoomActions from "@components/pages/dashboard/rooms/RoomActions.vue";
import Tabs from "@components/ui/Tabs.vue";
import {computed, onMounted, onUnmounted, ref} from "vue";
import {useI18n} from "vue-i18n";
import WidgetContainer from "@components/widgets/WidgetContainer.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import {storeToRefs} from "pinia";
import {useConfigurationRoomsStore} from "@store/dashboard/configuration/rooms.ts";
import {useRoute} from "vue-router";
import UiLoader from "@components/ui/Loader.vue";
import Button from "@components/ui/Button.vue";
import UiIcon from "@components/ui/Icon.vue";
import ModalCheckIn from "@components/pages/dashboard/rooms/check-in-out/ModalCheckIn.vue";
import GuestList from "@components/pages/dashboard/rooms/GuestList.vue";
import UiDropdown from "@components/ui/Dropdown.vue";
import UiButton from "@components/ui/Button.vue";
import ModalMove from "@components/pages/dashboard/rooms/check-in-out/ModalMove.vue";
const modal_move = ref<IModal | null>(null)

const modal_check_in = ref<IModal | null>(null)
const storeConfigurationDashboard = useConfigurationDashboardStore()
const storeConfigurationRooms = useConfigurationRoomsStore()
const {itemLoading, room} = storeToRefs(storeConfigurationRooms)
const {
  viewModel,
  viewWidgets,
} = storeToRefs(storeConfigurationDashboard)
const {t} = useI18n()
const {params} = useRoute()
const tabList = computed(() => [
  {
    name: 'Room controls',
    to: {name: 'room-inner'},
  },
  {
    name: t('dashboard.menu.backlog'),
    to: {name: 'room-inner', query: { tab: 'backlog' }},
  },
  {
    name: 'HVAC',
    to: {name: 'room-inner', query: { tab: 'HVAC' }},
  },
  {
    name: 'Guests',
    to: {name: 'room-inner', query: { tab: 'guests'}},
  }
])
onMounted(async () => {
  await storeConfigurationRooms.getItem(params.id as string, false)
  if (room.value?.type?.dashboard){
    await storeConfigurationDashboard.getItem(room.value?.type.dashboard.id as string, false)
    await storeConfigurationDashboard.getDashboardInnerHelpers()
  }
})
onUnmounted(() => {
  storeConfigurationDashboard.$reset()
  storeConfigurationDashboard.$resetData()
})
const openCheckIn = () => {
  modal_check_in.value?.open()
}
const openMove = () => {
  modal_move.value?.open()
}
</script>