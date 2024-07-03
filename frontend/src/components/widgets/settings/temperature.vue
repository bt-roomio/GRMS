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
        <h3>{{$t('dashboard.widget.form.temperature_settings')}}</h3>
        <div class="ui-multiselect">
          <label>{{$t('dashboard.widget.form.tag')}}</label>
          <Multiselect
              v-model="editWidget.descriptor.default_config.tag"
              :options="tags"
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
              :options="tags"
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
import {onMounted, ref} from "vue";
import UiInputCount from "@components/ui/InputCount.vue";
import UiDoubleSelect from "@components/ui/DoubleSelect.vue";
import UiCheckbox from "@components/ui/Checkbox.vue";
import UiIcon from "@components/ui/Icon.vue";
import UiButton from "@components/ui/Button.vue";
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {editWidget} = storeToRefs(storeConfigurationDashboard)
const storeConfigurationDevice = useConfigurationDeviceStore()
const {devices} = storeToRefs(storeConfigurationDevice)
const units = ref(['Celsius', 'Fahrenheit'])

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

const tags = ref([
  'DND',
  'MUR',
  'Door contact',
  'Door open',
  'Main Relay',
  'Check-In',
  'Balcony scenario',
  'Room sensor',
  'M sensor',
  'WC sensor',
  'Bath alarm',
  'Main light',
  'Spot light',
  'Balcony light',
  'Bed Left light',
  'Spot light',
  'Dressing light',
])
</script>