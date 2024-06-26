<template>
  <div class="widget-card" v-if="item">
    <div class="widget-card__head">
      <div class="widget-card__title" v-if="item.descriptor.default_config.title">{{ item.descriptor.default_config.title }}</div>
      <div class="widget-card__description" v-if="item.descriptor.default_config.subtitle">{{ item.descriptor.default_config.subtitle }}</div>
    </div>
    <div class="widget-card__actions" v-if="isSettings">
      <UiButton class="text" @click.prevent="$emit('edit', item)">
        <UiIcon name="edit" filled />
      </UiButton>
      <UiButton class="text" @click.prevent="$emit('delete', item)">
        <UiIcon name="trash" filled />
      </UiButton>
    </div>
    <div class="widget-card__content">
      <div v-if="item.type === 'chart'" :style="wAndH">
        <v-chart class="chart" :option="option" autoresize/>
      </div>
      <template v-if="item.type === 'progress-bar'">
        <UiProgress :color="item.config.color" :value="getValueProgress(data?.data, item.device_data_key)"/>
      </template>
      <template v-if="item.type === 'fan-speed'">
        <FanSpeed :value="item"/>
      </template>
      <template v-if="item.descriptor.default_config.type === 'Toggle'">
        <Mode :values="item.descriptor.default_config.controls"/>
      </template>
      <template v-if="item.descriptor.default_config.type === 'Sensor'">
        <Sensor :values="item.descriptor.default_config.controls"/>
      </template>
      <template v-if="item.descriptor.default_config.type === 'Slider'">
        <Slider :values="item.descriptor.default_config.controls"/>
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
import {provide, computed, ref, onMounted, nextTick, onUnmounted} from 'vue';
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
defineEmits(['edit', 'delete'])
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
const {send, unSubscription} = storeWs
const {state} = storeToRefs(storeWs)
const data = computed(() => state.value.events.get(props.item.device?.id))

onMounted(() => {
  nextTick(() => {
    wAndH.value.width = '100%'
    wAndH.value.height = '100%'
  })
  if (props.item?.device?.id){
    send({
      "type": "TIMESERIES",
      "entityType": "DEVICE",
      "entityId": props.item.device?.id,
      "scope": "LATEST_TELEMETRY",
    })
  }
})

onUnmounted(() => {
  if (data.value){
    unSubscription(data.value.subscriptionId)
  }
})

const getValueProgress = (data: any, field: string) => {
  return data ? (data[field]?.at(0).at(1) || 0).toString() : '0'
}
</script>