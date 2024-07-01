<template>
  <div class="ui-input-count">
    <label v-if="label" :for="id">{{ label }}</label>
    <div class="ui-input-count__group">
      <UiButton class="secondary" @click.prevent="minus">
        <UiIcon name="minus" filled/>
      </UiButton>
      <input
          type="number"
          :id="id"
          v-model="model"
          :class="[{'ui-input__invalid': errors && errors.find(el => el.$property === name)}]"
      >
      <UiButton class="secondary" @click.prevent="plus">
        <UiIcon name="plus" filled/>
      </UiButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineComponent } from 'vue';
import UiButton from '@components/ui/Button.vue';
import UiIcon from '@components/ui/Icon.vue';
import { ErrorObject } from '@vuelidate/core';

const model = defineModel<number>();

defineProps<{
  id?: string,
  name: string,
  errors?: ErrorObject[],
  label?: string,
}>();

const plus = () => {
  if (model.value !== undefined) {
    model.value += 1;
  }
}
const minus = () => {
  if (model.value !== undefined && model.value > 0) {
    model.value -= 1;
  }
}

defineComponent({ name: 'UiInputCount' });
</script>
