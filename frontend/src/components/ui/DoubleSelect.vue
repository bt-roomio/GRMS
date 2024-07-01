<template>
  <div class="ui-double-select">
    <label v-if="label" :for="id">{{ label }}</label>
    <div class="ui-double-select__group">
      <div class="ui-double-select__left">
        <Multiselect
            v-model="modelSelect"
            :options="selectOptions"
            :canClear="false"
            :canDeselect="false"
        />
      </div>
      <Multiselect
          v-model="model"
          :options="options"
          :canClear="false"
          :canDeselect="false"
          :caret="false"
          :searchable="true"
          v-bind="args"
      />
    </div>
    <span class="text-red-500" v-if="errors && errors.find(el => el.$property === name)">{{errors.find(el => el.$property === name)?.$message}}</span>
    <span class="text-xs" v-if="$slots.footer"><slot name="footer"/></span>
  </div>
</template>
<script setup lang="ts">
import {defineComponent} from "vue";
import {ErrorObject} from "@vuelidate/core";
import Multiselect from "@vueform/multiselect";
const model = defineModel()
const modelSelect = defineModel('select')
defineProps<{
  id?: string,
  name: string,
  errors?: ErrorObject[],
  label?: string,
  selectOptions: any
  options: any,
  args?: any
}>()
defineComponent({
  name: 'UiDoubleSelect',
})
</script>