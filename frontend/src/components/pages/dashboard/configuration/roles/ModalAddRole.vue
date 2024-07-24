<template>
  <Modal ref="add_role">
    <template #head v-if="editID">
      <h2>{{$t('dashboard.configuration.roles.modal.edit_role_title')}} </h2>
      <p>{{$t('dashboard.configuration.roles.modal.edit_role_subtitle')}}</p>
    </template>
    <template #head v-else>
      <h2>{{$t('dashboard.configuration.roles.modal.add_role_title')}} </h2>
      <p>{{$t('dashboard.configuration.roles.modal.add_role_subtitle')}}</p>
    </template>
      <form class="ui-form">
        <UiInput
            name="user_role_name"
            :label="$t('dashboard.configuration.roles.form.name')"
            :placeholder="$t('dashboard.configuration.roles.form.name_placeholder')"
            v-model="state.name"
            :errors="validation?.$dirty ? validation?.$silentErrors : []"
        />
        <h3>{{$t('dashboard.configuration.roles.form.choose_permissions')}}</h3>
        <GroupedPermissions
            :options="sortedPermissions"
            v-model="state.permissions"
        />
      </form>
    <template #footer="{close}">
      <UiButton class="primary" @click.prevent="storeRole.editItem(close)" v-if="editID">
        {{$t('dashboard.configuration.roles.button_save')}}
      </UiButton>
      <UiButton class="primary" @click.prevent="storeRole.addItem(close)" v-else>
        {{$t('dashboard.configuration.roles.button')}}
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
import {computed, ref} from "vue";
import UiInput from "@components/ui/Input.vue";
import {useConfigurationRolesStore} from "@store/dashboard/configuration/roles.ts";
import {storeToRefs} from "pinia";
import GroupedPermissions from "@components/pages/dashboard/configuration/roles/GroupedPermissions.vue";
const add_role = ref<IModal | null>(null)
const storeRole = useConfigurationRolesStore()
const {state, editID, validation, permissions} = storeToRefs(storeRole)
const close = () => {
  add_role.value?.close()
}
const open = () => {
  add_role.value?.open()
}
const sortedPermissions = computed(() => Object.values(permissions.value.reduce((acc: GroupedPermissions, permission: IConfigurationPermissions) => {
  const { content_type, name } = permission;
  if (!acc[content_type]) {
    acc[content_type] = {
      name: '',
      permissions: []
    };
  }
  acc[content_type].permissions.push(permission);

  // Определение названия группы на основе первого найденного названия
  if (!acc[content_type].name) {
    const match = name.match(/Can (add|change|delete|view) (.+)/);
    if (match) {
      acc[content_type].name = match[2].charAt(0).toUpperCase() + match[2].slice(1);
    }
  }

  return acc;
}, {})))
interface GroupedPermissions {
  [key: number]: {
    name: string;
    permissions: IConfigurationPermissions[];
  };
}
defineExpose({
  close,
  open,
})
</script>