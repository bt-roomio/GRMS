<template>
  <form v-if="editWidget?.descriptor.default_config">
    <General/>
    <div class="modal__card">
      <div class="ui-form">
        <h3>{{$t('dashboard.widget.form.temperature_settings')}}</h3>
        <div class="ui-multiselect">
          <label>{{$t('dashboard.widget.form.tag')}}</label>
          <Multiselect
              v-model="editWidget.descriptor.default_config.tag"
              :options="state.attrs.get(editWidget?.descriptor.default_config.ws_args.entityId + '_' + editWidget?.descriptor.default_config.ws_args.scope)"
              :disabled="!state.attrs.get(editWidget?.descriptor.default_config.ws_args.entityId + '_' + editWidget?.descriptor.default_config.ws_args.scope)"
              :canClear="false"
              :canDeselect="false"
              :caret="false"
              :searchable="true"
              :placeholder="$t('dashboard.widget.form.tag_placeholder')"
          />
        </div>
        <div class="ui-form__row col-2">
          <div class="ui-multiselect">
            <label>{{ $t('dashboard.widget.form.unit') }}</label>
            <Multiselect
                v-model="editWidget.descriptor.default_config.unit"
                :options="units"
                :canClear="false"
                :canDeselect="false"
                :caret="false"
                :searchable="true"
                :placeholder="$t('dashboard.widget.form.unit_placeholder')"
            />
          </div>
          <UiInputCount
              :label="$t('dashboard.widget.form.default_temperature')"
              v-model="editWidget.descriptor.default_config.default_temperature"
              name="default_temperature"
          />
        </div>
        <div class="ui-form__row col-2">
          <UiInputCount
              :label="$t('dashboard.widget.form.min_temperature')"
              v-model="editWidget.descriptor.default_config.min"
              name="min"
          />
          <UiInputCount
              :label="$t('dashboard.widget.form.max_temperature')"
              v-model="editWidget.descriptor.default_config.max"
              name="max"
          />
        </div>
      </div>
    </div>
    <div class="modal__card">
      <div class="ui-form">
        <h3>
          {{ $t('dashboard.widget.form.fan_speed_level') }}
          <UiIcon name="plus-circle" filled @click="addControls"/>
        </h3>
        <div class="ui-form__row col-2">
          <UiButton :class="editWidget?.descriptor.default_config.controls_type === 'line' ? 'primary': 'secondary'" @click.prevent="editWidget.descriptor.default_config.controls_type = 'line'">
            <UiIcon name="layout-rows" filled/>
          </UiButton>
          <UiButton :class="editWidget?.descriptor.default_config.controls_type === 'grid' ? 'primary': 'secondary'" @click.prevent="editWidget.descriptor.default_config.controls_type = 'grid'">
            <UiIcon name="layout-grid" filled/>
          </UiButton>
        </div>
        <div class="ui-multiselect">
          <label>{{ $t('dashboard.widget.form.tag') }}</label>
          <Multiselect
              v-model="editWidget.descriptor.default_config.fan_tag"
              :options="state.attrs.get(editWidget?.descriptor.default_config.ws_args.entityId + '_' + editWidget?.descriptor.default_config.ws_args.scope)"
              :disabled="!state.attrs.get(editWidget?.descriptor.default_config.ws_args.entityId + '_' + editWidget?.descriptor.default_config.ws_args.scope)"
              :canClear="false"
              :canDeselect="false"
              :caret="false"
              :searchable="true"
              :placeholder="$t('dashboard.widget.form.tag_placeholder')"
          />
        </div>
        <template v-for="(item, key) in editWidget?.descriptor.default_config?.controls" :key="key">

          <div class="ui-form__row col-2">
            <UiInput
                :label="$t('dashboard.widget.form.power_level_name')"
                :name="`power_level_name-${key}`"
                v-model="item.power_level_name"
                :placeholder="$t('dashboard.widget.form.power_level_name_placeholder')"
            />
            <UiInput
                :label="$t('dashboard.widget.form.value')"
                :name="`value-${key}`"
                v-model="item.value"
                placeholder="0"
            />
          </div>
          <div class="modal__actions">
            <UiButton class="delete" @click.prevent="deleteControl(key)">
              <UiIcon name="trash" filled/>
              {{$t('dashboard.widget.form.delete')}}
            </UiButton>
            <UiButton @click.prevent="copyControl(item)">
              <UiIcon name="copy" filled/>
              {{$t('dashboard.widget.form.copy')}}
            </UiButton>
          </div>
          <hr>
        </template>
        <div class="modal__actions justify-center">
          <UiButton @click.prevent="addControls">
            <UiIcon name="plus-circle" filled/>
            {{$t('dashboard.widget.form.add')}}
          </UiButton>
        </div>
      </div>
    </div>
    <div class="modal__card">
      <div class="ui-form">
        <h3>{{ $t('dashboard.widget.form.additional_settings') }}</h3>
        <div class="ui-form__row col-2">
          <div class="ui-multiselect">
            <label>{{ $t('dashboard.widget.form.tag') }}</label>
            <Multiselect
                v-model="editWidget.descriptor.default_config.master_off_tag"
                :options="state.attrs.get(editWidget?.descriptor.default_config.ws_args.entityId + '_' + editWidget?.descriptor.default_config.ws_args.scope)"
                :disabled="(!state.attrs.get(editWidget?.descriptor.default_config.ws_args.entityId + '_' + editWidget?.descriptor.default_config.ws_args.scope) || !editWidget.descriptor.default_config.master_off)"
                :canClear="false"
                :canDeselect="false"
                :caret="false"
                :searchable="true"
                :placeholder="$t('dashboard.widget.form.tag_placeholder')"
            />
          </div>
          <div class="ui-multiselect">
            <label>{{ $t('dashboard.widget.form.tag') }}</label>
            <Multiselect
                v-model="editWidget.descriptor.default_config.fan_valve_tag"
                :options="state.attrs.get(editWidget?.descriptor.default_config.ws_args.entityId + '_' + editWidget?.descriptor.default_config.ws_args.scope)"
                :disabled="(!state.attrs.get(editWidget?.descriptor.default_config.ws_args.entityId + '_' + editWidget?.descriptor.default_config.ws_args.scope) || !editWidget.descriptor.default_config.fan_valve)"
                :canClear="false"
                :canDeselect="false"
                :caret="false"
                :searchable="true"
                :placeholder="$t('dashboard.widget.form.tag_placeholder')"
            />
          </div>
        </div>
        <div class="ui-form__row col-2">
          <UiCheckbox v-model="editWidget.descriptor.default_config.master_off">{{ $t('dashboard.widget.form.master_off') }}</UiCheckbox>
          <UiCheckbox v-model="editWidget.descriptor.default_config.fan_valve">{{ $t('dashboard.widget.form.fan_valve') }}</UiCheckbox>
        </div>
      </div>
    </div>
  </form>
</template>
<script setup lang="ts">
import UiInput from "@components/ui/Input.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import {storeToRefs} from "pinia";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
import Multiselect from "@vueform/multiselect";
import {onMounted, ref, watch} from "vue";
import UiInputCount from "@components/ui/InputCount.vue";
import UiCheckbox from "@components/ui/Checkbox.vue";
import UiIcon from "@components/ui/Icon.vue";
import UiButton from "@components/ui/Button.vue";
import General from "@components/widgets/settings/general.vue";
import {useWS} from "@store/dashboard/ws";
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {editWidget} = storeToRefs(storeConfigurationDashboard)
const storeConfigurationDevice = useConfigurationDeviceStore()
const units = ref(['Celsius', 'Fahrenheit'])
const storeWs = useWS()
const {state} = storeToRefs(storeWs)
const addControls = () => {
  editWidget.value?.descriptor?.default_config?.controls.push({
    power_level_name: '',
    value: ''
  })
}
const deleteControl = (key: number) => {
  editWidget.value?.descriptor?.default_config?.controls.splice(key, 1)
}
const copyControl = (item: any) => {
  editWidget.value?.descriptor?.default_config?.controls.push(JSON.parse(JSON.stringify(item)))
}

onMounted(async () => {
  if (!editWidget.value?.descriptor?.default_config?.controls.length){
    addControls()
  }
  await storeConfigurationDevice.getList()
})

watch(state, (value) => {
  const entityId = editWidget.value?.descriptor?.default_config?.ws_args.entityId;
  const scope = editWidget.value?.descriptor?.default_config?.ws_args.scope;
  const attrs = entityId ? value.attrs.get(entityId + '_' + scope) : null;
  if (editWidget.value?.descriptor?.default_config && (!attrs || !attrs.includes(editWidget.value?.descriptor?.default_config?.tag))) {
    editWidget.value.descriptor.default_config.tag = '';
  }
  if (editWidget.value?.descriptor?.default_config && (!attrs || !attrs.includes(editWidget.value?.descriptor?.default_config?.fan_tag))) {
    editWidget.value.descriptor.default_config.fan_tag = '';
  }
  if (editWidget.value?.descriptor?.default_config && (!attrs || !attrs.includes(editWidget.value?.descriptor?.default_config?.master_off_tag))) {
    editWidget.value.descriptor.default_config.master_off_tag = '';
  }
  if (editWidget.value?.descriptor?.default_config && (!attrs || !attrs.includes(editWidget.value?.descriptor?.default_config?.fan_valve_tag))) {
    editWidget.value.descriptor.default_config.fan_valve_tag = '';
  }

}, { deep: true });
</script>