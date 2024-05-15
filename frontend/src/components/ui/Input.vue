<template>
  <div class="ui-input">
    <label :for="id">{{ label }}</label>
    <input
        :type="type || 'text'"
        :name="name"
        :id="id"
        :class="[`${inputClass || ''} input`, {'ui-input__invalid': errors && errors.find(el => el.$property === name)}] "
        v-model="model"
        v-bind="$attrs">
    <span class="text-red-500" v-if="errors && errors.find(el => el.$property === name)">{{errors.find(el => el.$property === name)?.$message}}</span>
  </div>
</template>
<script setup lang="ts">
import {defineComponent} from "vue";
import {ErrorObject} from "@vuelidate/core";

const model = defineModel()
defineProps<{
  id?: string,
  name: string,
  type?: string,
  inputClass?: string,
  errors?: ErrorObject[],
  label?: string
}>()
defineComponent({
  name: 'UiInput',
})
</script>