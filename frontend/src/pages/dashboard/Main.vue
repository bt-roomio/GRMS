<template>
    <div class="page">
      <div class="page__content">
        <Weather/>
        <Tabs :list="tabList"/>
        <StatisticsCardList />
        <PageHead title="Your overall stats" />
        <StatsHead />
        <WidgetContainer
            v-if="dashboardSettings"
            :isSettings="isDashboardSettings"
            v-model:config="dashboardSettingsConfig"
            v-model:layout="dashboardSettings"
        />
      </div>
    </div>
</template>
<script setup lang="ts">
import Weather from "@components/widgets/Weather.vue";
import Tabs from "@components/ui/Tabs.vue";
import {computed, onMounted} from "vue";
import {useI18n} from "vue-i18n";
import {useUserStore} from "@store/dashboard/user";
import StatisticsCardList from "@components/pages/dashboard/main/StatisticsCardList.vue";
import PageHead from "@components/pages/dashboard/PageHead.vue";
import StatsHead from "@components/pages/dashboard/main/StatsHead.vue";
import WidgetContainer from "@components/widgets/WidgetContainer.vue";
import {useMainWidgetSetting} from "@store/dashboard/widget/main-widget.ts";
import {storeToRefs} from "pinia";
const storeUser = useUserStore()
const storeMainWidgetSetting = useMainWidgetSetting()
const {dashboardSettings, isDashboardSettings, dashboardSettingsConfig} = storeToRefs(storeMainWidgetSetting)
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
  await Promise.all([
    storeUser.getUser(),
    storeMainWidgetSetting.getMainDashboardSettings()
  ])

})
</script>