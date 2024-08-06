<template>
  <div class="ui-slider">
    <div class="ui-slider__label">
      <span><slot/></span>
    </div>
    <div class="ui-slider__indicator">
      <vue-slider v-model="value" :lazy="true" @change="$emit('change', $event)" :tooltipPlacement="!index ? 'bottom' : 'top'" :dotSize="24" height="8px" v-bind="args"></vue-slider>
    </div>
    <div class="ui-slider__value">
      <span>{{value}}%</span>
    </div>
  </div>
</template>
<script setup lang="ts">
import {defineComponent} from "vue";
import VueSlider from 'vue-slider-component'
const value = defineModel()
defineProps<{args?: any, index: number}>()
defineEmits(['change'])
defineComponent({name: 'UiSliderItem'})
</script>