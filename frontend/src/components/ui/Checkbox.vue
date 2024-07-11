<template>
  <label class="ui-checkbox">
    <slot name="left"/>
    <input type="checkbox" v-model="model" :checked="$attrs.checked as any" :name="name">
    <div class="custom-checkbox">
      <UiIcon name="check" filled/>
    </div>
    <slot />
  </label>
</template>
<script setup lang="ts">
import {defineComponent} from "vue";
import UiIcon from "./Icon.vue";
const model = defineModel()

defineProps<{
  name?: string
}>()
defineComponent({name: 'UiCheckbox'})
</script>