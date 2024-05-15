<template>
  <div class="page">
    <div class="page__content">
      <PageHead
          :title="$t('dashboard.settings.title')"
      />
      <Tabs :list="tabList"/>
      <RouterView />
    </div>
  </div>
</template>
<script setup lang="ts">
import PageHead from "../../../components/pages/dashboard/PageHead.vue";
import Tabs from "../../../components/ui/Tabs.vue";
import {computed} from "vue";
import {useI18n} from "vue-i18n";
const {t} = useI18n()
const tabList = computed(() => [
  {
    name: t('dashboard.settings.general.title'),
    to: 'settings-general'
  },
  {
    name: t('dashboard.settings.alarms.title'),
    to: 'settings-alarms'
  },
  {
    name: t('dashboard.settings.email_setup.title'),
    to: 'settings-email-setup'
  }
])
</script>