<template>
  <Modal ref="edit_room" @closed="storeConfigurationRooms.$reset()">
    <template #head>
      <h2>{{$t('dashboard.configuration.rooms.modals.edit_new_rooms.title')}} </h2>
      <p>{{$t('dashboard.configuration.rooms.modals.edit_new_rooms.subtitle')}}</p>
    </template>
    <form class="ui-form" @submit.prevent="storeConfigurationRooms.editItem(close)">

      <UiSelect
          v-if="room_types?.results"
          v-bind="selectConfig"
          v-model="state.type"
          :options="room_types?.results.map(el => el.title)"
          :title="$t('dashboard.configuration.rooms.modals.add_new_rooms.choose_room_type')"
      />
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
      <UiSelect
          v-if="devices?.results"
          v-bind="multiSelectConfig"
          v-model="state.devices"
          label="name"
          :options="devices?.results"
          :title="$t('dashboard.configuration.rooms.modals.add_new_rooms.device')"
      />
      <button class="sr-only" type="submit"></button>
    </form>

    <template #footer="{close}">
      <UiButton class="primary" @click.prevent="storeConfigurationRooms.editItem(close)">
        {{ $t('dashboard.configuration.rooms.modals.edit_new_rooms.save') }}
      </UiButton>
      <UiButton class="text" @click.prevent="close()">
        {{ $t('dashboard.configuration.rooms.modals.add_new_rooms.cancel') }}
      </UiButton>
    </template>
  </Modal>
</template>
<script setup lang="ts">
import Modal from "@components/ui/Modal.vue";
import UiButton from "@components/ui/Button.vue";
import {ref} from "vue";
import UiSelect from "@components/ui/Select.vue";
import UiInput from "@components/ui/Input.vue";
import {useConfigurationRoomsStore} from "@store/dashboard/configuration/rooms.ts";
import {storeToRefs} from "pinia";
import {useConfigurationRoomTypeStore} from "@store/dashboard/configuration/room-type.ts";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
import {multiSelectConfig, selectConfig} from "@utils/configsSelect.ts";
const edit_room = ref<IModal | null>(null)

const storeConfigurationRooms = useConfigurationRoomsStore()
const storeConfigurationRoomType = useConfigurationRoomTypeStore()
const storeConfigurationDevice = useConfigurationDeviceStore()
const {state, validation} = storeToRefs(storeConfigurationRooms)
const {room_types} = storeToRefs(storeConfigurationRoomType)
const {devices} = storeToRefs(storeConfigurationDevice)
const close = () => {
  edit_room.value?.close()
}
const open = () => {
  edit_room.value?.open()
}
// const searchDevices = async (value:string) => {
//   console.log(value)
//   await storeConfigurationDevice.searchItems(value)
// }
// const searchRoomTypes = async (value:string) => {
//   await storeConfigurationRoomType.searchItems(value)
// }

defineExpose({close, open})
</script>