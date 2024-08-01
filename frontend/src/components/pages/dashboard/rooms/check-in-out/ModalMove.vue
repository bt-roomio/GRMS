<template>
  <Modal ref="modal">
    <template #head>
      <h2>Move guest</h2>
      <p>Enter new room</p>
    </template>
    <form class="ui-form" @submit.prevent>
      <div class="ui-multiselect">
        <label>{{ $t('dashboard.configuration.rooms.modals.add_new_rooms.room_number') }}</label>
        <Multiselect
            v-model="room"
            :options="rooms.results"
            label="room_number"
            value-prop="id"
            :canClear="false"
            :canDeselect="true"
            :close-on-select="true"
            :close-on-deselect="true"
            :searchable="true"
            @searchChange="searchRoom"
            :placeholder="$t('dashboard.search_from_the_list')"
        />
      </div>
    </form>
    <template #footer="{close}">
      <UiButton v-if="roomId" class="primary" @click.prevent="storeCheckInOut.move({id: roomId, room}, close)">
        {{$t('dashboard.settings.save')}}
      </UiButton>
      <UiButton v-else class="primary" @click.prevent="storeCheckInOut.moveAll({from_room: $route.params.id, to_room: room}, close)">
        {{$t('dashboard.settings.save')}}
      </UiButton>
      <UiButton class="text" @click.prevent="close()">
        {{ $t('dashboard.configuration.rooms.modals.add_new_rooms.cancel') }}
      </UiButton>
    </template>
  </Modal>
</template>
<script setup lang="ts">
import Modal from "@components/ui/Modal.vue";
import {ref} from "vue";
import UiButton from "@components/ui/Button.vue";
import {useConfigurationRoomsStore} from "@store/dashboard/configuration/rooms.ts";
import {storeToRefs} from "pinia";
import Multiselect from "@vueform/multiselect";
import {useCheckInOutStore} from "@store/dashboard/check-in-out";
const storeCheckInOut = useCheckInOutStore()
const storeRoom = useConfigurationRoomsStore()
const {rooms, searchValue, searchType} = storeToRefs(storeRoom)
const roomId = ref(null)
const room = ref(null)
const modal = ref<IModal | null>(null)
const close = () => {
  modal.value?.close()
}
const open = (id: any) => {
  if (id) {
    roomId.value = id
  }
  modal.value?.open()
}
const searchRoom = (query: string) => {
  if (query) {
    searchType.value = 'room_number'
    searchValue.value = query
  }else {
    searchValue.value = ''
  }
}
defineExpose({
  close,
  open,
})
</script>