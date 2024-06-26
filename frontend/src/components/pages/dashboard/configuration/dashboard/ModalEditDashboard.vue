<template>
  <Modal ref="edit_room_type" @closed="storeConfigurationDashboard.$reset()">
    <template #head>
      <h2>Edit new dashboard  </h2>
      <p>Edit a new room in your hotel</p>
    </template>
    <form class="ui-form" @submit.prevent="storeConfigurationDashboard.addItem(close)">
      <UiInput
          :label="$t('dashboard.configuration.room_type.name')"
          :placeholder="$t('dashboard.configuration.room_type.modals.add_new_room_type.name_placeholder')"
          v-model="state.title"
          name="title"
          :errors="validation?.$dirty ? validation?.$silentErrors : []"
          icon="help-circle"
          icon-position="right"
      />
<!--      <UiSelect-->
<!--          v-if="room_types?.results"-->
<!--          v-bind="multiSelectConfig"-->
<!--          v-model="state.type"-->
<!--          :options="room_types?.results.map(el => el.title)"-->
<!--          :title="$t('dashboard.configuration.rooms.modals.add_new_rooms.choose_room_type')"-->
<!--      />-->
<!--      <UiToggle>-->
<!--        Active-->
<!--      </UiToggle>-->

      <button class="sr-only" type="submit"></button>
    </form>

    <template #footer="{close}">
      <UiButton class="primary" @click.prevent="storeConfigurationDashboard.editItem(close)">
        Save dashboard
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
import UiInput from "@components/ui/Input.vue";
import {ref} from "vue";
import {storeToRefs} from "pinia";
// import {useConfigurationRoomTypeStore} from "@store/dashboard/configuration/room-type.ts";
// import {multiSelectConfig} from "@utils/configsSelect.ts";
// import UiSelect from "@components/ui/Select.vue";
// import UiToggle from "@components/ui/Toggle.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
const edit_room_type = ref<IModal | null>(null)
// const storeConfigurationRoomType = useConfigurationRoomTypeStore()
const storeConfigurationDashboard = useConfigurationDashboardStore()
// const {room_types} = storeToRefs(storeConfigurationRoomType)
const {state, validation} = storeToRefs(storeConfigurationDashboard)
const close = () => {
  edit_room_type.value?.close()
}
const open = () => {
  edit_room_type.value?.open()
}

defineExpose({
  close,
  open,
})
</script>