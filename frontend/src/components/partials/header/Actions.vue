<template>
  <div class="header__actions">
    <UiDropdown>
      <template #trigger>
        <UiIcon name="settings" filled/>
      </template>
      <template #content>
        <ul class="dropdown__menu">
          <li @click.prevent="changeMode">
            Mode: <span class="capitalize">{{cookies.get('mode') || 'light'}}</span>
          </li>
        </ul>
      </template>
    </UiDropdown>
    <UiDropdown>
      <template #trigger>
        <div class="header__profile">
          AK
        </div>
      </template>
      <template #content>
        <ul class="dropdown__menu">
          <li @click.prevent="authorizationStore.logout()">
            <UiIcon name="log-in" class="stroke-primary-600" filled/>
            {{ $t('authorization.login.form.sign_out') }}
          </li>
        </ul>
      </template>
    </UiDropdown>
  </div>
</template>
<script setup lang="ts">
import UiIcon from "@components/ui/Icon.vue";
import UiDropdown from "@components/ui/Dropdown.vue";
import {useAuthorizationStore} from "@/store/authorization";
import {useCookies} from "@vueuse/integrations/useCookies";
const authorizationStore = useAuthorizationStore()
const cookies = useCookies(['mode'])
const changeMode = () => {
  if (cookies.get('mode')) {
    switch (cookies.get('mode')) {
      case 'dark': cookies.set('mode', 'light', {path: '/'})
        break;
      case 'light': cookies.set('mode', 'dark', {path: '/'})
        break;
    }
  }else {
    cookies.set('mode', 'dark', {path: '/'})
  }

}
</script>