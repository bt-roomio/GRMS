<template>
  <div class="forgot-password__page">
    <div class="forgot-password__content">
      <Head
          icon="featured-icon"
          :title="$t('authorization.new_password.title')"
      />
      <form class="ui-form" @submit.prevent="storeNewPassword.submit()">
        <UiInput
            v-model="state.new_password"
            name="new_password"
            :label="$t('authorization.new_password.password')"
            type="password"
            placeholder="••••••••"
            autocomplete="new_password"
            :errors="validation.$dirty ? validation.$silentErrors : []"
        />
        <UiInput
            v-model="state.confirm_password"
            name="confirm_password"
            :label="$t('authorization.new_password.password_retry')"
            type="password"
            placeholder="••••••••"
            autocomplete="confirm_password"
            :errors="validation.$dirty ? validation.$silentErrors : []"
        />
        <UiButton :loading="loading" class="primary w-full" type="submit" @click.prevent="storeNewPassword.submit()">{{$t('authorization.new_password.save')}}</UiButton>
      </form>
      <RouterLink class="forgot-password__back mt-8" to="/auth/login">
        <UiIcon name="arrow-left" />
        {{ $t('authorization.forgot_password.back') }}
      </RouterLink>
    </div>
  </div>
</template>
<script setup lang="ts">
import Head from "@components/pages/authorization/Head.vue";
import UiIcon from "@components/ui/Icon.vue";
import UiInput from "@components/ui/Input.vue";
import UiButton from "@components/ui/Button.vue";
import {useNewPasswordStore} from "@store/authorization/new-password.ts";
import {storeToRefs} from "pinia";
const storeNewPassword = useNewPasswordStore()
const {state, validation, loading} = storeToRefs(storeNewPassword)
</script>