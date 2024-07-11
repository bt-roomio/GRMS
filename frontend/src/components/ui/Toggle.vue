<template>
  <label class="ui-toggle" v-if="isBoolean">
    <input :name="name" v-model="model" type="checkbox" class="sr-only peer">
    <div class="ui-toggle__custom"></div>
    <span class="ui-toggle__label" :class="{active: model}">
      <slot></slot>
    </span>
  </label>
  <label class="ui-toggle" v-else>
    {{model}}
    <span class="ui-toggle__label" :class="{active: model}">
      <slot></slot>
    </span>
  </label>
</template>
<script setup lang="ts">
import {computed, defineComponent} from "vue";
const model = defineModel()
const isBoolean = computed(() => typeof model.value === 'boolean')
defineProps<{name?: string}>()
defineComponent({name: 'UiToggle'})
</script>