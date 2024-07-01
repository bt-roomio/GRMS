<template>
  <form v-if="editWidget?.descriptor.default_config">
    <div class="modal__card" >
      <div class="ui-form">
        <h3>General</h3>
        <UiInput
            label="Title"
            name="title"
            v-model="editWidget.descriptor.default_config.title"
            placeholder="Write the title"
        />
        <UiInput
            label="Subtitle"
            name="subtitle"
            v-model="editWidget.descriptor.default_config.subtitle"
            placeholder="Write the subtitle"
        />
        <UiDoubleSelect
            v-model="editWidget.descriptor.default_config.entityId"
            v-model:select="editWidget.descriptor.default_config.entityType"
            :options="devices?.results"
            :args="{valueProp: 'id', label: 'name'}"
            :select-options="['Device', 'Alias']"
            label="Datasource"
            name="subtitle"
            placeholder="Room temperature"
        />
      </div>
    </div>
    <div class="modal__card">
      <div class="ui-form">
        <div class="ui-multiselect" v-if="editWidget?.descriptor.default_config.unit !== 'Custom Units'">
          <label>Unit</label>
          <Multiselect
              v-model="editWidget.descriptor.default_config.unit"
              :options="units"
              :canClear="false"
              :canDeselect="false"
              :caret="true"
              :searchable="true"
              placeholder="Write the unit"
          />
        </div>
        <UiInputSelect
            v-else
            v-model="editWidget.descriptor.default_config.unit_value"
            v-model:select="editWidget.descriptor.default_config.unit"
            :select-options="units"
            :args="{placeholder: 'Write the unit'}"
            label="Unit"
            name="unit"
        />
        <div class="ui-form__row col-2">
          <UiInputCount
              label="Min value"
              v-model="editWidget.descriptor.default_config.min"
              name="min"
          />
          <UiInputCount
              label="Max value"
              v-model="editWidget.descriptor.default_config.max"
              name="max"
          />
        </div>
        <UiInput
            label="Color"
            name="color"
            type="color"
            v-model="editWidget.descriptor.default_config.color"
            placeholder="Select the color"
        />
      </div>
    </div>
  </form>
</template>
<script setup lang="ts">
import UiInput from "@components/ui/Input.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import {storeToRefs} from "pinia";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
import UiInputSelect from "@components/ui/InputSelect.vue";
import Multiselect from "@vueform/multiselect";
import {onMounted, ref} from "vue";
import UiInputCount from "@components/ui/InputCount.vue";
import UiDoubleSelect from "@components/ui/DoubleSelect.vue";
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {editWidget} = storeToRefs(storeConfigurationDashboard)
const storeConfigurationDevice = useConfigurationDeviceStore()
const {devices} = storeToRefs(storeConfigurationDevice)
const units = ref(['Percent', 'Bytes', 'Kilobytes', 'Megabytes', 'Gigabytes', 'Time (seconds)', 'Time (minutes)', 'Time (hours)', 'Custom Units'])

onMounted(async () => {
  await storeConfigurationDevice.getList()
})
</script>