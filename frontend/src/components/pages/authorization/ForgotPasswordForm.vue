<template>
  <form class="forgot-password__form" @submit.prevent="submitHandle">
    <UiInput
        name="Email"
        type="email"
        :label="$t('authorization.forgot_password.form.email')"
        :placeholder="$t('authorization.forgot_password.form.email_placeholder')"
        autocomplete="user-email"
        v-model="state.email"
    />
    <UiButton class="primary" @click.prevent="submitHandle">{{ $t('authorization.forgot_password.form.reset_password') }}</UiButton>
  </form>
</template>
<script setup lang="ts">
import UiButton from "../../ui/Button.vue";
import UiInput from "../../ui/Input.vue";
import {ref} from "vue";
import {useRouter} from "vue-router";

const router = useRouter()
const state = ref({
  email: '',
})
const submitHandle = () => {
  router.push({name: 'reset-password'})
}
</script>