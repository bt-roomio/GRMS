<template>
  <Modal ref="add_widget" @closed="storeMainWidgetSetting.$reset()">
    <template #head>
      <h2>{{$t('dashboard.configuration.room_type.modals.add_new_room_type.title')}} </h2>
      <p>{{$t('dashboard.configuration.room_type.modals.add_new_room_type.subtitle')}}</p>
    </template>
    <form class="ui-form" @submit.prevent="storeMainWidgetSetting.addItem(close)">
      <UiSelect
          v-bind="selectConfig"
          v-model="state.widget_name"
          :options="storeMainWidgetSetting.getWidget().map(el => el.name)"
          :title="$t('dashboard.configuration.room_type.modals.add_new_room_type.choose_dashboard')"
          @change="changeSelectHandle"
      />
      <template v-if="state.configs">

      </template>
      <button class="sr-only" type="submit"></button>
    </form>

    <template #footer="{close}">
      <UiButton class="primary" @click.prevent="storeMainWidgetSetting.addItem(close)">
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
import {ref} from "vue";
import {storeToRefs} from "pinia";
import {selectConfig} from "@utils/configsSelect.ts";
import {useMainWidgetSetting} from "@store/dashboard/widget/main-widget.ts";
const add_widget = ref<IModal | null>(null)
const storeMainWidgetSetting = useMainWidgetSetting()
const {state} = storeToRefs(storeMainWidgetSetting)
const close = () => {
  add_widget.value?.close()
}
const open = () => {
  add_widget.value?.open()
}
const changeSelectHandle = (value: {selectedOption: string}) => {
  const selectObject = storeMainWidgetSetting.getWidget().find(el => el.name === value.selectedOption)
  if (selectObject?.configs){
    state.value.configs = selectObject?.configs
  }
}


defineExpose({
  close,
  open,
})
</script>