<template>
  <div class="card guest-list">
    <UiTable
        :headers="headers"
        :data="guests.results"
        :error="error"
        :loading="loading"
        :options="{
          elementsClass: {
            tr: (entity: any) => !entity.is_active ? 'opacity-50 select-none' : '',
          }
        }"
    >
      <template #name="{entity}">
        <div class="flex items-center gap-4">
          <UiIcon class="flex-shrink-0 w-5 h-5 stroke-primary-600 dark:stroke-gray-300" name="user" filled/>
          <div>
            <p class="text-lg font-semibold">{{entity.name}} {{entity.lastname}}</p>
            <p class="text-sm font-normal" v-if="entity.birthday">Birth Date: {{ moment.unix(entity.birthday).format('YYYY-MM-DD') }}</p>
            <p class="text-sm font-normal" v-else>Birth Date: ---</p>
          </div>
        </div>
      </template>
      <template #check_in="{entity}">
        {{ entity.check_in ? moment.unix(entity.check_in).format('YYYY-MM-DD hh:mm') : '-' }}
      </template>
      <template #check_out="{entity}">
        <div class="flex gap-3" v-if="entity.check_out">
          {{ moment.unix(entity.check_out).format('YYYY-MM-DD hh:mm') }}
          <UiBadge :class="{off: moment.unix(entity.check_out).isBefore()}">{{moment.unix(entity.check_out).startOf('milliseconds').fromNow()}}</UiBadge>
        </div>
        <span v-else>-</span>
      </template>
      <template #actions="{entity}">
        <div class="ui-table__actions" v-if="entity.is_active">
          <UiButton class="text" @click.prevent="storeCheckInOut.checkOut(entity.id)">
            <UiIcon name="x-circle" filled/>
            Check-out
          </UiButton>
<!--          <UiDropdown>-->
<!--            <template #trigger>-->
<!--              <UiButton class="text">-->
<!--                {{ $t('dashboard.rooms.table.actions') }}-->
<!--                <UiIcon name="chevron-down" filled @click.prevent/>-->
<!--              </UiButton>-->
<!--            </template>-->
<!--            <template #content>-->
<!--              <div class="dropdown__menu">-->
<!--                <div @click.prevent="storeCheckInOut.checkOut(entity.id)">Check-out</div>-->
<!--                <div @click.prevent="openMove">Move</div>-->
<!--              </div>-->
<!--            </template>-->
<!--          </UiDropdown>-->
        </div>
        <div class="ui-table__actions" v-else></div>
      </template>
    </UiTable>
  </div>
<!--  <ModalMove ref="modal_move"/>-->
</template>
<script setup lang="ts">
import UiTable from "@components/ui/Table.vue";
import {computed, onMounted} from "vue";
import UiButton from "@components/ui/Button.vue";
import UiIcon from "@components/ui/Icon.vue";
import {useCheckInOutStore} from "@store/dashboard/check-in-out";
import {storeToRefs} from "pinia";
import moment from "moment";
import UiBadge from "@components/ui/Badge.vue";
// import UiDropdown from "@components/ui/Dropdown.vue";
// import ModalMove from "@components/pages/dashboard/rooms/check-in-out/ModalMove.vue";
import {useConfigurationRoomsStore} from "@store/dashboard/configuration/rooms.ts";
// const modal_move = ref<IModal | null>(null)
const storeCheckInOut = useCheckInOutStore()
const storeRooms = useConfigurationRoomsStore()
const {guests, loading, error} = storeToRefs(storeCheckInOut)
const headers = computed<IConfigurationRoomsHead>(() => ({
  name: '',
  check_in: '',
  check_out: '',
  actions: '',
}))
onMounted( async () => {
  await Promise.all([
    storeRooms.getList({}),
    storeCheckInOut.getGuests({})
  ])
})
// const openMove = () => {
//   modal_move.value?.open()
// }
</script>