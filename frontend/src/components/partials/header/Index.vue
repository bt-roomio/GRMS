<template>
  <header class="header">
    <HotelInfo/>
    <Time/>
    <Actions/>
  </header>
</template>
<script setup lang="ts">
import {defineComponent} from "vue";
import HotelInfo from "./HotelInfo.vue";
import Time from "./Time.vue";
import Actions from "./Actions.vue";

defineComponent({name: 'Header'})
</script>