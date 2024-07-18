<template>
  <Modal ref="modal" @closed="storeConfigurationDashboard.$reset()">
    <template #head>
      <h2>{{ $t('dashboard.configuration.dashboard.modal.add_title') }}</h2>
      <p>{{ $t('dashboard.configuration.dashboard.modal.add_subtitle') }}</p>
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
      <button class="sr-only" type="submit"></button>
    </form>

    <template #footer="{close}">
      <UiButton class="primary" @click.prevent="storeConfigurationDashboard.addItem(close)">
        <UiIcon name="plus" filled/>
        {{ $t('dashboard.configuration.dashboard.modal.add_button') }}
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
import {ref} from "vue";
import {storeToRefs} from "pinia";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";

const modal = ref<IModal | null>(null)
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {state, validation} = storeToRefs(storeConfigurationDashboard)
const close = () => {
  modal.value?.close()
}
const open = () => {
  modal.value?.open()
}

defineExpose({
  close,
  open,
})
</script>