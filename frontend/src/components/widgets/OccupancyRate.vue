<template>
  <div class="occupancy-rate widget-card pl">
    <div class="widget-card__head">
      <div class="widget-card__title">Occupancy rate</div>
      <div class="widget-card__description mb-6">Track how your rating compares to your industry average.</div>
      <div style="width: 100%; height: 310px;">
        <v-chart class="chart" :option="option" autoresize />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { LineChart  } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components';
import VChart, { THEME_KEY } from 'vue-echarts';
import {provide, computed} from 'vue';
import {useCookies} from "@vueuse/integrations/useCookies";
import {useOccupancyWidget} from "@store/dashboard/widget/configs/occupancy.ts";
import {storeToRefs} from "pinia";
const cookies = useCookies(['mode'])
const storeOccupancyWidget = useOccupancyWidget()
const {exampleData, exampleData2} = storeToRefs(storeOccupancyWidget)
use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
]);

provide(THEME_KEY, computed(() => cookies.get('mode') || 'light'));

// name: "Wed May 29 2024 14:04:53 GMT+0500 (Узбекистан, стандартное время)"
// value: ['2024/5/29', 22]
const option = computed(() => ({
  backgroundColor: 'rgba(255,255,255,0)',
  legend: {
    left: 'right',
    data: ['Occupancy', 'Occupancy last year'],
    icon: 'circle',
    top: 0,
    textStyle: {
      fontFamily: 'Inter',
      fontSize: 14,
      fontWeight: 400
    }
  },
  tooltip: {
    trigger: 'axis',
  },
  xAxis: {
    type: 'time',
    axisLine: {
      show: false
    },
    axisTick: {
      show: false
    },
    axisLabel: {
      fontFamily: 'Inter',
      fontSize: 12,
      fontWeight: 400
    }
  },
  yAxis: {
    name: 'Rooms',
    type: 'value',
    nameLocation : 'middle',
    nameGap : 53,
    nameTextStyle: {
      fontFamily: 'Inter',
      fontSize: 12,
      fontWeight: 500
    },
    axisLabel: {
      fontFamily: 'Inter',
      fontSize: 12,
      fontWeight: 400
    }
  },
  grid: {
    left: '5%',
    right: '0%',
    top: '12%',
    bottom: '3%',
    containLabel: true
  },
  series: [
    {
      name: 'Occupancy',
      type: 'line',
      showSymbol: false,
      data: exampleData2.value,
      color: '#292930',
    },
    {
      name: 'Occupancy last year',
      type: 'line',
      showSymbol: false,
      data: exampleData.value,
      color: '#8A7D76'
    }
  ]
}));

</script>