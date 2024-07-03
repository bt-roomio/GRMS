<template>
  <div class="rooms-list" v-if="items && items.length">
    <div class="rooms-list__head">
      {{ $t('dashboard.configuration.rooms.floor') }} {{ items.at(0).floor }}, {{ $t('dashboard.configuration.rooms.block') }} {{ items.at(0).block }}
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