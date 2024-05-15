<template>
  <button class="ui-button"><slot /></button>
</template>
<script setup lang="ts">
import {defineComponent} from "vue";

defineComponent({name: 'UiButton'})
</script>