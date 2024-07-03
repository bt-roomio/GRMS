<template>
  <Modal ref="edit_room_type" @closed="storeConfigurationDashboard.$reset()">
    <template #head>
      <h2>{{$t('dashboard.configuration.dashboard.modal.edit_title')}}</h2>
      <p>{{$t('dashboard.configuration.dashboard.modal.edit_subtitle')}}</p>
    </template>
    <div class="modal__card">
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
        <button class="sr-only" type="submit"></button>
      </form>
    </div>

    <template #footer="{close}">
      <UiButton class="primary" @click.prevent="storeConfigurationDashboard.editItem(close)">
        {{$t('dashboard.configuration.dashboard.modal.edit_button')}}
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
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
const edit_room_type = ref<IModal | null>(null)
const storeConfigurationDashboard = useConfigurationDashboardStore()
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