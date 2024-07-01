<template>
  <div class="ui-sensor">
    <div class="ui-sensor__label"><slot/></div>
    <div class="ui-sensor__indicator">
      <UiStatus v-if="unit === 'Boolean'" :status="model ? 'On' : 'Off'"/>
      <span class="ui-sensor__indicator-text" v-else>{{getValueWithPrecision}}</span>
    </div>
  </div>
</template>
<script setup lang="ts">
import {computed, defineComponent} from "vue";
import UiStatus from "@components/ui/Status.vue";
const model = defineModel<Boolean | Number>()
const props = defineProps(['unit', 'precision'])
const getValueWithPrecision = computed(() => {
  if (typeof model.value === 'number'){
    let formattedNumber = parseFloat(model.value.toFixed(props.precision || 0));
    let power = Math.pow(10, props.precision || 0);
    formattedNumber = Math.ceil(formattedNumber * power) / power;
    return formattedNumber
  }else {
    return 0
  }
})
defineComponent({name: 'UiSensorItem'})
</script>