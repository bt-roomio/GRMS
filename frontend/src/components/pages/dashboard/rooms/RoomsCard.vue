<template>
  <div class="rooms-card">
    <div class="rooms-card__number">
      <p>0022</p>
    </div>
    <div class="rooms-card__type">
      Superior room
    </div>
    <div class="rooms-card__degree">
      23,8 °C
    </div>
    <div class="rooms-card__actions">
      <UiSmallButton class="">
        <UiIcon name="wind" filled/>
        1
      </UiSmallButton>
      <UiSmallButton class="inactive">
        <UiIcon name="brush" filled/>
      </UiSmallButton>
      <UiSmallButton class="active">
        <UiIcon name="wifi" filled/>
      </UiSmallButton>
      <UiSmallButton class="inactive">
        <UiIcon name="alert-circle" filled/>
      </UiSmallButton>
    </div>
  </div>
</template>
<script setup lang="ts">
import UiSmallButton from "@components/ui/ButtonSmall.vue";
import UiIcon from "@components/ui/Icon.vue";
</script>