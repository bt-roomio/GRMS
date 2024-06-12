<template>
  <div class="rooms-list">
    <div class="rooms-list__head">
      Floor 01, Block B
    </div>
    <div class="rooms-list__content">
      <RoomsCard/>
      <RoomsCard/>
      <RoomsCard/>
      <RoomsCard/>
      <RoomsCard class="warning"/>
      <RoomsCard/>
      <RoomsCard/>
    </div>
  </div>
</template>
<script setup lang="ts">
import RoomsCard from "@components/pages/dashboard/rooms/RoomsCard.vue";
</script>