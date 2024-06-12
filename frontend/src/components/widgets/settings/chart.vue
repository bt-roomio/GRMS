<template>
  <UiInput
      label="Title*"
      name="title"
      v-model="state.title"
      placeholder="Write the title"
  />
  <UiInput
      label="Description"
      name="description"
      v-model="state.description"
      placeholder="Write the description"
  />
  <p class="font-semibold">Grid</p>
  <div class="ui-form__row col-2">
    <UiInput v-model="state.grid.top" name="grid[top]" label="Top" icon="percent" icon-position="right"/>
    <UiInput v-model="state.grid.right" name="grid[right]" label="Right" icon="percent" icon-position="right"/>
    <UiInput v-model="state.grid.bottom" name="grid[bottom]" label="Bottom" icon="percent" icon-position="right"/>
    <UiInput v-model="state.grid.left" name="grid[left]" label="Left" icon="percent" icon-position="right"/>
  </div>
  <p class="font-semibold">Series</p>
<!--  <div class="ui-form__row col-2">-->
<!--    <UiInput name="grid[top]" label="Top" mask="##{%}"/>-->
<!--    <UiInput name="grid[right]" label="Right" mask="##{%}"/>-->
<!--    <UiInput name="grid[bottom]" label="Bottom" mask="##%"/>-->
<!--    <UiInput name="grid[left]" label="Left" mask="##%"/>-->
<!--  </div>-->

<!--
{
  "xAxis": {
      "type": "time",
      "axisLine": {
          "show": false
      },
      "axisTick": {
          "show": false
      },
      "axisLabel": {
          "fontSize": 12,
          "fontFamily": "Inter",
          "fontWeight": 400
      }
  },
  "yAxis": {
      "name": "Rooms",
      "type": "value",
      "nameGap": 53,
      "axisLabel": {
          "fontSize": 12,
          "fontFamily": "Inter",
          "fontWeight": 400
      },
      "nameLocation": "middle",
      "nameTextStyle": {
          "fontSize": 12,
          "fontFamily": "Inter",
          "fontWeight": 500
      }
  },
  "legend": {
      "top": 0,
      "data": [
          "Occupancy"
      ],
      "icon": "circle",
      "left": "right",
      "textStyle": {
          "fontSize": 14,
          "fontFamily": "Inter",
          "fontWeight": 400
      }
  },
  "series": [
      {
          "data": [],
          "name": "Occupancy",
          "type": "line",
          "color": "#292930",
          "showSymbol": false
      }
  ],
  "tooltip": {
      "trigger": "axis"
  },
  "backgroundColor": "rgba(255,255,255,0)"
}
-->
</template>
<script setup lang="ts">
import UiInput from "@components/ui/Input.vue";
import {ref} from "vue";
const state = ref({
  title: "",
  description: "",
  grid: {
    top: "12",
    left: "8",
    right: "0",
    bottom: "3",
  },
  xAxis: {
    type: '',
    name: ''
  },
  yAxis: {
    type: '',
    name: ''
  },
  backgroundColor: 'rgba(255,255,255,0)',
  series: [
    {
      name: "",
      type: "line",
      color: "#000",
    }
  ]
})
</script>