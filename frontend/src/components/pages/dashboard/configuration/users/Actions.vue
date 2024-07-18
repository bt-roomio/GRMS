<template>
  <div class="rooms__buttons">
    <UiIcon name="search" v-tooltip="$t('dashboard.search')" filled @click.prevent="search = !search"/>
<!--    <UiIcon name="download" v-tooltip="$t('dashboard.configuration.rooms.modals.export_new_rooms.title')" class="rotate-180" filled @click.prevent="openExportRoom"/>-->
<!--    <UiIcon name="download" v-tooltip="$t('dashboard.configuration.rooms.modals.import_new_rooms.title')" @click.prevent="openImportRoom" filled/>-->
    <UiDropdown>
      <template #trigger>
        <UiIcon name="settings" v-tooltip="$t('dashboard.settings.title')" filled/>
      </template>
      <template #content>
        <div class="dropdown__menu">
          <UiCheckbox
              v-for="(header, i) in sortTable"
              :key="`${header}${i}`"
              class="w-full"
              @change="changeSort"
              v-model="header.active"
          >
            {{header.name}}
          </UiCheckbox>
        </div>
      </template>
    </UiDropdown>
  </div>
  <ModalAddUser ref="add_user"/>
</template>
<script setup lang="ts" generic="T">
import {defineComponent, ref} from "vue";
import UiIcon from "@components/ui/Icon.vue";
import UiDropdown from "@components/ui/Dropdown.vue";
import {useI18n} from "vue-i18n";
import UiCheckbox from "@components/ui/Checkbox.vue";
import ModalAddUser from "@components/pages/dashboard/configuration/users/ModalAddUser.vue";
const add_user = ref<IModal | null>(null)
const edit_user = ref<IModal | null>(null)
const search = defineModel('search')
const {t} = useI18n()
const emits = defineEmits(['theadSort'])

defineExpose({
  add_user,
  edit_user,
})

const sortTable = ref([
    {
      name: t('dashboard.configuration.users.form.email_address'),
      active: true
    },
    {
      name: t('dashboard.configuration.users.form.first_name'),
      active: true
    },
    {
      name: t('dashboard.configuration.users.form.last_name'),
      active: true
    },
    {
      name: t('dashboard.configuration.users.form.phone'),
      active: true
    },
])
const changeSort = () => {
  emits('theadSort', sortTable.value.filter(el => el.active).map(el => el.name))
}
defineComponent({name: 'ConfigurationUsersActions'})
</script>