<template>
  <router-link :to="{name: 'room-inner', params: {id: item.id}}" class="rooms-card" v-if="item" :class="{'error': item.status === 'OFF'}">
    <div class="rooms-card__info">
      <div class="rooms-card__number" :class="item.state.toLowerCase()">
        <p>{{ item.room_number }}</p>
      </div>
      <div class="rooms-card__degree">
        t 23,8 °C
      </div>
    </div>
    <div class="rooms-card__actions">
      <div class="actions__item">
        <UiSmallButton class="inactive" v-if="item.state === 'DoNotDistrub'">
          <UiIcon name="alert-circle" filled/>
        </UiSmallButton>
        <UiSmallButton :class="item.state === 'MakeUpRoom' ? 'active' : 'inactive'">
          <UiIcon name="check" filled/>
        </UiSmallButton>
        <p>MUR</p>
      </div>
      <div class="actions__item">
        <UiSmallButton class="warning" v-if="item.status === 'OFF'">
          <UiIcon name="alert-circle" filled/>
        </UiSmallButton>
        <UiSmallButton class="inactive">
          <UiIcon name="alarm-clock-off" filled/>
        </UiSmallButton>
        <p>DND</p>
      </div>
    </div>
  </router-link>
</template>
<script setup lang="ts">
import UiSmallButton from "@components/ui/ButtonSmall.vue";
import UiIcon from "@components/ui/Icon.vue";
defineProps(['item'])
</script>