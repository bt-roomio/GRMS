<template>
  <div class="ui-slider">
    <div class="ui-slider__label">
      <span><slot/></span>
    </div>
    <div class="ui-slider__indicator">
      <vue-slider v-model="value" :lazy="true" :dotSize="24" height="8px" v-bind="args"></vue-slider>
    </div>
    <div class="ui-slider__value">
      <span>{{value}}%</span>
    </div>
  </div>
</template>
<script setup lang="ts">
import {defineComponent, ref} from "vue";
import VueSlider from 'vue-slider-component'
const value = ref(0)
defineProps<{args?: any}>()
defineComponent({name: 'UiSliderItem'})
</script>