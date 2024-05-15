<template>
  <div class="header__time">
    <UiIcon name="clock" filled/>
    {{ clock }}
  </div>
</template>
<script setup lang="ts">
import UiIcon from "../../ui/Icon.vue";
import {onMounted, ref} from "vue";
const clock = ref('00:00:00')

const updateClock = () => {
  const now = new Date();
  const hours = now.getHours();
  const minutes = now.getMinutes();
  const seconds = now.getSeconds();
  clock.value = `${hours}:${minutes < 10 ? '0' : ''}${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
}

onMounted(() => {
  updateClock()
  setInterval(updateClock, 1000);
})
</script>