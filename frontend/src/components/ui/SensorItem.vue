<template>
  <div class="ui-sensor" :class="indicator ? 'on' : 'off'" @click.prevent="indicator = !indicator">
    <div class="ui-sensor__label"><slot/></div>
    <div class="ui-sensor__indicator">
      <UiStatus :status="indicator ? 'On' : 'Off'"/>
    </div>
  </div>
</template>
<script setup lang="ts">
import {defineComponent, ref} from "vue";
import UiStatus from "@components/ui/Status.vue";
const indicator = ref(false)
defineComponent({name: 'UiSensorItem'})
</script>