<template>
  <div class="login-page">
    <div class="login-page__content">
      <Head
          icon="logo"
          :title="$t('authorization.login.title')"
          :description="$t('authorization.login.description')"
      />
      <LoginForm/>
    </div>
    <LoginFooter/>
  </div>
</template>
<script setup lang="ts">
import LoginForm from "../../components/pages/authorization/LoginForm.vue";
import LoginFooter from "../../components/pages/authorization/LoginFooter.vue";
import Head from "../../components/pages/authorization/Head.vue";
</script>