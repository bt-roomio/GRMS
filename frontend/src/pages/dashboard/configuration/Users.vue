<template>
  <div class="page">
    <div class="page__content">
      <PageHead
          :title="$t('dashboard.configuration.users.title')"
          :description="$t('dashboard.configuration.users.subtitle')"
          :buttons="buttons"
          button-icon="plus"
          @click-button="clickButtonHandle"
      />
    </div>
    <UiTable
        :loading="loading"
        :error="error"
        :headers="headers"
        :data="users"
        :sort="[]"
        :is-pagination="false"
    >
      <template #header-select>
        <CheckAll v-model="users" />
      </template>
      <template #select="{entity}">
        <UiCheckbox @click.stop v-model="entity.select"/>
      </template>
      <template #name="{entity}">
        {{(entity as IUser).first_name}} {{(entity as IUser).last_name}}
      </template>
      <template #actions="{entity}">
        <div class="ui-table__actions col-2">
          <UiButton class="secondary" @click.prevent="openEditUser(entity.id)">
            <UiIcon name="edit" filled />
          </UiButton>
          <UiButton class="text" @click.prevent="storeUser.deleteUser(entity.id)">
            <UiIcon name="trash" filled />
          </UiButton>
        </div>
      </template>
    </UiTable>
  </div>
  <ModalAddUser ref="modal_user"/>
</template>
<script setup lang="ts">
import PageHead from "@components/pages/dashboard/PageHead.vue";
import {computed, onMounted, ref} from "vue";
import {useI18n} from "vue-i18n";
import UiTable from "@components/ui/Table.vue";
import CheckAll from "@components/ui/CheckAll.vue";
import UiCheckbox from "@components/ui/Checkbox.vue";
import UiIcon from "@components/ui/Icon.vue";
import UiButton from "@components/ui/Button.vue";
import {useUserStore} from "@store/dashboard/user";
import {storeToRefs} from "pinia";
import ModalAddUser from "@components/pages/dashboard/configuration/users/ModalAddUser.vue";
const storeUser = useUserStore()
const {users, editID} = storeToRefs(storeUser)
const {t} = useI18n()
const error = ref({code: null, msg: null})
const modal_user = ref()
const loading = ref(false)
const buttons = computed(() => {
  return [
    // {name: t('dashboard.configuration.users.button_role'), icon: 'plus', id: 'add-role', class: 'text'},
    {name: t('dashboard.configuration.users.button'), icon: 'plus', id: 'add-user'}
  ]
})
const actions = ref<IConfigurationUsersActions | null>(null)
const headers = computed<IConfigurationRoomsHead>(() => ({
  select: true,
  email: t('dashboard.configuration.users.form.email_address'),
  name: t('dashboard.configuration.users.form.name'),
  phone: t('dashboard.configuration.users.form.phone'),
  actions: ''
}))

const openEditUser = async (id: string) => {
  try {
    editID.value = id
    await storeUser.getUser(id, true)
    modal_user.value.open()
  }catch (e){
    console.log(e)
  }
}
const clickButtonHandle = async (evt: any) => {
  if (evt.id === 'add-user'){
    modal_user.value.open()
  }else {
    actions.value?.add_role.open()
  }
}

onMounted(async () => {
  loading.value = true
  await storeUser.getUsers()
  loading.value = false
})
interface IUser {
  id?: string
  first_name?: string
  last_name?: string
  email?: string
  additional_info?: null | any
  phone?: null | any
  created_at?: number
  tenant_id?: string
  groups?: any[]
}
</script>