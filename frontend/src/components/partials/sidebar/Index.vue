<template>
  <div class="sidebar">
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

defineComponent({name: 'Sidebar'})
</script>