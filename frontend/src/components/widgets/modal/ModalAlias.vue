<template>
  <Modal ref="modal" @closed="closedModal" position="top-center">
    <template #head>
      <h2>Alias</h2>
      <p>In this window you can create edit delete all current aliases of this dashboard</p>
    </template>

    <AliasList v-if="state === 'list'" @add="state = 'add'" @edit="(key: number) => state = `edit-${key}`"/>
    <div class="flex items-center">
      <h2 class="text-lg font-semibold" v-if="state === 'add'">{{$t('dashboard.widget.form.add_alias')}}</h2>
      <h2 class="text-lg font-semibold" v-if="state.includes('edit')">{{$t('dashboard.widget.form.edit_alias')}}</h2>
      <UiButton v-if="state === 'add' || state.includes('edit')" class="link ml-auto" @click.prevent="closedModal">
        <UiIcon name="arrow-left" filled />
        Back to list
      </UiButton>
    </div>

    <AliasAdd v-if="state === 'add'" @submit="addAlias"/>
    <AliasEdit v-if="state.includes('edit')" @submit="editAlias(+state.split('-')[1])"/>

    <template #footer="{close}">
      <UiButton v-if="state === 'add'" class="primary" @click.prevent="addAlias()">
        {{$t('dashboard.widget.form.add_alias')}}
      </UiButton>
      <UiButton v-if="state.includes('edit')" class="primary" @click.prevent="editAlias(+state.split('-')[1])">
        {{$t('dashboard.widget.modal.save_button')}}
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
import {nextTick, ref} from "vue";
import AliasList from "@components/pages/dashboard/configuration/dashboard/AliasList.vue";
import AliasAdd from "@components/pages/dashboard/configuration/dashboard/AliasAdd.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import {storeToRefs} from "pinia";
import {toast} from "vue3-toastify";
import {useI18n} from "vue-i18n";
import AliasEdit from "@components/pages/dashboard/configuration/dashboard/AliasEdit.vue";
import UiIcon from "@components/ui/Icon.vue";
import useMainStore from "@/store";
const storeMain = useMainStore()
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {aliasState, alias} = storeToRefs(storeConfigurationDashboard)
const modal = ref<IModal | null>(null)
const state = ref('list')
const {t} = useI18n()
const close = () => {
  modal.value?.close()
}
const open = () => {
  modal.value?.open()
}
const addAlias = () => {
  aliasState.value.id = storeMain.generateRandomString(10)
  alias.value.push(aliasState.value as never)
  state.value = 'list'
  nextTick(() => {
    toast.success(t('toast.alias_add_success') as string);
    emits('submit')
  })
  closedModal()
}
const editAlias = (key: number) => {
  alias.value.splice(key, 1, aliasState.value as never)
  state.value = 'list'
  nextTick(() => {
    toast.success(t('toast.alias_edit_success') as string);
    emits('submit')
  })
  closedModal()
}
const closedModal = () => {
  aliasState.value = {
    id: '',
    name: '',
    device_id: '',
    device_name: ''
  }
  state.value = 'list'
}
const emits = defineEmits(['submit'])
defineExpose({
  close,
  open,
})
</script>