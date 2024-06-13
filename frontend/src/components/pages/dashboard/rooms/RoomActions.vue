<template>
  <div class="flex gap-4 mb-6">
    <UiStatus status="Available" class="on h-8"/>
    <UiBadge class="bg-gray-200 font-medium h-8">Superior room</UiBadge>
    <UiBadge class="bg-warning-200 font-bold h-8">23,8 °C</UiBadge>
    <UiBadge class="bg-gray-200 font-medium h-8">
      <UiIcon name="wind" filled/>
      1
    </UiBadge>
    <UiBadge class="bg-gray-200 font-medium h-8">
      <UiIcon name="brush" filled/>
    </UiBadge>
    <UiBadge class="bg-gray-200 font-medium h-8">
      <UiIcon name="wifi" filled/>
    </UiBadge>
    <UiBadge class="bg-gray-200 font-medium h-8">
      <UiIcon name="alert-circle" filled/>
    </UiBadge>
  </div>
</template>
<script setup lang="ts">
import UiStatus from "@components/ui/Status.vue";
import UiBadge from "@components/ui/Badge.vue";
import UiIcon from "@components/ui/Icon.vue";
</script>