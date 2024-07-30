<template>
  <Modal ref="modal">
    <template #head>
      <h2>Move guest</h2>
      <p>Enter new room</p>
    </template>
    <form class="ui-form" @submit.prevent>
      <UiInput
          name="room"
          v-model="room"
          label="Room"
          placeholder="Enter new room"
      />
    </form>
    <template #footer="{close}">
      <UiButton class="primary">
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
import UiInput from "@components/ui/Input.vue";
import UiButton from "@components/ui/Button.vue";
const room = ref(null)
const modal = ref<IModal | null>(null)
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