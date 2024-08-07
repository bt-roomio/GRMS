<template>
  <form class="forgot-password__form text-left" @submit.prevent="storeForgotPassword.submit()">
    <UiInput
        name="email"
        type="email"
        :label="$t('authorization.forgot_password.form.email')"
        :placeholder="$t('authorization.forgot_password.form.email_placeholder')"
        autocomplete="user-email"
        v-model="state.email"
        :errors="validation?.$dirty ? validation?.$silentErrors : []"
    />
    <UiButton :loading="loading" class="primary w-full" @click.prevent="storeForgotPassword.submit()">{{ $t('authorization.forgot_password.form.reset_password') }}</UiButton>
  </form>
</template>
<script setup lang="ts">
import {useForgotPasswordStore} from "@store/authorization/forgot-password.ts";
import {storeToRefs} from "pinia";
import UiButton from "@components/ui/Button.vue";
import UiInput from "@components/ui/Input.vue";
const storeForgotPassword = useForgotPasswordStore()
const {state, validation, loading} = storeToRefs(storeForgotPassword)
</script>