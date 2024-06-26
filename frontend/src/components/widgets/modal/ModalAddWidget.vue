<template>
  <Modal ref="add_widget" @closed="cancelModal()">
    <template #head v-if="isEdit">
      <h2>Edit new widget</h2>
      <p>Select the widget you want to add</p>
    </template>
    <template #head v-else>
      <h2>Add new widget</h2>
      <p>Select the widget you want to add</p>
    </template>
    <div class="modal-add-widget">
      <template v-if="selectedComponent">
        <component ref="currentComponent" :is="selectedComponent"/>
      </template>
      <template v-else>
        <div class="ui-form">
          <h3>Choose widget type</h3>
          <div class="modal-add-widget__list">
            <div class="modal-add-widget__item" v-for="item in widgetTypes?.results" :key="item.id" @click.prevent="selectWidgetTypeHandle(JSON.parse(JSON.stringify(item)))">
              <div class="item__icon">
                <UiIcon :name="item.descriptor?.icon" filled/>
              </div>
              <div class="item__info">
                <p>{{item.name}}</p>
                <span>{{item.description}}</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
    <template #footer="{close, closeWithoutEvents}" v-if="selectedComponent && isEdit">
      <UiButton class="primary" @click.prevent="closeWithoutEvents(); storeConfigurationDashboard.handleConfirmWidget()">
        <UiIcon name="plus" filled/>
        Edit widget
      </UiButton>
      <UiButton class="text" @click.prevent="close(); storeConfigurationDashboard.handleCancelWidget()">
        {{ $t('dashboard.configuration.rooms.modals.add_new_rooms.cancel') }}
      </UiButton>
    </template>
  </Modal>
</template>
<script setup lang="ts">
import UiIcon from "@components/ui/Icon.vue";
import Modal from "@components/ui/Modal.vue";
import UiButton from "@components/ui/Button.vue";
import {onMounted, ref} from "vue";
import {storeToRefs} from "pinia";
import {useWidgetType} from "@store/dashboard/widget/widget-type.ts";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
const add_widget = ref<IModal | null>(null)
const storeWidgetType = useWidgetType()
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {isEdit, selectedComponent} = storeToRefs(storeConfigurationDashboard)
const {widgetTypes} = storeToRefs(storeWidgetType)
const currentComponent = ref<{[key: string]: any} | null>(null)
const close = () => {
  add_widget.value?.close()
}
const open = () => {
  add_widget.value?.open()
}
const selectWidgetTypeHandle = async (value: IWidgetType) => {
  const key = storeConfigurationDashboard.addWidget(value, {isEdit: false, key: 0})
  await storeConfigurationDashboard.setEditWidget(value, {
    callback: (confirm) => {
      if (!confirm){
        storeConfigurationDashboard.deleteWidget((key as number) - 1)
      }else {
        storeConfigurationDashboard.saveWidget((key as number) - 1)
      }
      storeConfigurationDashboard.clearEditWidget()
    }
  })
}


const cancelModal = async () => {
  storeConfigurationDashboard.handleCancelWidget()
}

onMounted(async () => {
  await storeWidgetType.getWidgetTypes()
})


defineExpose({
  close,
  open,
})
</script>