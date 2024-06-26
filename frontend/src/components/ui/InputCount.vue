<template>
  <div class="ui-input-count">
    <label v-if="label" :for="id">{{ label }}</label>
    <div class="ui-input-count__group">
      <UiButton class="secondary">
        <UiIcon name="minus" filled/>
      </UiButton>
      <input
          type="number"
          :id="id"
          v-model="model"
          :class="[{'ui-input__invalid': errors && errors.find(el => el.$property === name)}]"
      >
      <UiButton class="secondary">
        <UiIcon name="plus" filled/>
      </UiButton>
    </div>
  </div>
</template>
<script setup lang="ts">
import {defineComponent} from "vue";
import UiButton from "@components/ui/Button.vue";
import UiIcon from "@components/ui/Icon.vue";
import {ErrorObject} from "@vuelidate/core";
const model = defineModel()
defineProps<{
  id?: string,
  name: string,
  errors?: ErrorObject[],
  label?: string,
}>()
defineComponent({name: 'UiInputCount'})
</script>