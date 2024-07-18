<template>
  <div class="forgot-password__page">
    <div class="forgot-password__content">
      <Head
          icon="featured-icon"
          :title="$t('authorization.reset_password.title')"
      />
      <UiButton
          class="primary w-full"
          @click.prevent="openMail"
      >{{$t('authorization.reset_password.open')}}</UiButton>
      <RouterLink class="forgot-password__resend" to="/password/forgot">
        {{$t('authorization.reset_password.description')}}
        <span>{{ $t('authorization.reset_password.click_resend') }}</span>
      </RouterLink>
      <RouterLink class="forgot-password__back" to="/auth/login">
        <UiIcon name="arrow-left" />
        {{ $t('authorization.forgot_password.back') }}
      </RouterLink>
    </div>
  </div>
</template>
<script setup lang="ts">
import Head from "../../components/pages/authorization/Head.vue";
import UiButton from "../../components/ui/Button.vue";
import UiIcon from "../../components/ui/Icon.vue";

const openMail = () => {
  window.open('https://mail.google.com/', '_blank')
}
</script>