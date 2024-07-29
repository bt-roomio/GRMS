<template>
  <UiLoader v-if="loading" />
  <div class="dashboard__layouts" v-else-if="permissions.size && !loading">
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
import {usePermissions} from "@store/dashboard/user/permissions.ts";
import UiLoader from "@components/ui/Loader.vue";
const storeTemplate = useTemplateStore()
const storePermissions = usePermissions()
const {permissions, loading} = storeToRefs(storePermissions)
const {sidebarIsOpen} = storeToRefs(storeTemplate)
</script>