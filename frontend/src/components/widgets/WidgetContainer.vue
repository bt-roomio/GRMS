<template>
  <GridLayout
      v-if="currentModel"
      :responsiv="true"
      v-model:layout="currentModel"
      :col-num="12"
      :row-height="4"
      :is-draggable="isSettings"
      :is-resizable="isSettings"
      :vertical-compact="true"
      :margin="[16, 16]"
      :passive="true"
  >
    <GridItem
        v-for="item in currentModel"
        :key="item.i"
        :x="item.x"
        :y="item.y"
        :w="item.w"
        :h="item.h"
        :i="item.i"
    >
        <WidgetItem :is-settings="isSettings" :item="item" @edit="item => storeMainWidget.editItem(item)"/>
    </GridItem>
  </GridLayout>
</template>
<script setup lang="ts">
import {GridLayout, GridItem, Layout} from 'grid-layout-plus'
import {computed, onMounted, ref, watch} from "vue";
import WidgetItem from "@components/widgets/WidgetItem.vue";
import {useMainWidgetSetting} from "@store/dashboard/widget/main-widget.ts";
const props = defineProps<{ isSettings: boolean }>()
const config = defineModel<IModelObj[] | null>('config')
const layout = defineModel<IModelObj[] | null>('layout')
const currentModel = ref<Layout | null>(null)
const isConfigs = computed(() => props.isSettings)
const storeMainWidget = useMainWidgetSetting()

onMounted(() => {
  currentModel.value = layout.value as Layout
})
watch(isConfigs, value => {
  currentModel.value = value ? config.value as Layout : layout.value as Layout
})

interface IModelObj { [key: string]: any }
</script>