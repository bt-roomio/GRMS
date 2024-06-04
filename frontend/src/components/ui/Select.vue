<template>
  <div class="ui-select" ref="reference">
    <label class="ui-select__label" v-if="title">{{ title }}</label>
    <multiselect
        v-bind="$attrs"
        v-model="model"
        @Select="(selectedOption: any) => $emit('change', {selectedOption})"
        :open="true"
    >
      <template #option="props">
        <slot name="option" :props="props" />
      </template>
      <template #singleLabel="props">
        <slot name="singleLabel" :props="props" />
      </template>
    </multiselect>
  </div>
</template>
<script setup lang="ts" generic="T">
import {defineComponent} from "vue";
import Multiselect from "vue-multiselect";
const model = defineModel<any>()
defineProps<{title?: string}>()
defineEmits(['change'])
defineComponent({name: 'UiSelect'})
</script>