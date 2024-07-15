<template>
  <div class="page">
    <div class="page__content">
      <Weather/>
      <Tabs :list="tabList"/>
      <StatisticsCardList/>
      <PageHead title="Your overall stats"/>
      <StatsHead/>
      <WidgetContainer
          v-if="viewModel"
          :isSettings="false"
          v-model="viewModel"
          :widgets="viewWidgets"
      />
    </div>
  </div>
</template>
<script setup lang="ts">
import Weather from "@components/widgets/Weather.vue";
import Tabs from "@components/ui/Tabs.vue";
import {computed, onMounted, onUnmounted} from "vue";
import {useI18n} from "vue-i18n";
import StatisticsCardList from "@components/pages/dashboard/main/StatisticsCardList.vue";
import PageHead from "@components/pages/dashboard/PageHead.vue";
import StatsHead from "@components/pages/dashboard/main/StatsHead.vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import {storeToRefs} from "pinia";
import WidgetContainer from "@components/widgets/WidgetContainer.vue";
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {
  viewModel,
  viewWidgets,
} = storeToRefs(storeConfigurationDashboard)

const {t} = useI18n()
const tabList = computed(() => [
  {
    name: t('dashboard.main.tabs.overview'),
    to: {name: 'main'},
  },
  {
    name: t('dashboard.main.tabs.energy'),
    to: {name: 'main', query: {tab: 'energy'}},
  }
])

onMounted(async () => {
  await Promise.all([
    storeConfigurationDashboard.getItem('e91dd3e9-d109-4924-b82d-95262d4ceece' as string, false),
  ])
  await storeConfigurationDashboard.getDashboardInnerHelpers()
})
onUnmounted(() => {
  storeConfigurationDashboard.$reset()
})
</script>