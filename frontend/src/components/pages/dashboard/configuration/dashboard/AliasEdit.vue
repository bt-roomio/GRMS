<template>
  <form class="ui-form" @submit.prevent="submit">
    <UiInput
        name="name"
        v-model="aliasState.name"
        label="Alias name"
        placeholder="Lighting settings"
    ></UiInput>
    <div class="ui-multiselect">
      <label>{{$t('dashboard.configuration.rooms.modals.add_new_rooms.device')}}</label>
      <Multiselect
          :close-on-select="true"
          :searchable="true"
          :caret="false"
          :can-clear="false"
          label="name"
          :valueProp="'id'"
          @select="selectedDevice"
          v-model="aliasState.device_id"
          :options="devices?.results"
          :placeholder="$t('dashboard.search_from_the_list')"
      />
    </div>
  </form>
</template>
<script setup lang="ts">
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import {storeToRefs} from "pinia";
import UiInput from "@components/ui/Input.vue";
import Multiselect from "@vueform/multiselect";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
const emits = defineEmits(['submit'])
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {aliasState} = storeToRefs(storeConfigurationDashboard)
const storeConfigurationDevice = useConfigurationDeviceStore()
const {devices} = storeToRefs(storeConfigurationDevice)
const submit = () => {
  emits('submit')
}
const selectedDevice = (value: any, option: any) => {
  aliasState.value.device_id = value
  aliasState.value.device_name = option.name
}
</script>