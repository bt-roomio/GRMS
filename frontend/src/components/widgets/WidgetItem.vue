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
      <template v-if="item.type === 'progress-bar' && (!(Object.keys(data).length == 0) && data[item.device_data_key])">
        <UiProgress :color="item.config.color" :value="data[item.device_data_key].at(0).at(1).toString()"/>
      </template>
      <template v-if="item.type === 'fan-speed'">
        <FanSpeed :value="item"/>
      </template>
      <template v-if="item.type === 'mode'">
        <Mode :value="item"/>
      </template>
      <template v-if="item.type === 'sensor'">
        <Sensor :value="item"/>
      </template>
      <template v-if="item.type === 'slider'">
        <Slider :value="item"/>
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
import {provide, computed, ref, onMounted, nextTick, onUnmounted, watch} from 'vue';
import FanSpeed from "@components/widgets/FanSpeed.vue";
import Mode from "@components/widgets/Mode.vue";
import Sensor from "@components/widgets/Sensor.vue";
import Slider from "@components/widgets/Slider.vue";
import {useWS} from "@store/dashboard/ws";
import {storeToRefs} from "pinia";
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
provide(THEME_KEY, computed(() => cookies.get('mode') || 'light'));

const props = defineProps<{ isSettings: boolean, item: {[key: string]: any} }>()
const storeWs = useWS()
const {data: dataWs, status} = storeToRefs(storeWs)
const data = ref<{[key: string]: any}>({})

watch(dataWs, value => {
  if (status.value === 'OPEN') {
    data.value = Object.assign(data.value, value.data)
  }
})
onMounted(() => {
  nextTick(() => {
    wAndH.value.width = '100%'
    wAndH.value.height = '100%'
  })
  if (status.value === 'CLOSED'){
    storeWs.open()
  }else {
    storeWs.send({
      "type": "TIMESERIES",
      "entityType": "DEVICE",
      "entityId": props.item.device?.id,
      "scope": "LATEST_TELEMETRY",
    })
  }
})
onUnmounted(() => {
  storeWs.close()
})
</script>