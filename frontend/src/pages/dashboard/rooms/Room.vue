<template>
  <div class="page">
    <div class="page__content">
      <PageHead
          back-to="/rooms/room-list"
          back="Back to rooms"
          title="Room 0701, floor 1"
      />
      <RoomActions/>
      <Tabs :list="tabList"/>
      <WidgetContainer
          :is-settings="false"
          v-model:layout="dashboardSettings"
      />
    </div>
  </div>
</template>
<script setup lang="ts">
import PageHead from "@components/pages/dashboard/PageHead.vue";
import RoomActions from "@components/pages/dashboard/rooms/RoomActions.vue";
import Tabs from "@components/ui/Tabs.vue";
import {computed, ref} from "vue";
import {useI18n} from "vue-i18n";
import WidgetContainer from "@components/widgets/WidgetContainer.vue";
const {t} = useI18n()

const tabList = computed(() => [
  {
    name: 'Room controls',
    to: {name: 'room-inner'},
  },
  {
    name: t('dashboard.menu.backlog'),
    to: {name: 'room-inner', query: { tab: 'backlog' }},
  },
  {
    name: 'HVAC',
    to: {name: 'room-inner', query: { tab: 'HVAC' }},
  }
])
const dashboardSettings = ref([
  {
    "i": "2d07b30f",
    "type": "fan-speed",
    "x": 0,
    "y": 0,
    "w": 6,
    "h": 39,
    "config": {
      "title": "Current Fan Speed",
      "description": "You can manage current Fan Speed",
    }
  },
  {
    "i": "2d0das7b30f",
    "type": "mode",
    "x": 6,
    "y": 0,
    "w": 6,
    "h": 32,
    "config": {
      "title": "System Mode",
      "description": "Select one of the operating modes",
    },
  },
  {
    "i": "2d0das72b30f",
    "type": "sensor",
    "x": 0,
    "y": 0,
    "w": 6,
    "h": 23,
    "config": {
      "title": "General sensor",
      "description": "Select one of the operating modes",
    },
  },
  {
    "i": "2d0das7asd2b30f",
    "type": "slider",
    "x": 6,
    "y": 0,
    "w": 6,
    "h": 42,
    "config": {
      "title": "Lighting settings",
      "description": "Select one of the operating modes",
    },
  }
])
</script>