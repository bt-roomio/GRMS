<template>
  <router-link :to="{name: 'room-inner', params: {id: item.id}}" class="rooms-card" v-if="item">
    <div class="rooms-card__number" :class="item.state.toLowerCase()">
      <p>{{ item.room_number }}</p>
    </div>
    <div class="rooms-card__type">
      {{ item.type }}
    </div>
    <div class="rooms-card__degree">
      23,8 °C
    </div>
    <div class="rooms-card__actions">
      <UiSmallButton class="">
        <UiIcon name="wind" filled/>
        1
      </UiSmallButton>
      <UiSmallButton :class="item.state === 'MakeUpRoom' ? 'active' : 'inactive'">
        <UiIcon name="brush" filled/>
      </UiSmallButton>
      <UiSmallButton :class="item.status === 'OFF' ? 'active' : 'inactive'">
        <UiIcon name="wifi" filled/>
      </UiSmallButton>
      <UiSmallButton class="inactive">
        <UiIcon name="alert-circle" filled/>
      </UiSmallButton>
    </div>
  </router-link>
</template>
<script setup lang="ts">
import UiSmallButton from "@components/ui/ButtonSmall.vue";
import UiIcon from "@components/ui/Icon.vue";
defineProps(['item'])
</script>