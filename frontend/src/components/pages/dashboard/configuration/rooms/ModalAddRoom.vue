<template>
  <Modal ref="add_room" @closed="storeConfigurationRooms.$reset()">
    <template #head>
      <h2>{{$t('dashboard.configuration.rooms.modals.add_new_rooms.title')}} </h2>
      <p>{{$t('dashboard.configuration.rooms.modals.add_new_rooms.subtitle')}}</p>
    </template>
      <form class="ui-form" @submit.prevent="storeConfigurationRooms.addItem(close)">
        <div class="ui-multiselect">
          <label>{{ $t('dashboard.configuration.rooms.modals.add_new_rooms.choose_room_type') }}</label>
          <Multiselect
              v-if="room_types?.results"
              v-model="state.type"
              :options="room_types?.results.map(el => el.title)"
              :placeholder="$t('dashboard.search_from_the_list')"
              :can-clear="false"
          />
        </div>
        <UiInput
            :label="$t('dashboard.configuration.rooms.modals.add_new_rooms.room_number')"
            :placeholder="$t('dashboard.configuration.rooms.modals.add_new_rooms.room_number_placeholder')"
            v-model="state.room_number"
            name="room_number"
            :errors="validation?.$dirty ? validation?.$silentErrors : []"
        >
          <template #footer>{{ $t('dashboard.configuration.rooms.modals.add_new_rooms.room_number_example') }}</template>
        </UiInput>
        <div class="ui-form__row col-2">
          <UiInput
              :label="$t('dashboard.configuration.rooms.floor')"
              :placeholder="$t('dashboard.configuration.rooms.modals.add_new_rooms.room_floor_placeholder')"
              v-model="state.floor"
              name="floor"
              :errors="validation?.$dirty ? validation?.$silentErrors : []"
          />
          <UiInput
              :label="$t('dashboard.configuration.rooms.block')"
              :placeholder="$t('dashboard.configuration.rooms.modals.add_new_rooms.room_block_placeholder')"
              v-model="state.block"
              name="block"
              :errors="validation?.$dirty ? validation?.$silentErrors : []"
          />
        </div>
        <div class="ui-multiselect">
          <label>{{$t('dashboard.configuration.rooms.modals.add_new_rooms.device')}}</label>
          <Multiselect
              mode="tags"
              :close-on-select="false"
              :searchable="true"
              :caret="false"
              :can-clear="false"
              label="name"
              :valueProp="'id'"
              v-model="state.devices"
              :options="devices?.results"
              :placeholder="$t('dashboard.search_from_the_list')"
          />
        </div>
        <button class="sr-only" type="submit"></button>
      </form>

    <template #footer="{close}">
      <UiButton class="primary" @click.prevent="storeConfigurationRooms.addItem(close)">
        <UiIcon name="plus" filled/>
        {{ $t('dashboard.configuration.rooms.add_room') }}
      </UiButton>
      <UiButton class="text" @click.prevent="close()">
        {{ $t('dashboard.configuration.rooms.modals.add_new_rooms.cancel') }}
      </UiButton>
    </template>
  </Modal>
</template>
<script setup lang="ts">
import UiIcon from "@components/ui/Icon.vue";
import Modal from "@components/ui/Modal.vue";
import UiButton from "@components/ui/Button.vue";
import UiInput from "@components/ui/Input.vue";
import Multiselect from "@vueform/multiselect"

import {onMounted, ref} from "vue";
import {useConfigurationRoomsStore} from "@store/dashboard/configuration/rooms.ts";
import {storeToRefs} from "pinia";
import {useConfigurationRoomTypeStore} from "@store/dashboard/configuration/room-type.ts";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
const add_room = ref<IModal | null>(null)
const storeConfigurationRooms = useConfigurationRoomsStore()
const storeConfigurationRoomType = useConfigurationRoomTypeStore()
const storeConfigurationDevice = useConfigurationDeviceStore()
const {state, validation} = storeToRefs(storeConfigurationRooms)
const {room_types} = storeToRefs(storeConfigurationRoomType)
const {devices} = storeToRefs(storeConfigurationDevice)
const close = () => {
  add_room.value?.close()
}
const open = () => {
  add_room.value?.open()
}

onMounted(async () => {
  await Promise.all([
    storeConfigurationRoomType.getList({}),
    storeConfigurationDevice.getList(),
  ])
})

defineExpose({
  close,
  open,
})
</script>