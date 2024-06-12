<template>
  <div class="card">
    <form class="card__content">
      <div class="card__head">
        <h3>{{ $t('dashboard.settings.email_setup.title') }}</h3>
        <p>{{ $t('dashboard.settings.email_setup.description') }}</p>
      </div>
      <ul class="card__list">
        <li class="card__list-item">
          <div class="item-texts">
            <p class="title">{{ $t('dashboard.settings.email_setup.smtp_server_address.title') }}</p>
            <p class="description">{{ $t('dashboard.settings.email_setup.smtp_server_address.description') }}</p>
          </div>
          <div class="item-actions">
            <UiInput
                v-model="state.host"
                :errors="validation.$dirty ? validation.$silentErrors : []"
                name="host"
                :placeholder="$t('dashboard.settings.email_setup.smtp_server_address.title')"
            />
          </div>
        </li>
        <li class="card__list-item">
          <div class="item-texts">
            <p class="title">{{ $t('dashboard.settings.email_setup.smtp_username.title') }}</p>
            <p class="description">{{ $t('dashboard.settings.email_setup.smtp_username.description') }}</p>
          </div>
          <div class="item-actions">
            <UiInput
                v-model="state.username"
                :errors="validation.$dirty ? validation.$silentErrors : []"
                name="username"
                :placeholder="$t('dashboard.settings.email_setup.smtp_username.title')"
            />
          </div>
        </li>
        <li class="card__list-item">
          <div class="item-texts">
            <p class="title">{{ $t('dashboard.settings.email_setup.smtp_password.title') }}</p>
            <p class="description">{{ $t('dashboard.settings.email_setup.smtp_password.description') }}</p>
          </div>
          <div class="item-actions">
            <UiInput
                v-model="state.password"
                :errors="validation.$dirty ? validation.$silentErrors : []"
                name="password"
                :placeholder="$t('dashboard.settings.email_setup.smtp_password.title')"
            />
          </div>
        </li>
        <li class="card__list-item">
          <div class="item-texts">
           <p class="title">{{ $t('dashboard.settings.email_setup.smtp_port.title') }}</p>
            <p class="description">{{ $t('dashboard.settings.email_setup.smtp_port.description') }}</p>
          </div>
          <div class="item-actions">
            <UiInput
                v-model="state.port"
                :errors="validation.$dirty ? validation.$silentErrors : []"
                name="port"
                :placeholder="$t('dashboard.settings.email_setup.smtp_port.title')"
            />
          </div>
        </li>
        <li class="card__list-item">
          <div class="item-texts">
            <p class="title">{{ $t('dashboard.settings.email_setup.email_to.title') }}</p>
            <p class="description">{{ $t('dashboard.settings.email_setup.email_to.description') }}</p>
          </div>
          <div class="item-actions">
            <UiInput
                v-model="state.email"
                :errors="validation.$dirty ? validation.$silentErrors : []"
                name="email"
                :placeholder="$t('dashboard.settings.email_setup.email_to.title')"
            />
          </div>
        </li>
        <li class="card__list-item">
          <div class="item-texts">
            <p class="title">{{ $t('dashboard.settings.email_setup.smtp_ssl.title') }}</p>
            <p class="description">{{ $t('dashboard.settings.email_setup.smtp_ssl.description') }}</p>
          </div>
          <div class="item-actions">
            <Toggle v-model="state.use_tls"/>
          </div>
        </li>
      </ul>
      <div class="card__buttons inline-block mt-5">
        <UiButton class="primary" @click.prevent="emailSetupStore.submit">{{ $t('dashboard.settings.save') }}</UiButton>
      </div>
    </form>
  </div>
</template>
<script setup lang="ts">
import UiInput from "@components/ui/Input.vue";
import UiButton from "@components/ui/Button.vue";
import {storeToRefs} from "pinia";
import {useEmailSetupStore} from "@store/dashboard/settings/email-setup.ts";
import {onMounted} from "vue";
import Toggle from "@components/ui/Toggle.vue";

const emailSetupStore = useEmailSetupStore()
const {state, validation} = storeToRefs(emailSetupStore)

onMounted(async () => {
  await emailSetupStore.getEmailSetup()
})
</script>