<template>
  <div class="auth__head">
    <div class="logo">
      <UiIcon :name="icon" filled></UiIcon>
    </div>
    <h1 class="title">{{ title }}</h1>
    <p class="description" v-if="description">{{ description }}</p>
  </div>
</template>
<script setup lang="ts">
import UiIcon from "../../ui/Icon.vue";
defineProps<{
  icon: string,
  title: string,
  description?: string
}>()
</script>