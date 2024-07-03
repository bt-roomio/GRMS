<template>
  <div class="stats__head">
    <div class="stats__head-sorts">
      <UiButton :class="sortWidgets !== 2 ? 'text' : 'primary'" @click.prevent="changeSort(2)">{{$t('dashboard.main.stats.today')}}</UiButton>
      <UiButton :class="sortWidgets !== 7 ? 'text' : 'primary'" @click.prevent="changeSort(7)">{{$t('dashboard.main.stats.one_week')}}</UiButton>
      <UiButton :class="sortWidgets !== 30 ? 'text' : 'primary'" @click.prevent="changeSort(30)">{{$t('dashboard.main.stats.one_month')}}</UiButton>
      <UiButton :class="sortWidgets !== 365 ? 'text' : 'primary'" @click.prevent="changeSort(365)">{{$t('dashboard.main.stats.one_year')}}</UiButton>
    </div>
    <div class="stats__head-period">
      <UiButton class="text">
        <UiIcon name="calendar" filled/>
        {{$t('dashboard.main.stats.choose_period')}}
      </UiButton>
    </div>
    <div class="stats__head-settings">
      <UiButton class="text" @click.prevent="handleSettings">
        <UiIcon name="settings" filled/>
        {{ $t('dashboard.settings.title') }}
      </UiButton>
    </div>
  </div>
</template>
<script setup lang="ts">
import UiButton from "@components/ui/Button.vue";
import UiIcon from "@components/ui/Icon.vue";
import {useMainWidgetSetting} from "@store/dashboard/widget/widget.ts";
import {storeToRefs} from "pinia";
import {useRouter} from "vue-router";
const {push} = useRouter()
const storeMainWidgetSetting = useMainWidgetSetting()
const {sortWidgets} = storeToRefs(storeMainWidgetSetting)
const handleSettings = async () => {
  await push({name: 'configuration-dashboard-inner', params: {id: 'e91dd3e9-d109-4924-b82d-95262d4ceece'}})
}

const changeSort = (val: number) => {
  sortWidgets.value = val
}
</script>