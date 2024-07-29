<template>
  <div class="page">
    <div class="page__content">
      <PageHead
          :title="$t('dashboard.configuration.roles.title')"
          :description="$t('dashboard.configuration.roles.subtitle')"
          :button="storePermissions.hasPermission('add_group') ? $t('dashboard.configuration.roles.button') : undefined"
          button-icon="plus"
          @click-button="openModalRole"
      />
      <UiTable
          :loading="loading"
          :error="error"
          :is-search-open="false"
          :headers="headers"
          :data="roles as any[]"
          :sort="['email', 'first_name']"
          @more="moreHandle"
          :is-pagination="false"
      >
        <template #header-select>
          <CheckAll v-model="roles" />
        </template>
        <template #select="{entity}">
          <UiCheckbox @click.stop v-model="entity.select"/>
        </template>
        <template #name="{entity}">
          <p class="whitespace-nowrap">{{(entity as IRole).name}}</p>
        </template>
        <template #permissions="{entity}">
          <div class="flex flex-wrap gap-1" v-if="transformPermissions((entity as IRole).permissions).length < 10">
            <UiBadge v-for="item in transformPermissions((entity as IRole).permissions)" :key="item.name">{{item.name}}({{actionParse(item.children)}})</UiBadge>
          </div>
          <div class="flex flex-wrap gap-1" v-else>
            <UiBadge v-for="item in transformPermissions((entity as IRole).permissions).splice(0, 7)" :key="item.name">{{item.name}}({{actionParse(item.children)}})</UiBadge>
            <UiBadge> +{{transformPermissions((entity as IRole).permissions).length - 7 }}</UiBadge>
          </div>
        </template>
        <template #actions="{entity}">
          <div class="ui-table__actions col-2">
            <UiButton class="secondary" v-if="storePermissions.hasPermission('change_group')" @click.prevent="openEditRole(entity.id)">
              <UiIcon name="edit" filled />
            </UiButton>
            <UiButton class="text" v-if="storePermissions.hasPermission('delete_group')" @click.prevent="storeRole.deleteItem(entity.id)">
              <UiIcon name="trash" filled />
            </UiButton>
          </div>
        </template>
      </UiTable>
    </div>
  </div>
  <ModalAddRole ref="modal_role"/>
</template>
<script setup lang="ts">
import PageHead from "@components/pages/dashboard/PageHead.vue";
import ModalAddRole from "@components/pages/dashboard/configuration/roles/ModalAddRole.vue";
import {computed, onMounted, onUnmounted, ref} from "vue";
import UiCheckbox from "@components/ui/Checkbox.vue";
import UiTable from "@components/ui/Table.vue";
import CheckAll from "@components/ui/CheckAll.vue";
import UiIcon from "@components/ui/Icon.vue";
import UiButton from "@components/ui/Button.vue";
import {useConfigurationRolesStore} from "@store/dashboard/configuration/roles.ts";
import {storeToRefs} from "pinia";
import router from "@/router";
import {useI18n} from "vue-i18n";
import UiBadge from "@components/ui/Badge.vue";
import {usePermissions} from "@store/dashboard/user/permissions.ts";
const storePermissions = usePermissions()

const {t} = useI18n()
const storeRole = useConfigurationRolesStore()
const {roles, editID, loading, error, role} = storeToRefs(storeRole)
const modal_role = ref<IModal | null>()
const openModalRole = async () => {
  modal_role.value?.open()
}
const headers = computed(() => ({
  select: true,
  name: t('dashboard.configuration.roles.table.name'),
  permissions: t('dashboard.configuration.roles.table.access'),
  actions: ''
}))
const openEditRole = async (id: string) => {
  try {
    editID.value = id
    await storeRole.getItem(id, true)
    modal_role.value?.open()
  }catch (e){
    console.log(e)
  }
}
const moreHandle = async () => {
  await storeRole.loadMore()
}

onMounted(async () => {
  await Promise.all([
    storeRole.getList(router.currentRoute.value.query),
    storeRole.getPermissions()
  ])
})
onUnmounted(() => {
  role.value = null
  roles.value = []
  error.value = {code: null, msg: null}
  storeRole.$reset()
})
interface Permission {
  id: number;
  name: string;
  codename: string;
  content_type: number;
}

interface GroupedPermission {
  name: string;
  children: string[];
}
function transformPermissions(permissions: Permission[]): GroupedPermission[] {
  const actionMap: { [key: string]: string } = {
    add: 'Create',
    change: 'Update',
    delete: 'Delete',
    view: 'Read'
  };

  const grouped = permissions.reduce((acc: { [key: number]: { name: string, children: string[] } }, permission) => {
    const { content_type, name } = permission;
    if (!acc[content_type]) {
      acc[content_type] = { name: '', children: [] };
    }

    const match = name.match(/Can (add|change|delete|view) (.+)/);
    if (match) {
      acc[content_type].children.push(actionMap[match[1]]);
      if (!acc[content_type].name) {
        acc[content_type].name = match[2].charAt(0).toUpperCase() + match[2].slice(1);
      }
    }

    return acc;
  }, {});

  return Object.values(grouped);
}
const actionParse = (actions: string[]) => {
  if (JSON.stringify(actions) === JSON.stringify(['Create', 'Update', 'Delete', 'Read'])){
    return 'All'
  }else {
    return actions.join(', ')
  }
}
interface IRole {
  id?: string
  name: string
  permissions: any[]
}
</script>