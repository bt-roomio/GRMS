<template>
  <div class="widget-card">
    <div class="widget-card__head">
      <div class="widget-card__title" v-if="item.config.title">{{ item.config.title }}</div>
      <div class="widget-card__description" v-if="item.config.description">{{ item.config.description }}</div>
    </div>
    <div class="widget-card__actions" v-if="isSettings">
      <UiButton class="text" @click.prevent="$emit('edit', item)">
        <UiIcon name="edit" filled />
      </UiButton>
      <UiButton class="text">
        <UiIcon name="trash" filled />
      </UiButton>
    </div>
    <div class="widget-card__content">
      <div v-if="item.type === 'chart'" :style="wAndH">
        <v-chart class="chart" :option="option" autoresize/>
      </div>
      <template v-if="item.type === 'progress-bar'">
        <UiProgress :color="item.config.color" :value="item.device.telemetry.at(0)[item.device_data_key] as string"/>
      </template>
    </div>
  </div>
</template>
<script setup lang="ts">
import UiButton from "@components/ui/Button.vue";
import UiIcon from "@components/ui/Icon.vue";
import {BarChart, LineChart} from "echarts/charts";
import {useCookies} from "@vueuse/integrations/useCookies";
import UiProgress from "@components/ui/Progress.vue";
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent
} from 'echarts/components';
import VChart, { THEME_KEY } from 'vue-echarts';
import {provide, computed, ref, onMounted, nextTick} from 'vue';
const cookies = useCookies(['mode'])
const option = computed(() => props.item.config.setting)
const wAndH = ref({
  width: '10px',
  height: '10px'
})
defineEmits(['edit'])
use([
  CanvasRenderer,
  BarChart,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
]);
const props = defineProps<{ isSettings: boolean, item: {[key: string]: any} }>()
provide(THEME_KEY, computed(() => cookies.get('mode') || 'light'));

onMounted(() => {
  nextTick(() => {
    wAndH.value.width = '100%'
    wAndH.value.height = '100%'
  })
})
</script>