<template>
  <div class="mode">
    <ul>
      <li v-for="(item, key) in values" :key="key">
        {{ item.title || 'There should be a title here' }}
        <UiToggle :model-value="true"/>
      </li>
    </ul>
  </div>
</template>
<script setup lang="ts">
import UiToggle from "@components/ui/Toggle.vue";
defineProps(['values'])
</script>