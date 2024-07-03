<template>
  <form v-if="editWidget?.descriptor.default_config">
    <div class="modal__card">
      <div class="ui-form">
        <h3>{{$t('dashboard.widget.form.general')}}</h3>
        <UiInput
            :label="$t('dashboard.widget.form.title')"
            name="title"
            v-model="editWidget.descriptor.default_config.title"
            :placeholder="$t('dashboard.widget.form.title_placeholder')"
        />
        <UiInput
            :label="$t('dashboard.widget.form.subtitle')"
            name="subtitle"
            v-model="editWidget.descriptor.default_config.subtitle"
            :placeholder="$t('dashboard.widget.form.subtitle_placeholder')"
        />
        <UiDoubleSelect
            v-model="editWidget.descriptor.default_config.entityId"
            v-model:select="editWidget.descriptor.default_config.entityType"
            :options="devices?.results"
            :args="{valueProp: 'id', label: 'name'}"
            :select-options="['Device', 'Alias']"
            :label="$t('dashboard.widget.form.datasource')"
            name="datasource"
            :placeholder="$t('dashboard.widget.form.room_temperature')"
        />
      </div>
    </div>
    <div class="modal__card">
      <div class="ui-form">
        <div class="ui-multiselect" v-if="editWidget?.descriptor.default_config.unit !== 'Custom Units'">
          <label>{{ $t('dashboard.widget.form.unit') }}</label>
          <Multiselect
              v-model="editWidget.descriptor.default_config.unit"
              :options="units"
              :canClear="false"
              :canDeselect="false"
              :caret="true"
              :searchable="true"
              :placeholder="$t('dashboard.widget.form.unit_placeholder')"
          />
        </div>
        <UiInputSelect
            v-else
            v-model="editWidget.descriptor.default_config.unit_value"
            v-model:select="editWidget.descriptor.default_config.unit"
            :select-options="units"
            :args="{placeholder: $t('dashboard.widget.form.unit_placeholder')}"
            :label="$t('dashboard.widget.form.unit')"
            name="unit"
        />
        <div class="ui-form__row col-2">
          <UiInputCount
              :label="$t('dashboard.widget.form.min_value')"
              v-model="editWidget.descriptor.default_config.min"
              name="min"
          />
          <UiInputCount
              :label="$t('dashboard.widget.form.max_value')"
              v-model="editWidget.descriptor.default_config.max"
              name="max"
          />
        </div>
        <UiInput
            :label="$t('dashboard.widget.form.color')"
            name="color"
            type="color"
            v-model="editWidget.descriptor.default_config.color"
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