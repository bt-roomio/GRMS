<template>
  <div class="ui-slider">
    <div class="ui-slider__label"><slot/></div>
    <div class="ui-slider__indicator">
      <vue-slider v-model="value" :lazy="true" :dotSize="24" height="8px"></vue-slider>
    </div>
  </div>
</template>
<script setup lang="ts">
import {defineComponent, ref} from "vue";
import VueSlider from 'vue-slider-component'
const value = ref(0)
defineComponent({name: 'UiSliderItem'})
</script>