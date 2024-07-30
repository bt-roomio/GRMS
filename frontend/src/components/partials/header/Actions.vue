<template>
  <div class="header__actions">
    <UiDropdown>
      <template #trigger>
        <div class="flex items-center gap-2">
          <div class="header__profile">
            {{ profile?.first_name?.slice(0, 1) }}{{ profile?.last_name?.slice(0, 1) }}
          </div>
          <span>{{ profile?.first_name }}  {{ profile?.last_name?.slice(0, 1) }}.</span>
          <UiIcon name="chevron-down" filled />
        </div>
      </template>
      <template #content>
        <ul class="dropdown__menu">
          <li style="background:transparent;">
            <UiIcon name="user" class="mb-auto mt-1" filled/>
            <div>
              <p class="text-lg font-semibold"> {{ profile?.first_name }} {{ profile?.last_name }}</p>
              <span class="text-sm font-medium">{{profile?.email}}</span>
            </div>
          </li>
          <li style="padding: 0; border-radius: 0" class="border-b"></li>
          <li @click.prevent="changeMode">
            <UiIcon name="palette" class="mb-auto mt-1" filled/>
            Mode: <span class="capitalize">{{hasMode}}</span>
          </li>
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
import {useUserStore} from "@store/dashboard/user";
import {storeToRefs} from "pinia";
import {computed, ref} from "vue";
const authorizationStore = useAuthorizationStore()
const cookies = useCookies(['mode'])
const storeUser = useUserStore()
const { profile } = storeToRefs(storeUser)
const isDarkMode = ref(window.matchMedia('(prefers-color-scheme: dark)').matches);
const hasMode = computed(() => cookies.get('mode') || (isDarkMode.value ? 'dark' : 'light'))
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