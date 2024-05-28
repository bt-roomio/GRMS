<template>
  <div class="statistics-card">
    <p class="statistics-card__title">{{data.name}}</p>
    <div class="statistics-card__value">
      <span>{{data.value}}</span>
      <p class="difference" :class="data.difference_sign === '+' ? 'positive' : 'negative'">
        {{data.difference_sign}} {{data.difference_value}}
        <small>vs 24h</small>
      </p>
    </div>
  </div>
</template>
<script setup lang="ts">
defineProps<{
  data: IStatisticsCard
}>()
</script>