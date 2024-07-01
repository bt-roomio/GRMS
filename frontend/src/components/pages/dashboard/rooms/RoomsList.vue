<template>
  <div class="rooms-list" v-if="items && items.length">
    <div class="rooms-list__head">
      Floor {{ items.at(0).floor }}, Block {{ items.at(0).block }}
    </div>
    <div class="rooms-list__content">
      <RoomsCard v-for="(item, key) in items" :key="key" :item="item"/>
    </div>
  </div>
</template>
<script setup lang="ts">
import RoomsCard from "@components/pages/dashboard/rooms/RoomsCard.vue";
defineProps(['items'])
</script>