<template>
  <Modal ref="export_room">
    <template #head>
      <h2>{{$t('dashboard.configuration.rooms.modals.export_new_rooms.title')}} </h2>
      <p>{{$t('dashboard.configuration.rooms.modals.export_new_rooms.subtitle')}}</p>
    </template>
    <div class="ui-form">
      <UiButton class="primary" @click.prevent="close()">
        XLS
      </UiButton>
      <UiButton class="primary" @click.prevent="close()">
        CSV
      </UiButton>
    </div>
    <template #footer="{close}">
      <UiButton class="secondary" @click.prevent="close()">
        {{ $t('dashboard.configuration.rooms.modals.add_new_rooms.cancel') }}
      </UiButton>
    </template>
  </Modal>
</template>
<script setup lang="ts">
import Modal from "@components/ui/Modal.vue";
import UiButton from "@components/ui/Button.vue";
import {ref} from "vue";
const export_room = ref<IModal | null>(null)

const close = () => export_room.value?.close()
const open = () => export_room.value?.open()


defineExpose({
  close,
  open,
})
</script>