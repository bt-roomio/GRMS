<template>
  <div class="auth-layouts">
    <div class="auth-layouts__content">
      <RouterView/>
    </div>
    <div class="auth-layouts__image">
      <UiIcon name="logo-big" filled/>
      <img src="../assets/images/auth/bg.png" alt="Auth background">
    </div>
  </div>
</template>
<script setup lang="ts">
import UiIcon from "../components/ui/Icon.vue";
</script>