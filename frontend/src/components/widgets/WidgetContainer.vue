<template>
  <GridLayout
      v-if="currentModal"
      :responsiv="true"
      v-model:layout="currentModal"
      :col-num="12"
      :row-height="105"
      :is-draggable="isSettings"
      :is-resizable="isSettings"
      :vertical-compact="true"
      :margin="[16, 16]"
  >
    <GridItem
        v-for="item in currentModal"
        :key="item.i"
        :x="item.x"
        :y="item.y"
        :w="item.w"
        :h="item.h"
        :i="item.i"
    >
        <component :is="components[item.i as keyof typeof components] "/>
    </GridItem>
  </GridLayout>
</template>
<script setup lang="ts">
import { GridLayout, GridItem } from 'grid-layout-plus'
import OccupancyRate from "@components/widgets/OccupancyRate.vue";
import RoomAvailability from "@components/widgets/RoomAvailability.vue";
import {computed, onMounted, ref, watch} from "vue";
const props = defineProps<{ isSettings: boolean }>()
const config = defineModel<IModelObj[] | null>('config')
const layout = defineModel<IModelObj[] | null>('layout')
const currentModal = ref<IModelObj[] | null>(null)
const isConfigs = computed(() => props.isSettings)
const components = {
  OccupancyRate,
  RoomAvailability,
};

onMounted(() => {
  currentModal.value = layout.value as IModelObj[]
})
watch(isConfigs, value => {
  currentModal.value = value ? config.value as IModelObj[] : layout.value as IModelObj[]
})

interface IModelObj { i: keyof typeof components | string, x: number, y:number, w: number, h:number, minH?: number, minW?: number }
</script>