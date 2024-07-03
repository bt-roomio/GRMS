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
        <div class="ui-multiselect">
          <label>{{ $t('dashboard.widget.form.type') }}</label>
          <Multiselect
              v-model="editWidget.descriptor.default_config.type"
              :options="types"
              :canClear="false"
              :canDeselect="false"
              :caret="false"
              :searchable="true"
              :placeholder="$t('dashboard.search_from_the_list')"
              @select="changeTypeHandle"
          />
        </div>
      </div>
    </div>
    <div class="modal__card">
      <div class="ui-form">
        <h3>
          {{ $t('dashboard.widget.form.settings_values') }}
          <UiIcon name="plus-circle" filled @click="addControls"/>
        </h3>
        <template v-for="(item, key) in editWidget?.descriptor.default_config?.controls" :key="key">
          <div class="ui-multiselect">
            <label>{{ $t('dashboard.widget.form.tag') }}</label>
            <Multiselect
                v-model="item.tag"
                :options="tags"
                :canClear="false"
                :canDeselect="false"
                :caret="false"
                :searchable="true"
                :placeholder="$t('dashboard.widget.form.tag_placeholder')"
            />
          </div>
          <UiInput
              :label="$t('dashboard.widget.form.title_name')"
              :name="`title-${key}`"
              v-model="item.title"
              :placeholder="$t('dashboard.widget.form.title_placeholder')"
          />
          <div class="ui-form__row col-2" v-if="item.min !== undefined && item.max !== undefined">
            <UiInputCount
                :label="$t('dashboard.widget.form.min_value')"
                v-model="item.min"
                name="min"
            />
            <UiInputCount
                :label="$t('dashboard.widget.form.max_value')"
                v-model="item.max"
                name="max"
            />
          </div>
          <template v-if="editWidget?.descriptor.default_config.type === 'Sensor'">
            <div class="ui-multiselect">
              <label>{{$t('dashboard.widget.form.unit')}}</label>
              <Multiselect
                  v-model="item.unit"
                  :options="units"
                  :canClear="false"
                  :canDeselect="false"
                  :caret="true"
                  :searchable="true"
                  :placeholder="$t('dashboard.widget.form.unit_placeholder')"
              />
            </div>
            <UiInput
                v-if="item.unit === 'Integer'"
                :label="$t('dashboard.widget.form.precision_level')"
                :name="`precision-${key}`"
                v-model="item.precision"
                :placeholder="$t('dashboard.widget.form.precision_placeholder')"
                type="number"
            />
          </template>
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
  </form>
</template>
<script setup lang="ts">
import UiInput from "@components/ui/Input.vue";
import {onMounted, ref} from "vue";
import UiIcon from "@components/ui/Icon.vue";
import UiButton from "@components/ui/Button.vue";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
import {storeToRefs} from "pinia";
import Multiselect from "@vueform/multiselect";
import UiInputCount from "@components/ui/InputCount.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import UiDoubleSelect from "@components/ui/DoubleSelect.vue";
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {editWidget} = storeToRefs(storeConfigurationDashboard)
const storeConfigurationDevice = useConfigurationDeviceStore()
const {devices} = storeToRefs(storeConfigurationDevice)

const units = ref(['Boolean', 'Integer'])
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
const types = ref([
  'Toggle',
  'Slider',
  'Sensor',
])
const addControls = () => {
  if (editWidget.value?.descriptor?.default_config?.type === 'Slider') {
    editWidget.value?.descriptor?.default_config?.controls.push({
      tag: '',
      title: '',
      min: 0,
      max: 100
    })
  } else if (editWidget.value?.descriptor?.default_config?.type === 'Sensor'){
    editWidget.value?.descriptor?.default_config?.controls.push({
      tag: '',
      title: '',
      unit: 'Boolean',
      precision: 0
    })
  } else {
    editWidget.value?.descriptor?.default_config?.controls.push({
      tag: '',
      title: ''
    })
  }
}

const deleteControl = (key: number) => {
  editWidget.value?.descriptor?.default_config?.controls.splice(key, 1)
}
const copyControl = (item: any) => {
  editWidget.value?.descriptor?.default_config?.controls.push(JSON.parse(JSON.stringify(item)))
}
const changeTypeHandle = (value: string) => {
  if (editWidget.value?.descriptor?.default_config?.controls){
    if (value === 'Slider') {
      editWidget.value.descriptor.default_config.controls = []
      editWidget.value.descriptor.default_config.controls.push({
        tag: '',
        title: '',
        min: 0,
        max: 100
      })
    } else if (value === 'Sensor'){
      editWidget.value.descriptor.default_config.controls = []
      editWidget.value.descriptor.default_config.controls.push({
        tag: '',
        title: '',
        unit: 'Boolean',
        max: 100
      })
    } else {
      editWidget.value.descriptor.default_config.controls = []
      editWidget.value.descriptor.default_config.controls.push({
        tag: '',
        title: ''
      })
    }
  }

}
onMounted(async () => {
  if (!editWidget.value?.descriptor?.default_config?.controls.length){
    changeTypeHandle(editWidget.value?.descriptor?.default_config?.type)
  }
  await storeConfigurationDevice.getList()
})

</script>