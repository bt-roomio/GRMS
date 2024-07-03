<template>
  <GridLayout
      v-if="model"
      :responsiv="true"
      v-model:layout="model"
      :col-num="12"
      :row-height="4"
      :is-draggable="isSettings"
      :is-resizable="isSettings"
      :vertical-compact="true"
      :margin="[16, 16]"
      :passive="true"
  >
    <GridItem
        v-for="(item, key) in model"
        :key="item.i"
        :x="item.x"
        :y="item.y"
        :w="item.w"
        :h="item.h"
        :i="item.i"
        :min-h="item.minH"
        :min-w="item.minW"
    >
      <Teleport to="#app" :disabled="!isCurrentWidgetEdit[key]">
        <WidgetItem
            v-if="widgets"
            :class="{'isEdit': isCurrentWidgetEdit[key]}"
            :is-settings="(isSettings && !isCurrentWidgetEdit[key])"
            :item="widgets[key]"
            @edit="item => emits('edit', {item, key})"
            @delete="emits('delete', key)"
        />
      </Teleport>
    </GridItem>
  </GridLayout>
</template>
<script setup lang="ts">
import {GridLayout, GridItem, Layout} from 'grid-layout-plus'
import WidgetItem from "@components/widgets/WidgetItem.vue";
import {computed} from "vue";
import {useConfigurationDashboardStore} from "@store/dashboard/configuration/dashboard.ts";
import {storeToRefs} from "pinia";
const storeConfigurationDashboard = useConfigurationDashboardStore()
const {editWidget} = storeToRefs(storeConfigurationDashboard)
const props = defineProps<{ isSettings: boolean, widgets: IWidgetType[] | null }>()
const emits = defineEmits(['edit', 'delete'])
const model = defineModel<Layout | null>()
const isCurrentWidgetEdit = computed(() => props.widgets?.map(el => JSON.stringify(el) === JSON.stringify(editWidget.value)) || [])
</script>