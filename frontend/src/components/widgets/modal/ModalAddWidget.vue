<template>
  <Modal ref="add_widget" @closed="storeMainWidgetSetting.$reset()">
    <template #head>
      <h2>{{$t('dashboard.configuration.room_type.modals.add_new_room_type.title')}} </h2>
      <p>{{$t('dashboard.configuration.room_type.modals.add_new_room_type.subtitle')}}</p>
    </template>
    <form class="ui-form" @submit.prevent="storeMainWidgetSetting.addItem(state, close)">
      <UiSelect
          v-bind="selectConfig"
          v-model="state.device"
          label="name"
          :options="devices"
          title="Choose device"
      />
      <UiSelect
          v-if="state.device"
          v-bind="selectConfig"
          v-model="state.device_data_key"
          :options="Object.keys(state.device.telemetry.at(0))"
          title="Choose device data key"
      />
      <UiSelect
          v-bind="selectConfig"
          v-model="state.type"
          label="name"
          :options="widgetTypes?.results"
          title="Choose widget type"
          @change="changeSelectHandle"
      />
      <template v-if="selectedComponent">
        <component :is="selectedComponent" @input="changeComponentSettings"/>
      </template>
    </form>

    <template #footer="{close}">
      <UiButton class="primary" @click.prevent="storeMainWidgetSetting.addItem(state, close)">
        <UiIcon name="plus" filled/>
        Add widget
      </UiButton>
      <UiButton class="text" @click.prevent="close()">
        {{ $t('dashboard.configuration.rooms.modals.add_new_rooms.cancel') }}
      </UiButton>
    </template>
  </Modal>
</template>
<script setup lang="ts">
import UiIcon from "@components/ui/Icon.vue";
import Modal from "@components/ui/Modal.vue";
import UiButton from "@components/ui/Button.vue";
import UiSelect from "@components/ui/Select.vue";
import devices from "@components/widgets/data/devices.json"
import {DefineComponent, onMounted, ref, shallowRef} from "vue";
import {storeToRefs} from "pinia";
import {selectConfig} from "@utils/configsSelect.ts";
import {useMainWidgetSetting} from "@store/dashboard/widget/main-widget.ts";
import {useWidgetType} from "@store/dashboard/widget/widget-type.ts";
const add_widget = ref<IModal | null>(null)
const storeMainWidgetSetting = useMainWidgetSetting()
const storeWidgetType = useWidgetType()
const {widgetTypes} = storeToRefs(storeWidgetType)
const {state} = storeToRefs(storeMainWidgetSetting)
const selectedComponent = shallowRef<DefineComponent | null>(null)
const close = () => {
  add_widget.value?.close()
}
const open = () => {
  add_widget.value?.open()
}
const componentImport = import.meta.glob('../settings/**.vue');

const changeSelectHandle = async (value: {selectedOption: { [key: string]: any }}) => {
  const type = value.selectedOption.descriptor.type
  const importFunction = componentImport[`../settings/${type}.vue`];

  if (importFunction) {
    const componentModule = await importFunction() as {default: DefineComponent};
    selectedComponent.value = componentModule.default;
  } else {
    console.error(`Component ../settings/${type}.vue not found`);
    selectedComponent.value = null;
  }
}

const changeComponentSettings = (value: any) => {
  state.value.config = value
}

onMounted(async () => {
  await storeWidgetType.getWidgetTypes()
})

defineExpose({
  close,
  open,
})
</script>