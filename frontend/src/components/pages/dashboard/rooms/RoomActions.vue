<template>
  <div class="flex gap-4 mb-6" v-if="item">
    <UiStatus :status="item.state" class="on h-8"/>
    <UiBadge class="bg-gray-200 font-medium h-8" v-if="item.type">{{ item.type.title }}</UiBadge>
    <UiBadge class="bg-warning-200 font-bold h-8">23,8 °C</UiBadge>
    <UiBadge class="bg-gray-200 font-medium h-8">
      <UiIcon name="wind" filled/>
      1
    </UiBadge>
    <UiBadge :isDot="false" :class="item.state === 'MakeUpRoom' ? 'off' : ''" class="bg-gray-200 font-medium h-8">
      <UiIcon name="brush" filled/>
    </UiBadge>
    <UiBadge :isDot="false" :class="item.status === 'OFF' ? 'off' : 'on'" class="bg-gray-200 font-medium h-8">
      <UiIcon name="wifi" filled/>
    </UiBadge>
    <UiBadge :isDot="false" class="bg-gray-200 font-medium h-8">
      <UiIcon name="alert-circle" filled/>
    </UiBadge>
  </div>
</template>
<script setup lang="ts">
import UiStatus from "@components/ui/Status.vue";
import UiBadge from "@components/ui/Badge.vue";
import UiIcon from "@components/ui/Icon.vue";
defineProps<{
  item: IConfigurationRoom | undefined | null
}>()
</script>