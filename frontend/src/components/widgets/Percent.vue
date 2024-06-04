<template>
  <div class="percent-widget widget-card">
    <div class="widget-card__head">
      <div class="widget-card__title" v-if="configs?.title">{{ configs.title }}</div>
      <div class="widget-card__description mb-6" v-if="configs?.description">{{ configs.description }}</div>
    </div>
    <div class="widget-card__actions" v-if="isSettings">
      <UiButton class="text" @click.prevent="editWidget">
        <UiIcon name="edit" filled />
      </UiButton>
      <UiButton class="text" @click.prevent="deleteWidget">
        <UiIcon name="trash" filled />
      </UiButton>
    </div>
    <div class="widget-card__content" v-if="configs?.value">
      <UiProgress color="red" :value="configs?.value as string"/>
    </div>
  </div>
</template>
<script setup lang="ts">
import UiButton from "@components/ui/Button.vue";
import UiIcon from "@components/ui/Icon.vue";
import UiProgress from "@components/ui/Progress.vue";
defineProps<{
  configs?: { [key: string]: unknown }
  isSettings: boolean,
}>()

const deleteWidget = async () => {}
const editWidget = async () => {}
</script>