<template>
  <UiSelect
      track-by="name"
      v-bind="selectConfig"
      v-model="selectValue"
      :options="locales"
      label="name"
      @change="changeLocale"
  >
    <template #singleLabel="{props}">
      <UiIcon :name="(props as any).option.icon" filled/>
      {{ (props as any).option.name }}
    </template>
    <template #option="{props}">
      <UiIcon :name="(props as any).option.icon" filled/>
      {{ (props as any).option.name }}
    </template>
  </UiSelect>
</template>
<script setup lang="ts">
import UiIcon from "@components/ui/Icon.vue";
import UiSelect from "@components/ui/Select.vue";
import {ref} from "vue";
import {selectConfig} from "@utils/configsSelect.ts";
const model = defineModel<{[key: string]: unknown} | string>()
const changeLocale = (loc: { selectedOption: ILocales }) => {
  model.value = loc.selectedOption.code
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
const selectValue = ref(locales.value.find(el => el.code === model.value))

</script>