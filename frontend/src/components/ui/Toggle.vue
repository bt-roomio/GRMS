<template>
  <label class="ui-toggle">
    <input :name="name" v-model="model" type="checkbox" class="sr-only peer">
    <div class="ui-toggle__custom"></div>
    <span class="ui-toggle__label" :class="{active: model}">
      <slot></slot>
    </span>
  </label>
</template>
<script setup lang="ts">
import {defineComponent} from "vue";

const model = defineModel()
defineProps<{name?: string}>()
defineComponent({name: 'UiToggle'})
</script>