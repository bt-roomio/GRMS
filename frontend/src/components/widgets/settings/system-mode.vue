<template>
  <div class="modal__card" v-if="editWidget?.descriptor.default_config">
    <form class="ui-form">
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
      <UiInputSelect
          v-model="editWidget.descriptor.default_config.entityId"
          v-model:select="editWidget.descriptor.default_config.entityType"
          :options="devices?.results"
          :args="{valueProp: 'id', label: 'name'}"
          :select-options="['Device', 'Alias']"
          label="Datasource"
          name="subtitle"
          placeholder="Room temperature"
      />
      <div class="ui-multiselect">
        <label>Type</label>
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
    </form>
  </div>
  <div class="modal__card" v-if="editWidget?.descriptor.default_config">
    <form class="ui-form">
      <h3>
        Settings values
        <UiIcon name="plus-circle" filled @click="addControls"/>
      </h3>
      <template v-for="(item, key) in editWidget?.descriptor.default_config?.controls" :key="key">
        <div class="ui-multiselect">
          <label>Tag</label>
          <Multiselect
              v-model="item.tag"
              :options="tags"
              :canClear="false"
              :canDeselect="false"
              :caret="false"
              :searchable="true"
              placeholder="Write the tag"
          />
        </div>
        <UiInput
            label="Title Name"
            :name="`title-${key}`"
            v-model="item.title"
            placeholder="Write the title"
        />
        <div class="ui-form__row col-2" v-if="item.min !== undefined && item.max !== undefined">
          <UiInputCount
              label="Min value"
              v-model="item.min"
              name="min"
          />
          <UiInputCount
              label="Max value"
              v-model="item.max"
              name="max"
          />
        </div>
        <template v-if="editWidget?.descriptor.default_config.type === 'Sensor'">
          <div class="ui-multiselect">
            <label>Unit</label>
            <Multiselect
                v-model="item.unit"
                :options="units"
                :canClear="false"
                :canDeselect="false"
                :caret="true"
                :searchable="true"
                placeholder="Write the unit"
            />
          </div>
          <UiInput
              v-if="item.unit === 'Integer'"
              label="Precision level"
              :name="`precision-${key}`"
              v-model="item.precision"
              placeholder="Write the precision"
              type="number"
          />
        </template>
        <div class="modal__actions">
          <UiButton class="delete" @click.prevent="deleteControl(key)">
            <UiIcon name="trash" filled/>
            Delete
          </UiButton>
          <UiButton @click.prevent="copyControl(item)">
            <UiIcon name="copy" filled/>
            Copy
          </UiButton>
        </div>
        <hr>
      </template>
      <div class="modal__actions justify-center">
        <UiButton @click.prevent="addControls">
          <UiIcon name="plus-circle" filled/>
          Add
        </UiButton>
      </div>
    </form>
  </div>
</template>
<script setup lang="ts">
import UiInput from "@components/ui/Input.vue";
import {onMounted, ref} from "vue";
import UiIcon from "@components/ui/Icon.vue";
import UiButton from "@components/ui/Button.vue";
import UiInputSelect from "@components/ui/InputSelect.vue";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
import {storeToRefs} from "pinia";
import Multiselect from "@vueform/multiselect";
import UiInputCount from "@components/ui/InputCount.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
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