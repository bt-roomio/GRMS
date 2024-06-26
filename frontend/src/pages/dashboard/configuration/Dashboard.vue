<template>
  <div class="page" v-if="dashboards">
    <div class="page__content">
      <PageHead
          :title="$t('dashboard.menu.dashboard')"
          :description="'Edit your dashboard list'"
          :button="'Add  dashboard'"
          button-icon="plus"
          @click-button="openAddDashboard"
      />
    </div>
    <UiTable
        :loading="loading"
        :error="error"
        :headers="headers"
        :data="dashboards.results"
        :sort="['title','dashboard']"
        @sorted="storeConfigurationDashboard.sortList"
        @more="moreHandle"
        :is-pagination="dashboards.count > dashboards.results.length"
        @click="toPage"
        pointer
    >
      <template #header-select>
        <CheckAll v-model="dashboards.results" />
      </template>
      <template #select="{entity}">
        <UiCheckbox @click.stop v-model="entity.select"/>
      </template>
      <template #active="{entity}">
          <UiStatus :status="entity.active as string ? 'Active': 'Not active'" :class="entity.active as string ? 'on': 'off'" />
      </template>
      <template #actions="{entity}">
        <div class="ui-table__actions col-2">
          <UiButton class="secondary" @click.stop="openEditRoomType(entity.id as string)">
            <UiIcon name="edit" filled />
          </UiButton>
          <UiButton class="text" @click.stop="storeConfigurationDashboard.deleteItem(entity.id as string)">
            <UiIcon name="trash" filled />
          </UiButton>
        </div>

      </template>
    </UiTable>
    <ModalAddDashboard ref="add_dashboard"/>
    <ModalEditDashboard ref="edit_dashboard"/>
  </div>
</template>
<script setup lang="ts">
import PageHead from "../../../components/pages/dashboard/PageHead.vue";
import UiTable from "@components/ui/Table.vue";
import UiButton from "@components/ui/Button.vue";
import UiIcon from "@components/ui/Icon.vue";
import UiCheckbox from "@components/ui/Checkbox.vue";
import CheckAll from "@components/ui/CheckAll.vue";
import {useConfigurationRoomTypeStore} from "@store/dashboard/configuration/room-type.ts";
import {storeToRefs} from "pinia";
import {computed, onMounted, ref} from "vue";
import {useI18n} from "vue-i18n";
import UiStatus from "@components/ui/Status.vue";
import ModalAddDashboard from "@components/pages/dashboard/configuration/dashboard/ModalAddDashboard.vue";
import ModalEditDashboard from "@components/pages/dashboard/configuration/dashboard/ModalEditDashboard.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import {useRouter} from "vue-router";
const {push} = useRouter()
const add_dashboard = ref<IModal | null>(null)
const edit_dashboard = ref<IModal | null>(null)
const {t} = useI18n()
const storeConfigurationDashboard = useConfigurationDashboardStore()
const storeConfigurationRoomType = useConfigurationRoomTypeStore()

const {dashboards, loading, error} = storeToRefs(storeConfigurationDashboard)

const headers = computed<IConfigurationRoomsHead>(() => ({
  select: true,
  title: t('dashboard.configuration.room_type.name'),
  dashboard: t('dashboard.configuration.room_type.title'),
  active: '',
  actions: ''
}))

const openAddDashboard = () => {
  add_dashboard.value?.open()
}
const openEditRoomType = async (id: string) => {
  try {
    await storeConfigurationDashboard.getItem(id, true)
    edit_dashboard.value?.open()
  }catch (e){
    console.log(e)
  }
}
onMounted(async () => {
  await Promise.all([
    storeConfigurationDashboard.getList({}),
    storeConfigurationRoomType.getList({})
  ])
})
const moreHandle = async () => {
  await storeConfigurationDashboard.loadMore()
}
const toPage = async (entity: any) => {
  await push({name: 'configuration-dashboard-inner', params: {id: entity.id}})
}
</script>