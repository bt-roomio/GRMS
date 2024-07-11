<template>
  <div class="modal__card" v-if="editWidget?.descriptor.default_config">
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
          v-model="editWidget.descriptor.default_config.ws_args.entityId"
          v-model:select="editWidget.descriptor.default_config.ws_args.entityType"
          :options="devices?.results"
          :args="{valueProp: 'id', label: 'name'}"
          :select-options="['DEVICE', 'ALIAS']"
          :label="$t('dashboard.widget.form.datasource')"
          name="datasource"
          :placeholder="$t('dashboard.widget.form.room_temperature')"
      />
      <div class="ui-multiselect">
        <label>{{ $t('dashboard.widget.form.type') }}</label>
        <Multiselect
            v-model="editWidget.descriptor.default_config.ws_args.type"
            :options="['ATTRIBUTES', 'TIMESERIES']"
            :canClear="false"
            :canDeselect="false"
            :caret="false"
            :searchable="true"
            :placeholder="$t('dashboard.search_from_the_list')"
            @select="typeSelected"
        />
      </div>
      <div class="ui-multiselect" v-if="editWidget.descriptor.default_config.ws_args.type === 'ATTRIBUTES'">
        <label>SCOPE</label>
        <Multiselect
            v-model="editWidget.descriptor.default_config.ws_args.scope"
            :options="['SHARED_SCOPE', 'CLIENT_SCOPE', 'SERVER_SCOPE']"
            :canClear="false"
            :canDeselect="false"
            :caret="false"
            :searchable="true"
            :placeholder="'Write the SCOPE'"
        />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import UiInput from "@components/ui/Input.vue";
import UiDoubleSelect from "@components/ui/DoubleSelect.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import {storeToRefs} from "pinia";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
import Multiselect from "@vueform/multiselect";
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {editWidget} = storeToRefs(storeConfigurationDashboard)
const storeConfigurationDevice = useConfigurationDeviceStore()
const {devices} = storeToRefs(storeConfigurationDevice)

const typeSelected = (value: any) => {
  if (value === 'TIMESERIES' && editWidget.value && editWidget.value.descriptor.default_config) {
    editWidget.value.descriptor.default_config.ws_args.scope = 'LATEST_TELEMETRY'
  }else if (value === 'ATTRIBUTES' && editWidget.value && editWidget.value.descriptor.default_config) {
    editWidget.value.descriptor.default_config.ws_args.scope = ''
  }
}
</script>