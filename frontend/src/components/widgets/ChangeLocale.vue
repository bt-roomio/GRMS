<template>
  <div class="change-locale w-max">
    <Multiselect
        v-model="model"
        label="name"
        :value-prop="'value'"
        :options="locales"
        :canClear="false"
    >
      <template #option="{option}">
        <UiIcon :name="(option as any).icon" filled/>
        {{ (option as any).name }}
      </template>
      <template #singlelabel="{value}">
        <div class="multiselect-option">
          <UiIcon :name="(value as any).icon" filled/>
          {{ (value as any).name }}
        </div>
        <div class="mx-auto"></div>
      </template>
    </Multiselect>
  </div>
</template>
<script setup lang="ts">
import {ref} from "vue";
import Multiselect from "@vueform/multiselect";
import UiIcon from "@components/ui/Icon.vue";
const model = defineModel<{[key: string]: unknown} | string>()

const locales = ref<ILocales[]>([
  {
    name: 'English',
    value: 'en',
    icon: 'us'
  },
  {
    name: 'O‘zbekcha',
    value: 'uz',
    icon: 'uz'
  },
  {
    name: 'Русский',
    value: 'ru',
    icon: 'ru'
  }
])
</script>