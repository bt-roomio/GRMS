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
import {useUserStore} from "@store/dashboard/user";
import {onMounted} from "vue";
import {useCookies} from "@vueuse/integrations/useCookies";
const storeTemplate = useTemplateStore()
const storeUser = useUserStore()
const {sidebarIsOpen} = storeToRefs(storeTemplate)
const cookies = useCookies(['user_id'])

onMounted(async () => {
  await storeUser.getProfile(cookies.get('user_id'))
})
</script>