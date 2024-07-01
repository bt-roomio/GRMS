<template>
  <div class="ui_badge" :class="{'dot': isDot}"><slot /></div>
</template>

<script setup lang="ts">
import {defineComponent} from "vue";
defineProps<{isDot?: boolean}>()
defineComponent({name: 'UiBadge'})
</script>