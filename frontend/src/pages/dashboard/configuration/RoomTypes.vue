<template>
  <div class="page" v-if="room_types">
    <div class="page__content">
      <PageHead
          :title="$t('dashboard.configuration.room_type.title')"
          :description="$t('dashboard.configuration.room_type.subtitle')"
          :button="$t('dashboard.configuration.room_type.add_room_type')"
          button-icon="plus"
          @click-button="openAddRoomType"
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
        <UiCheckbox @click.stop v-model="entity.select"/>
      </template>
      <template #dashboard="{entity}">
        <UiBadge>{{(entity as Entity).dashboard?.title || '-'}}</UiBadge>
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
    <ModalAddRoomType ref="add_room_type"/>
    <ModalEditRoomType ref="edit_room_type"/>
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
import ModalAddRoomType from "@components/pages/dashboard/configuration/room-type/ModalAddRoomType.vue";
import ModalEditRoomType from "@components/pages/dashboard/configuration/room-type/ModalEditRoomType.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import UiBadge from "@components/ui/Badge.vue";
const add_room_type = ref<IModal | null>(null)
const edit_room_type = ref<IModal | null>(null)
const {t} = useI18n()
const storeConfigurationRoomType = useConfigurationRoomTypeStore()
const storeConfigurationDashboardStore = useConfigurationDashboardStore()
const {room_types, loading, error} = storeToRefs(storeConfigurationRoomType)

const headers = computed<IConfigurationRoomsHead>(() => ({
  select: true,
  title: t('dashboard.configuration.room_type.name'),
  dashboard: t('dashboard.configuration.room_type.dashboard'),
  actions: ''
}))

const openAddRoomType = () => {
  add_room_type.value?.open()
}
const openEditRoomType = async (id: string) => {
  try {
    await storeConfigurationRoomType.getItem(id, true)
    edit_room_type.value?.open()
  }catch (e){
    console.log(e)
  }
}
onMounted(async () => {
  await Promise.all([
    storeConfigurationRoomType.getList({}),
    storeConfigurationDashboardStore.getList({})
  ])
})
const moreHandle = async () => {
  await storeConfigurationRoomType.loadMore()
}

interface Dashboard {
  title: string;
}

interface Entity {
  select?: boolean;
  title?: string;
  dashboard?: Dashboard;
  active?: string;
  actions?: string;
  [key: string]: any;
}
</script>