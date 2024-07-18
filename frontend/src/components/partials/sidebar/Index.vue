<template>
  <div class="sidebar" :class="{'sidebar-close': sidebarIsOpen}">
    <div class="sidebar__content">
      <SidebarHead/>
      <SidebarMenu/>
      <SidebarFooter/>
    </div>
  </div>
</template>
<script setup lang="ts">
import SidebarHead from "./Head.vue";
import SidebarMenu from "./Menu.vue";
import SidebarFooter from "./Footer.vue";
import {defineComponent} from "vue";
import {storeToRefs} from "pinia";
import {useTemplateStore} from "@store/template.ts";
const storeTemplate = useTemplateStore()
const {sidebarIsOpen} = storeToRefs(storeTemplate)
defineComponent({name: 'Sidebar'})
</script>