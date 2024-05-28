<template>
  <div class="dashboard__layouts" :class="cookies.get('mode')">
    <Sidebar />
    <Header />
    <div class="dashboard__layouts-content">
      <RouterView/>
    </div>
  </div>
</template>
<script setup lang="ts">
import Sidebar from "../components/partials/sidebar/Index.vue";
import Header from "../components/partials/header/Index.vue";
import {useCookies} from "@vueuse/integrations/useCookies";
const cookies = useCookies(['mode'])
</script>