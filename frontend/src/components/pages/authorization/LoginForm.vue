<template>
  <form class="login-page__form" @submit.prevent="authorizationStore.login(state)">
    <UiInput
        name="email"
        type="email"
        :label="$t('authorization.login.form.email')"
        :placeholder="$t('authorization.login.form.email_placeholder')"
        autocomplete="user-email"
        v-model="state.email"
        :errors="validation?.$dirty ? validation?.$silentErrors : []"
    />
    <UiInput
        name="password"
        type="password"
        :label="$t('authorization.login.form.password')"
        placeholder="••••••••"
        autocomplete="current-password"
        v-model="state.password"
        :errors="validation?.$dirty ? validation?.$silentErrors : []"
    />
    <div class="actions">
      <div class="remember-me">
        <UiCheckbox v-model="state.remember_me">{{ $t('authorization.login.form.remember_me') }}</UiCheckbox>
      </div>
      <RouterLink to="/forgot-password">{{ $t('authorization.login.form.forgot_password') }}</RouterLink>
    </div>
    <UiButton class="primary w-full" @click.prevent="submit()">{{ $t('authorization.login.form.sign_in') }}</UiButton>
  </form>
</template>
<script setup lang="ts">
import UiButton from "../../ui/Button.vue";
import UiInput from "../../ui/Input.vue";
import UiCheckbox from "../../ui/Checkbox.vue";
import {useAuthorizationStore} from "@/store/authorization";
import {storeToRefs} from "pinia";
import {useGeneralSettingStore} from "@store/dashboard/settings/general.ts";
import {useI18n} from "vue-i18n";
import {useCookies} from "@vueuse/integrations/useCookies";
const authorizationStore = useAuthorizationStore()
const {state, validation} = storeToRefs(authorizationStore)
const generalSettingStore = useGeneralSettingStore()
const {state: generalState} = storeToRefs(generalSettingStore)
const {locale} = useI18n()
const cookies = useCookies(['locale'])
const submit = async () => {
  try {
    await authorizationStore.login(state.value)
    await generalSettingStore.getGeneralSetting()
    locale.value = generalState.value.lang
    cookies.set('locale', generalState.value.lang, {path: '/'})
  }catch (e) {
    console.log(e)
  }
}
</script>