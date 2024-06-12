<template>
  <div class="ui-input">
    <label v-if="label" :for="id">{{ label }}</label>
    <div class="ui-input__group">
      <UiIcon :class="iconPosition" v-if="icon && iconPosition === 'left'" :name="icon" filled/>
      <input
          :type="type || 'text'"
          :name="name"
          :id="id"
          :class="[`${inputClass || ''} input`, {'ui-input__invalid': errors && errors.find(el => el.$property === name)}, iconPosition] "
          v-model="model"
          v-bind="$attrs"
      >
      <UiIcon :class="iconPosition" v-if="icon && iconPosition === 'right'" :name="icon" filled/>
    </div>
    <span class="text-red-500" v-if="errors && errors.find(el => el.$property === name)">{{errors.find(el => el.$property === name)?.$message}}</span>
    <span class="text-xs" v-if="$slots.footer"><slot name="footer"/></span>
  </div>
</template>
<script setup lang="ts">
import {defineComponent} from "vue";
import {ErrorObject} from "@vuelidate/core";
import UiIcon from "@components/ui/Icon.vue";
const model = defineModel()
defineProps<{
  id?: string,
  name: string,
  type?: string,
  inputClass?: string,
  errors?: ErrorObject[],
  label?: string,
  icon?: string,
  iconPosition?: string,
}>()
defineComponent({
  name: 'UiInput',
})
</script>