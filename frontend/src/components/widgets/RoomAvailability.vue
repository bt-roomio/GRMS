<template>
  <div class="room-availability widget-card">
    <div class="widget-card__head">
      <div class="widget-card__title">Room availability</div>
      <div class="widget-card__description mb-6">Manage your team members and their account permissions here.</div>
      <div style="width: 100%; height: 310px;">
        <v-chart class="chart" :option="option" autoresize />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { BarChart  } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components';
import VChart, { THEME_KEY } from 'vue-echarts';
import {provide, computed} from 'vue';
import {useCookies} from "@vueuse/integrations/useCookies";
import {storeToRefs} from "pinia";
import {useAvailabilityWidget} from "@store/dashboard/widget/configs/availability.ts";
const cookies = useCookies(['mode'])
const storeAvailabilityWidget = useAvailabilityWidget()
const {exampleData, exampleData2} = storeToRefs(storeAvailabilityWidget)
use([
  CanvasRenderer,
  BarChart,
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
    show: false
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
      name: 'Availability',
      type: 'bar',
      stack: 'a',
      data: exampleData2.value,
      color: '#606271',
    },
    {
      name: 'Availability last year',
      type: 'bar',
      stack: 'a',
      data: exampleData.value,
      color: '#CDCDCD',
      itemStyle: {
        borderRadius: [12, 12, 0, 0]
      },
      lineStyle: {
        width: 1000
      }
    }
  ]
}));

</script>