<template>
  <Modal ref="edit_room_type" @closed="storeConfigurationRoomType.$reset()">
    <template #head>
      <h2>{{$t('dashboard.configuration.room_type.modals.edit_new_room_type.title')}} </h2>
      <p>{{$t('dashboard.configuration.room_type.modals.edit_new_room_type.subtitle')}}</p>
    </template>
    <form class="ui-form" @submit.prevent="storeConfigurationRoomType.editItem(close)">
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
      <!--          v-if="dashboards?.results"-->
      <!--          v-bind="multiSelectConfig"-->
      <!--          v-model="state.dashboards"-->
      <!--          :options="dashboards?.results.map(el => el.name)"-->
      <!--          :title="$t('dashboard.configuration.room_type.modals.edit_new_room_type.choose_dashboard')"-->
      <!--      />-->
      <button class="sr-only" type="submit"></button>
    </form>

    <template #footer="{close}">
      <UiButton class="primary" @click.prevent="storeConfigurationRoomType.editItem(close)">
        {{ $t('dashboard.configuration.room_type.modals.edit_new_room_type.save') }}
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
import {useConfigurationRoomTypeStore} from "@store/dashboard/configuration/room-type.ts";
const edit_room_type = ref<IModal | null>(null)
const storeConfigurationRoomType = useConfigurationRoomTypeStore()
const {state, validation} = storeToRefs(storeConfigurationRoomType)
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