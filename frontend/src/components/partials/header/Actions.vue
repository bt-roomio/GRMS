<template>
  <div class="header__actions">
    Roomio Admin Panel
    <div class="header__actions-app">
      <UiIcon name="grid" filled/>
    </div>
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
            Logout
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
const authorizationStore = useAuthorizationStore()
</script>