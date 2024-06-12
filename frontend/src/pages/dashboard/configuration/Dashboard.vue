<template>
  <div class="page" v-if="room_types">
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
        :data="room_types.results"
        :sort="['title','dashboard']"
        @sorted="storeConfigurationRoomType.sortList"
        @more="moreHandle"
        :is-pagination="room_types.count > room_types.results.length"
    >
      <template #header-select>
        <CheckAll v-model="room_types.results" />
      </template>
      <template #select="{entity}">
        <UiCheckbox v-model="entity.select"/>
      </template>
      <template #active="{entity}">
          <UiStatus :status="entity.active as string ? 'Active': 'Not active'" :class="entity.active as string ? 'on': 'off'" />
      </template>
      <template #actions="{entity}">
        <div class="ui-table__actions col-2">
          <UiButton class="secondary" @click.prevent="openEditRoomType(entity.id as string)">
            <UiIcon name="edit" filled />
          </UiButton>
          <UiButton class="text" @click.prevent="storeConfigurationRoomType.deleteItem(entity.id as string)">
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
import ModalAddDashboard from "@components/pages/dashboard/configuration/dashboard.vue/ModalAddDashboard.vue";
import ModalEditDashboard from "@components/pages/dashboard/configuration/dashboard.vue/ModalEditDashboard.vue";
const add_dashboard = ref<IModal | null>(null)
const edit_dashboard = ref<IModal | null>(null)
const {t} = useI18n()
const storeConfigurationRoomType = useConfigurationRoomTypeStore()
const {room_types, loading, error} = storeToRefs(storeConfigurationRoomType)

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
    await storeConfigurationRoomType.getItem(id, true)
    edit_dashboard.value?.open()
  }catch (e){
    console.log(e)
  }
}
onMounted(async () => {
  await storeConfigurationRoomType.getList({})
})
const moreHandle = async () => {
  await storeConfigurationRoomType.loadMore()
}
</script>