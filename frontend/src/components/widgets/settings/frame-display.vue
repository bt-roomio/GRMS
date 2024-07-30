<template>
  <form v-if="editWidget?.descriptor.default_config">
    <General :hide-device="true"/>
    <div class="modal__card">
      <div class="ui-form">
        <UiInput
            :label="$t('dashboard.widget.form.url')"
            name="url"
            type="url"
            v-model="editWidget.descriptor.default_config.url"
            placeholder="https://www.example.com"
        />
        <div class="ui-multiselect">
          <label>{{$t('dashboard.widget.form.loading_type')}}</label>
          <Multiselect
              v-model="editWidget.descriptor.default_config.loading"
              :options="['lazy', 'eager', 'auto']"
              :canClear="false"
              :canDeselect="false"
              :caret="false"
              :searchable="true"
              :placeholder="$t('dashboard.widget.form.loading_type_placeholder')"
          />
        </div>
      </div>
    </div>
  </form>
</template>
<script setup lang="ts">
import UiInput from "@components/ui/Input.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import {storeToRefs} from "pinia";
import Multiselect from "@vueform/multiselect";
import General from "@components/widgets/settings/general.vue";
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {editWidget} = storeToRefs(storeConfigurationDashboard)
</script>