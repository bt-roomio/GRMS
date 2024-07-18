<template>
  <header class="header" :class="{'sidebar-close': sidebarIsOpen}">
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
import {useTemplateStore} from "@store/template.ts";
import {storeToRefs} from "pinia";
const storeTemplate = useTemplateStore()
const {sidebarIsOpen} = storeToRefs(storeTemplate)
defineComponent({name: 'Header'})
</script>