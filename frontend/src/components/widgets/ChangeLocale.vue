<template>
  <UiSelect
      v-model="model"
      :data="locales"
      modelKey="code"
      @change="changeLocale"
      name="name"
  >
    <template #trigger>
      <UiIcon :name="locales.find(el => el.code === model)?.icon || 'en'" filled/>
      {{ locales.find(el => el.code === model)?.name }}
    </template>
    <template #item="{item}">
      <UiIcon :name="item.icon" filled/>
      {{ item.name }}
    </template>
  </UiSelect>
</template>
<script setup lang="ts">
import UiIcon from "@components/ui/Icon.vue";
import UiSelect from "@components/ui/Select.vue";
import {ref} from "vue";
const model = defineModel<{[key: string]: unknown} | string>()
const changeLocale = (loc: string) => {
  model.value = loc
}
const locales = ref<ILocales[]>([
  {
    name: 'English',
    code: 'en',
    icon: 'us'
  },
  {
    name: 'O‘zbekcha',
    code: 'uz',
    icon: 'uz'
  },
  {
    name: 'Русский',
    code: 'ru',
    icon: 'ru'
  }
])
</script>