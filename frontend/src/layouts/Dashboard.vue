<template>
  <div class="dashboard__layouts">
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
</script>