<template>
  <Modal ref="import_room">
    <template #head>
      <h2>{{$t('dashboard.configuration.rooms.modals.import_new_rooms.title')}} </h2>
      <p>{{$t('dashboard.configuration.rooms.modals.import_new_rooms.subtitle')}}</p>
    </template>
    <FileUpload class="mb-6" :accept="['.csv', '.xls']"/>
    <UiButton class="secondary w-full" @click.prevent="close()">
      {{$t('dashboard.configuration.rooms.modals.import_new_rooms.view_example')}}
    </UiButton>
    <template #footer="{close}">
      <UiButton class="primary" @click.prevent="close()">
        <UiIcon name="import" filled/>
        {{$t('dashboard.configuration.rooms.modals.import_new_rooms.title')}}
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
import UiIcon from "@components/ui/Icon.vue";
import FileUpload from "@components/ui/FileUpload.vue";
const import_room = ref<IModal | null>(null)

const close = () => import_room.value?.close()
const open = () => import_room.value?.open()


defineExpose({
  close,
  open,
})
</script>