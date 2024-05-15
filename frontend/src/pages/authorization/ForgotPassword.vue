<template>
 <div class="forgot-password__page">
   <div class="forgot-password__content">
     <Head
        icon="featured-icon"
        :title="$t('authorization.forgot_password.title')"
        :description="$t('authorization.forgot_password.description')"
     />
     <ForgotPasswordForm />
     <RouterLink class="forgot-password__back" to="/auth/login">
       <UiIcon name="arrow-left" />
       {{ $t('authorization.forgot_password.back') }}
     </RouterLink>
   </div>
 </div>
</template>
<script setup lang="ts">
import ForgotPasswordForm from "../../components/pages/authorization/ForgotPasswordForm.vue";
import UiIcon from "../../components/ui/Icon.vue";
import Head from "../../components/pages/authorization/Head.vue";
</script>