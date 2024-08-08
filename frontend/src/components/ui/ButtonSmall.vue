<template>
  <button class="ui-small-button">
    <slot/>
  </button>
</template>

<script setup lang="ts">
import {defineComponent} from "vue";

defineComponent({name: 'UiSmallButton'})
</script>