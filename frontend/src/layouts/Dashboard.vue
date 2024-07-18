<template>
  <div class="dashboard__layouts">
    <Sidebar />
    <Header />
    <div class="dashboard__layouts-content" :class="{'sidebar-close': sidebarIsOpen}">
      <RouterView/>
    </div>
  </div>
</template>
<script setup lang="ts">
import Sidebar from "../components/partials/sidebar/Index.vue";
import Header from "../components/partials/header/Index.vue";
import {useTemplateStore} from "@store/template.ts";
import {storeToRefs} from "pinia";
const storeTemplate = useTemplateStore()
const {sidebarIsOpen} = storeToRefs(storeTemplate)
</script>