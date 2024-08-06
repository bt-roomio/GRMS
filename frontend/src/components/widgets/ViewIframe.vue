<template>
  <div class="iframe-container">
    <iframe
        :src="value.url"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowfullscreen
        referrerpolicy="strict-origin-when-cross-origin"
        :loading="value.loading"
    ></iframe>
  </div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue';
defineProps(['value']);
</script>