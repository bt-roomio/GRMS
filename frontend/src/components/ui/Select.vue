<template>
  <div class="ui-select" ref="reference">
    <label class="ui-select__label" v-if="title">{{ title }}</label>
    <Multiselect
        v-bind="$attrs"
        v-model="model"
        @select="selectHandle"
    ></Multiselect>
  </div>
</template>
<script setup lang="ts" generic="T">
import {defineComponent} from "vue";
import Multiselect from '@vueform/multiselect'
const model = defineModel<any>()
defineProps<{title?: string}>()
defineEmits(['change'])
const selectHandle = (value: any) => {
  console.log(value)
}
defineComponent({name: 'UiSelect'})
</script>