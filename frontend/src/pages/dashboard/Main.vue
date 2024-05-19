<template>
  <div class="page">
    <div class="page__content">
      <Weather/>
      <Tabs :list="tabList"/>
    </div>
  </div>
</template>
<script setup lang="ts">
import Weather from "@components/widgets/Weather.vue";
import Tabs from "@components/ui/Tabs.vue";
import {computed, onMounted} from "vue";
import {useI18n} from "vue-i18n";
import {useUserStore} from "@store/dashboard/user";
const storeUser = useUserStore()
const {t} = useI18n()
const tabList = computed(() => [
  {
    name: t('dashboard.main.tabs.overview'),
    to: {name: 'main'},
  },
  {
    name: t('dashboard.main.tabs.energy'),
    to: {name: 'main', query: { tab: 'energy' }},
  }
])
onMounted(async () => {
  await storeUser.getUser()
})
</script>