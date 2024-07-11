<template>
  <div class="ui-input-select">
    <label v-if="label" :for="id">{{ label }}</label>
    <div class="ui-input-select__group">
      <div class="ui-input-select__left" v-if="selectPosition !== 'right'">
        <Multiselect
            v-model="modelSelect"
            :options="selectOptions"
            :canClear="false"
            :canDeselect="false"
        />
      </div>
      <UiInput name="input-select" :class="selectPosition" v-model="model" v-bind="args"/>
      <div class="ui-input-select__right" v-if="selectPosition === 'right'">
        <Multiselect
            v-model="modelSelect"
            :options="selectOptions"
            :canClear="false"
            :canDeselect="false"
        />
      </div>
    </div>
    <span class="text-red-500" v-if="errors && errors.find(el => el.$property === name)">{{errors.find(el => el.$property === name)?.$message}}</span>
    <span class="text-xs" v-if="$slots.footer"><slot name="footer"/></span>
  </div>
</template>
<script setup lang="ts">
import {defineComponent} from "vue";
import {ErrorObject} from "@vuelidate/core";
import Multiselect from "@vueform/multiselect";
import UiInput from "@components/ui/Input.vue";
const model = defineModel()
const modelSelect = defineModel('select')
defineProps<{
  id?: string,
  name: string,
  errors?: ErrorObject[],
  label?: string,
  selectOptions: any
  selectPosition?: string
  args?: any
}>()
defineComponent({
  name: 'UiInputSelect',
})
</script>