<template>
  <form v-if="editWidget?.descriptor.default_config">
    <General/>
    <div class="modal__card">
      <div class="ui-form">
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
                :options="state.attrs.get(storeConfigurationDashboard.getAliasIsEqual(editWidget?.descriptor.default_config.ws_args) + '_' + editWidget?.descriptor.default_config.ws_args.scope)"
                :canClear="false"
                :canDeselect="false"
                :caret="false"
                :searchable="true"
                :placeholder="$t('dashboard.widget.form.tag_placeholder')"
                :disabled="!state.attrs.get(storeConfigurationDashboard.getAliasIsEqual(editWidget?.descriptor.default_config.ws_args) + '_' + editWidget?.descriptor.default_config.ws_args.scope)"
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
import {onMounted, ref, watch} from "vue";
import UiIcon from "@components/ui/Icon.vue";
import UiButton from "@components/ui/Button.vue";
import {storeToRefs} from "pinia";
import Multiselect from "@vueform/multiselect";
import UiInputCount from "@components/ui/InputCount.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import General from "@components/widgets/settings/general.vue";
import {useWS} from "@store/dashboard/ws";
import {useConfigurationDeviceStore} from "@store/dashboard/configuration/device.ts";
const storeConfigurationDashboard = useConfigurationDashboardStore()
const storeConfigurationDevice = useConfigurationDeviceStore()
const {editWidget} = storeToRefs(storeConfigurationDashboard)
const storeWs = useWS()
const {state} = storeToRefs(storeWs)
const units = ref(['String', 'Boolean', 'Integer'])

const types = ref([
  'Toggle',
  'Slider',
  'Sensor',
])
watch(state, (value) => {
  const entityId = storeConfigurationDashboard.getAliasIsEqual(editWidget.value?.descriptor?.default_config?.ws_args);
  const scope = editWidget.value?.descriptor?.default_config?.ws_args.scope;
  const attrs = entityId ? value.attrs.get(entityId + '_' + scope) : null;

  if (editWidget.value?.descriptor?.default_config?.controls) {
    editWidget.value.descriptor.default_config.controls.forEach((control: any) => {
      if (!attrs || !attrs.includes(control.tag)) {
        control.tag = '';
      }
    });
  }
}, { deep: true });

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