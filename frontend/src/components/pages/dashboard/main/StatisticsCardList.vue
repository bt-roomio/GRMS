<template>
  <div class="statistics-card__list">
    <StatisticsCard
      v-for="item in cardList"
      :key="item.name"
      :data="item"
    />
  </div>
</template>
<script setup lang="ts">
import StatisticsCard from "@components/pages/dashboard/main/StatisticsCard.vue";
import {ref} from "vue";

const cardList = ref([
  {
    name: 'Available room',
    difference_value: '23',
    difference_sign: '-',
    value: '1201'
  },
  {
    name: 'Checked in',
    difference_value: '23',
    difference_sign: '+',
    value: '1201'
  },
  {
    name: 'Occupied',
    difference_value: '23',
    difference_sign: '-',
    value: '1201'
  },
  {
    name: 'Do not disturb',
    difference_value: '23',
    difference_sign: '-',
    value: '1201'
  },
  {
    name: 'Make up room',
    difference_value: '23',
    difference_sign: '-',
    value: '1201'
  }
])
</script>