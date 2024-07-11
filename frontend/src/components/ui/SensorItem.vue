<template>
  <div class="ui-sensor">
    <div class="ui-sensor__label"><slot/></div>
    <div class="ui-sensor__indicator">
      <UiStatus v-if="unit === 'Boolean'" :status="getStatus"/>
      <span class="ui-sensor__indicator-text" v-else-if="unit === 'Integer'">{{getValueWithPrecision}}</span>
      <span class="ui-sensor__indicator-text" v-else-if="unit === 'String'">{{model}}</span>
    </div>
  </div>
</template>
<script setup lang="ts">
import {computed, defineComponent} from "vue";
import UiStatus from "@components/ui/Status.vue";
const model = defineModel<Boolean | Number | String>()
const props = defineProps(['unit', 'precision'])
const getStatus = computed(() => {
  if (typeof model.value === 'number') {
    return model.value > 0 ? 'On' : 'Off';
  }
  if (typeof model.value === 'string') {
    return model.value.trim() ? 'On' : 'Off';
  }
  if (typeof model.value === 'boolean') {
    return model.value ? 'On' : 'Off';
  }
  return 'Off';
})
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