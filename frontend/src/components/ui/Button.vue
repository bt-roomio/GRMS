<template>
  <button class="ui-button">
    <span class="ui-button__loader" v-if="loading"></span>
    <slot />
  </button>
</template>
<script setup lang="ts">
import {defineComponent} from "vue";
defineProps(['loading'])
defineComponent({name: 'UiButton'})
</script>