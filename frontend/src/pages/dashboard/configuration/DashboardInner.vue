<template>
  <div class="page">
    <div class="page__content" v-if="dashboard">
      <PageHead
          :title="dashboard.title || ''"
          :buttons="buttons"
          @click-button="clickButtonsHandle"
          back-to="/configuration/dashboard"
          back="Back"
      />
      <WidgetContainer
          v-if="viewModel"
          :isSettings="isSettings"
          v-model="viewModel"
          :widgets="viewWidgets"
          @edit="editWidgetHandle"
          @delete="deleteWidgetHandle"
      />
    </div>
    <ModalAddWidget ref="add_widget" />
    <ModalAlias @submit="saveAlias" ref="modal_alias" />
  </div>
</template>
<script setup lang="ts">
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import {computed, onMounted, onUnmounted, ref} from "vue";
import {useRoute} from "vue-router";
import {storeToRefs} from "pinia";
import PageHead from "@components/pages/dashboard/PageHead.vue";
import WidgetContainer from "@components/widgets/WidgetContainer.vue";
import ModalAddWidget from "@components/widgets/modal/ModalAddWidget.vue";
import {useI18n} from "vue-i18n";
import ModalAlias from "@components/widgets/modal/ModalAlias.vue";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
const storeConfigurationDashboard = useConfigurationDashboardStore()
const storeConfigurationDevice = useConfigurationDeviceStore()
const {
  dashboard,
  isSettings,
  viewModel,
  viewWidgets,
} = storeToRefs(storeConfigurationDashboard)
const {t} = useI18n()
const {params} = useRoute()
const modal_alias = ref<IModal | null>(null)
const add_widget = ref<IModal | null>(null)

const buttons = computed(() => {
  let objs = [
    {icon: 'settings', id: 'settings', class: 'text'},
    {icon: 'check', id: 'save', class: 'text'},
    {icon: 'x-close', id: 'cancel', class: 'text delete'},
    {name: t('dashboard.widget.form.alias'), id: 'alias', class: 'text'},
    {name: t('dashboard.widget.form.add_widget'), icon: 'plus', id: 'add-widget'},
  ]
  if (!isSettings.value) {
    objs = objs.filter(el => !(['alias', 'add-widget', 'save', 'cancel'].includes(el.id)))
  }else {
    objs = objs.filter(el => !(['settings'].includes(el.id)))
  }
  return objs
})

onMounted(async () => {
  await Promise.all([
    storeConfigurationDashboard.getItem(params.id as string, true),
    storeConfigurationDevice.getList(),
  ])
  await storeConfigurationDashboard.getAlias()
  await storeConfigurationDashboard.getDashboardInnerHelpers()
})
const editWidgetHandle = (args: {item: IWidgetType, key: number}) => {
  if (add_widget.value){
    add_widget.value?.open()
    storeConfigurationDashboard.setEditWidget(args.item, {
      callback: (confirm) => {
        if (!confirm) {
          storeConfigurationDashboard.clearEditWidget()
        }else {
          storeConfigurationDashboard.saveWidget(args.key)
        }
      }
    })
  }
}

const deleteWidgetHandle = (key: number) => {
  storeConfigurationDashboard.deleteWidget(key)
}
const clickButtonsHandle = (evt: any) => {
  switch (evt.id) {
    case 'settings': storeConfigurationDashboard.setSettings({
      callback: (confirm) => {
        if (confirm) {
          storeConfigurationDashboard.saveDashboard()
        }else {
          storeConfigurationDashboard.resetDashboard()
        }
      }
    })
          break;
    case 'save': storeConfigurationDashboard.handleConfirm()
          break;
    case 'cancel': storeConfigurationDashboard.handleCancel()
          break;
    case 'add-widget': add_widget.value?.open()
          break;
    case 'alias': modal_alias.value?.open()
          break;
  }
}

const saveAlias = () => {
  storeConfigurationDashboard.saveAlias()
}
onUnmounted(() => {
  storeConfigurationDashboard.$reset()
  storeConfigurationDashboard.$resetData()
})
</script>