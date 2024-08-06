<template>
  <Modal ref="add_widget" @closed="cancelModal()">
    <template #head v-if="isEdit">
      <h2>{{$t('dashboard.widget.modal.edit_title')}}</h2>
      <p>{{$t('dashboard.widget.modal.edit_subtitle')}}</p>
    </template>
    <template #head v-else>
      <h2>{{$t('dashboard.widget.modal.add_title')}}</h2>
      <p>{{$t('dashboard.widget.modal.add_subtitle')}}</p>
    </template>
    <div class="modal-add-widget">
      <template v-if="selectedComponent">
        <component ref="currentComponent" :is="selectedComponent"/>
      </template>
      <template v-else>
        <div class="ui-form">
          <h3>{{$t('dashboard.widget.modal.choose_widget_type')}}</h3>
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
        {{$t('dashboard.widget.modal.save_button')}}
      </UiButton>
      <UiButton class="text" @click.prevent="close(); storeConfigurationDashboard.handleCancelWidget()">
        {{ $t('dashboard.configuration.rooms.modals.add_new_rooms.cancel') }}
      </UiButton>
    </template>
    <template #footer v-if="mode === 'development' && !isEdit">
      <UiButton class="primary" @click.prevent="storeConfigurationDevice.setDeviceAttrs">SET DEVICE ATTRS</UiButton>
      <UiButton class="primary" @click.prevent="storeWidgetType.setWidgetTypes">SET WIDGET TYPES</UiButton>
      <UiButton class="text" @click.prevent="storeWidgetType.deleteWidgetTypes">DELETE WIDGET TYPES</UiButton>
    </template>
  </Modal>
</template>
<script setup lang="ts">
import UiIcon from "@components/ui/Icon.vue";
import Modal from "@components/ui/Modal.vue";
import UiButton from "@components/ui/Button.vue";
import {computed, onMounted, ref, watch} from "vue";
import {storeToRefs} from "pinia";
import {useWidgetType} from "@store/dashboard/widget/widget-type.ts";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import {useWS} from "@store/dashboard/ws";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
const add_widget = ref<IModal | null>(null)
const storeWidgetType = useWidgetType()
const storeConfigurationDevice = useConfigurationDeviceStore()
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {isEdit, selectedComponent, editWidget, alias} = storeToRefs(storeConfigurationDashboard)
const {widgetTypes} = storeToRefs(storeWidgetType)
const currentComponent = ref<{[key: string]: any} | null>(null)
const mode = computed(() => import.meta.env.MODE)
const storeWs = useWS()
const {send, unSubscription} = storeWs

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
const attrDataWs = computed(() => {
  const wsArgs = editWidget.value?.descriptor.default_config?.ws_args;
  if (!wsArgs) return null;

  const isFilled = Object.values(wsArgs).every(arg => !!arg);
  return isFilled ? wsArgs : null;
});
let previousValue = JSON.parse(JSON.stringify(attrDataWs.value));
watch(attrDataWs, (newValue) => {
  if (previousValue) {
    unSubscription(previousValue)

    previousValue = null
  }
  if (newValue) {
    if (newValue.entityType === 'ALIAS') {
      const deviceId = alias.value.find((el: any) => el.id === newValue.entityId)?.device_id
      const newObj = {
        ...newValue,
        entityId: deviceId,
        entityType: 'DEVICE',
      }
      send(newObj)
    }else {
      send(newValue);
    }

    previousValue = JSON.parse(JSON.stringify(newValue));
  }
}, { deep: true });

defineExpose({
  close,
  open,
})
</script>