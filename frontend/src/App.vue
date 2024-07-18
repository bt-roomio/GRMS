<script setup lang="ts">
import UiConfirm from "@components/ui/Confirm.vue";
import {useCookies} from "@vueuse/integrations/useCookies";
import {computed, onMounted, onUnmounted, ref, watch} from "vue";
const cookies = useCookies(['mode', 'access_token'])
const isDarkMode = ref(window.matchMedia('(prefers-color-scheme: dark)').matches);
const hasMode = computed(() => cookies.get('mode') || (isDarkMode.value ? 'dark' : 'light'))

function updateDarkMode(event: any) {
  isDarkMode.value = event.matches;
}

onMounted(() => {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  mediaQuery.addEventListener('change', updateDarkMode);
});

onUnmounted(() => {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  mediaQuery.removeEventListener('change', updateDarkMode);
});

watch(hasMode, value => {
  setMode(value)
})
const setMode = (value: string) => {
  document.body.classList.remove('dark')
  document.body.classList.remove('light')
  document.body.classList.add(value)
}
setMode(hasMode.value)
</script>

<template>
  <UiConfirm/>
  <RouterView/>
</template>