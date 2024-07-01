<template>
  <div class="widget-card" v-if="item">
    <div class="widget-card__head">
      <div
          class="widget-card__title"
          v-if="item.descriptor.default_config.title || isCurrentEdit"
      >
        {{ item.descriptor.default_config.title || (isCurrentEdit ? 'There should be a title here' : '') }}
      </div>
      <div
          class="widget-card__description"
          v-if="item.descriptor.default_config.subtitle || isCurrentEdit"
      >
        {{ item.descriptor.default_config.subtitle || (isCurrentEdit ? 'There should be a subtitle here' : '') }}
      </div>
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
      <template v-if="item.fqn === 'progress_bar'">
        <UiProgress :value="item.descriptor.default_config"/>
      </template>
      <template v-if="item.fqn === 'system_mode'">
        <template v-if="item.descriptor.default_config.type === 'Toggle'">
          <Mode :values="item.descriptor.default_config.controls"/>
        </template>
        <template v-if="item.descriptor.default_config.type === 'Sensor'">
          <Sensor :values="item.descriptor.default_config.controls"/>
        </template>
        <template v-if="item.descriptor.default_config.type === 'Slider'">
          <Slider :values="item.descriptor.default_config.controls"/>
        </template>
      </template>
      <template v-if="item.fqn === 'room_temperature'">
        <FanSpeed :value="item.descriptor.default_config"/>
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
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
const cookies = useCookies(['mode'])
const option = computed(() => props.item.config.setting)
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {editWidget} = storeToRefs(storeConfigurationDashboard)
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
const isCurrentEdit = computed(() => JSON.stringify(props.item) === JSON.stringify(editWidget.value))
onMounted(() => {
  nextTick(() => {
    wAndH.value.width = '100%'
    wAndH.value.height = '100%'
  })
  if (props.item?.descriptor?.default_config.entityId){
    send({
      "type": "TIMESERIES",
      "entityType": props.item?.descriptor?.default_config.entityType,
      "entityId": props.item?.descriptor?.default_config.entityId,
      "scope": "LATEST_TELEMETRY",
    })
  }
})

onUnmounted(() => {
  if (data.value){
    unSubscription(data.value.subscriptionId)
  }
})
</script>