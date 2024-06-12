<template>
  <button class="ui-small-button" v-bind="$attrs">
    <slot/>
  </button>
</template>

<script setup lang="ts">
import {defineComponent} from "vue";

defineComponent({name: 'UiSmallButton'})
</script>