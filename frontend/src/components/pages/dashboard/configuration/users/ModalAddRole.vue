<template>
  <Modal ref="add_role">
    <template #head>
      <h2>{{$t('dashboard.configuration.users.modal.add_role_title')}} </h2>
      <p>{{$t('dashboard.configuration.users.modal.add_role_subtitle')}}</p>
    </template>
      <form class="ui-form">
        <UiInput
            name="user_role_name"
            :label="$t('dashboard.configuration.users.form.user_role_name')"
            :placeholder="$t('dashboard.configuration.users.form.user_role_name_placeholder')"
        />
        <h3>{{$t('dashboard.configuration.users.modal.choose_settings_permissions')}}</h3>
        <div>
          <UiCheckbox>Rooms</UiCheckbox>
          <UiCheckbox>Public Space</UiCheckbox>
          <UiCheckbox>Scenario</UiCheckbox>
          <UiCheckbox>Directory</UiCheckbox>
          <UiCheckbox>Settings</UiCheckbox>
          <UiCheckbox>Access</UiCheckbox>
          <UiCheckbox>Backlog</UiCheckbox>
        </div>

        <CheckboxTree />
      </form>
    <template #footer="{close}">
      <UiButton class="primary" @click.prevent="close()">
        {{$t('dashboard.configuration.users.modal.add_role_button')}}
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
import UiInput from "@components/ui/Input.vue";
import UiCheckbox from "@components/ui/Checkbox.vue";
import CheckboxTree from "@components/ui/CheckboxTree.vue";
const add_role = ref<IModal | null>(null)
const close = () => {
  add_role.value?.close()
}
const open = () => {
  add_role.value?.open()
}

defineExpose({
  close,
  open,
})
</script>