<template>
  <div class="page">
    <div class="page__content">
      <PageHead
          :title="$t('dashboard.configuration.users.title')"
          :description="$t('dashboard.configuration.users.subtitle')"
          :button="$t('dashboard.configuration.users.button')"
          button-icon="plus"
          @click-button="openModalUser"
      />
    </div>
    <div class="rooms__actions">
      <span></span>
      <ConfigurationUsersActions
          v-model:search="isSearchOpen"
          ref="actions"
          @theadSort="theadSortHandle"
          :filters="sortedHeaders ? sortedHeaders : headers"
      />
    </div>
    <UiTable
        :loading="loading"
        :error="error"
        v-model:searchType="searchType"
        v-model:searchValue="searchValue"
        :is-search-open="isSearchOpen"
        :search-types="searchTypes"
        :headers="sortedHeaders ? sortedHeaders : headers"
        :data="users.results"
        :sort="['email', 'first_name']"
        @sorted="storeUser.sortList"
        @more="moreHandle"
        :is-pagination="users.count > users.results.length"
    >
      <template #header-select>
        <CheckAll v-model="users.results" />
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
import {computed, onMounted, onUnmounted, ref, watch} from "vue";
import {useI18n} from "vue-i18n";
import UiTable from "@components/ui/Table.vue";
import CheckAll from "@components/ui/CheckAll.vue";
import UiCheckbox from "@components/ui/Checkbox.vue";
import UiIcon from "@components/ui/Icon.vue";
import UiButton from "@components/ui/Button.vue";
import {useUserStore} from "@store/dashboard/user";
import {storeToRefs} from "pinia";
import ModalAddUser from "@components/pages/dashboard/configuration/users/ModalAddUser.vue";
import ConfigurationUsersActions from "@components/pages/dashboard/configuration/users/Actions.vue";
import {onBeforeRouteUpdate} from "vue-router";
import router from "@/router";
import {useConfigurationRolesStore} from "@store/dashboard/configuration/roles.ts";
const storeRoles = useConfigurationRolesStore()
const storeUser = useUserStore()
const {users, editID, searchType, searchValue, loading, error, size, user, sortedData, profile} = storeToRefs(storeUser)
const isSearchOpen = ref(false)
const {t} = useI18n()
const modal_user = ref()
const actions = ref<IConfigurationUsersActions | null>(null)
const headers = computed<IConfigurationRoomsHead>(() => ({
  select: true,
  email: t('dashboard.configuration.users.form.email_address'),
  first_name: t('dashboard.configuration.users.form.first_name'),
  last_name: t('dashboard.configuration.users.form.last_name'),
  phone: t('dashboard.configuration.users.form.phone'),
  actions: ''
}))
const searchTypes = computed(() => [
  {
    name: t('dashboard.configuration.users.form.first_name'),
    key: 'first_name'
  },
  {
    name: t('dashboard.configuration.users.form.email_address'),
    key: 'email'
  },
  {
    name: t('dashboard.configuration.users.form.phone'),
    key: 'phone'
  },
])
const openEditUser = async (id: string) => {
  try {
    editID.value = id
    await storeUser.getUser(id, true)
    modal_user.value.open()
  }catch (e){
    console.log(e)
  }
}
const openModalUser = async () => {
    modal_user.value.open()
}
const sortedHeaders = computed(() => {
  const columns = profile.value?.additional_info?.[router.currentRoute.value.path]?.columnFilters || null
  if (columns) {
    const importantKeys = ['select', 'actions']
    const results: any = {}

    for (const headersKey in headers.value) {
      if ([...columns, ...importantKeys].includes(headersKey as string)){
        results[headersKey] = headers.value[headersKey]
      }
    }
    return results
  } else {
    return null
  }
});
const theadSortHandle = (array: string[]) => {
  let results: any = {}
  results.select = true
  for (const headersKey in headers.value) {
    if (array.includes(headers.value[headersKey] as string)){
      results[headersKey] = headers.value[headersKey]
    }
  }
  results.actions = ''
  const key = Object.keys(results)
  storeUser.saveUserConfiguration(router.currentRoute.value.path, { columnFilters: key });
}

watch(isSearchOpen, value => {
  if (!value) {
    searchValue.value = ''
  }
})
const moreHandle = async () => {
  await storeUser.loadMore()
}

onBeforeRouteUpdate(async (to) => {
  await storeUser.getUsers(to.query)
})
onMounted(async () => {
  await Promise.all([
    storeUser.getUsers(router.currentRoute.value.query),
    storeRoles.getList({})
  ])
})
onUnmounted(() => {
  size.value = 10
  user.value = null
  users.value = {results: [], count: 0}
  searchValue.value = ''
  searchType.value = 'first_name'
  error.value = {code: null, msg: null}
  sortedData.value = {}
  storeUser.$reset()
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