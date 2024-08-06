<template>
  <UiButton class="link mb-2 ml-auto" @click.prevent="addAlias">
    <UiIcon name="plus-circle" filled/>
    {{$t('dashboard.widget.form.add_alias')}}
  </UiButton>
  <div class="alias__table">
    <UiTable
        :headers="headers"
        :data="alias"
        :options="{
        elementsClass: {
          td: (entity: any) => entity.name ? 'whitespace-nowrap' : ''
        }
      }"
    >
      <template #actions="{entity}">
        <div class="ui-table__actions col-2">
          <UiButton class="secondary" @click.prevent="editAlias(entity)">
            <UiIcon name="edit" filled />
          </UiButton>
          <UiButton class="text" @click.prevent="deleteAlias(entity)">
            <UiIcon name="trash" filled />
          </UiButton>
        </div>
      </template>
    </UiTable>
  </div>
</template>
<script setup lang="ts">
import UiTable from "@components/ui/Table.vue";
import {computed} from "vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import {storeToRefs} from "pinia";
import UiButton from "@components/ui/Button.vue";
import UiIcon from "@components/ui/Icon.vue";
import {toast} from "vue3-toastify";
import {useConfirm} from "@store/dashboard/useConfirm.ts";
import {useI18n} from "vue-i18n";
const emits = defineEmits(['add', 'edit'])
const storeConfigurationDashboard = useConfigurationDashboardStore()
const confirmStore = useConfirm()
const {alias, aliasState} = storeToRefs(storeConfigurationDashboard)
const {t} = useI18n()
const headers = computed<IConfigurationRoomsHead>(() => ({
  name: '',
  device_name: '',
  actions: ''
}))

const addAlias = () => {
  emits('add')
}
const deleteAlias = async (entity: any) => {
  await confirmStore.showConfirm({
    title: t('dashboard.configuration.dashboard.alias.confirm.title'),
    content: t('dashboard.configuration.dashboard.alias.confirm.subtitle'),
    callback: async (confirmed) => {
      if (confirmed) {
        try {
          const index = alias.value.findIndex(value => JSON.stringify(entity) === JSON.stringify(value))
          alias.value.splice(index, 1)
          await storeConfigurationDashboard.saveAlias()
          toast.success(t('toast.alias_delete_success') as string);
        }catch (e: any) {
          throw e
        }
      }
    }
  })
}
const editAlias = async (entity: any) => {
  const index = alias.value.findIndex(value => JSON.stringify(entity) === JSON.stringify(value))
  aliasState.value = entity
  emits('edit', index)
}
</script>