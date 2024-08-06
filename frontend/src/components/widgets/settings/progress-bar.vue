<template>
  <form v-if="editWidget?.descriptor.default_config">
    <General/>
    <div class="modal__card">
      <div class="ui-form">
        <div class="ui-multiselect">
          <label>{{$t('dashboard.widget.form.tag')}}</label>
          <pre>{{editWidget.descriptor.default_config.tag}}</pre>
          <pre>{{state.attrs.get(storeConfigurationDashboard.getAliasIsEqual(editWidget?.descriptor.default_config.ws_args) + '_' + editWidget?.descriptor.default_config.ws_args.scope)}}</pre>
          <Multiselect
              v-model="editWidget.descriptor.default_config.tag"
              :options="state.attrs.get(storeConfigurationDashboard.getAliasIsEqual(editWidget?.descriptor.default_config.ws_args) + '_' + editWidget?.descriptor.default_config.ws_args.scope)"
              :canClear="false"
              :canDeselect="false"
              :caret="false"
              :searchable="true"
              :placeholder="$t('dashboard.widget.form.tag_placeholder')"
              :disabled="!state.attrs.get(storeConfigurationDashboard.getAliasIsEqual(editWidget?.descriptor.default_config.ws_args) + '_' + editWidget?.descriptor.default_config.ws_args.scope)"
          />
        </div>
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
import {onMounted, ref, watch} from "vue";
import UiInputCount from "@components/ui/InputCount.vue";
import {useWS} from "@store/dashboard/ws";
import General from "@components/widgets/settings/general.vue";
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {editWidget} = storeToRefs(storeConfigurationDashboard)
const storeConfigurationDevice = useConfigurationDeviceStore()
const storeWs = useWS()
const {state} = storeToRefs(storeWs)
const units = ref(['Percent', 'Bytes', 'Kilobytes', 'Megabytes', 'Gigabytes', 'Time (seconds)', 'Time (minutes)', 'Time (hours)', 'Custom Units'])
onMounted(async () => {
  await storeConfigurationDevice.getList()
})
watch(state, (value) => {
  const entityId = storeConfigurationDashboard.getAliasIsEqual(editWidget.value?.descriptor?.default_config?.ws_args);
  const scope = editWidget.value?.descriptor?.default_config?.ws_args.scope;
  const attrs = entityId ? value.attrs.get(entityId + '_' + scope) : null;
  if (editWidget.value?.descriptor?.default_config && (!attrs || !attrs.includes(editWidget.value?.descriptor?.default_config?.tag))) {
    editWidget.value.descriptor.default_config.tag = '';
  }

}, { deep: true });

</script>