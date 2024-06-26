<template>
  <div class="stats__head">
    <div class="stats__head-sorts">
      <UiButton :class="sortWidgets !== 2 ? 'text' : 'primary'" @click.prevent="changeSort(2)">Today</UiButton>
      <UiButton :class="sortWidgets !== 7 ? 'text' : 'primary'" @click.prevent="changeSort(7)">7 days</UiButton>
      <UiButton :class="sortWidgets !== 30 ? 'text' : 'primary'" @click.prevent="changeSort(30)">30 days</UiButton>
      <UiButton :class="sortWidgets !== 365 ? 'text' : 'primary'" @click.prevent="changeSort(365)">1 year</UiButton>
    </div>
    <div class="stats__head-period">
      <UiButton class="text">
        <UiIcon name="calendar" filled/>
        Choose period
      </UiButton>
    </div>
    <div class="stats__head-settings">
      <template v-if="isDashboardSettings">
        <UiButton class="primary" @click.prevent="openAddWidget">
          Add widget
        </UiButton>
        <UiButton class="text" @click.prevent="storeMainWidgetSetting.handleCancel()">
          {{ $t('confirm.button_cancel') }}
        </UiButton>
        <UiButton class="primary" @click.prevent="storeMainWidgetSetting.handleConfirm()">
          {{ $t('dashboard.settings.save') }}
        </UiButton>
      </template>
      <UiButton v-else class="text" @click.prevent="handleSettings">
        <UiIcon name="settings" filled/>
        Settings
      </UiButton>
    </div>
  </div>
  <ModalAddWidget ref="add_widget" />
</template>
<script setup lang="ts">
import UiButton from "@components/ui/Button.vue";
import UiIcon from "@components/ui/Icon.vue";
import {useMainWidgetSetting} from "@store/dashboard/widget/widget.ts";
import {storeToRefs} from "pinia";
import ModalAddWidget from "@components/widgets/modal/ModalAddWidget.vue";
import {ref} from "vue";
const add_widget = ref<IModal | null>(null)
const storeMainWidgetSetting = useMainWidgetSetting()
const {isDashboardSettings, sortWidgets} = storeToRefs(storeMainWidgetSetting)
const handleSettings = () => {
  storeMainWidgetSetting.setSettings({
    callback: (confirm) => {
      if (confirm) {
        storeMainWidgetSetting.setMainDashboardSettings()
      }
    }
  })
}
const openAddWidget = () => {
  add_widget.value?.open()
}
const changeSort = (val: number) => {
  sortWidgets.value = val
}
</script>