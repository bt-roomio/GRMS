<script setup lang="ts">
import UiConfirm from "@components/ui/Confirm.vue";
import {useCookies} from "@vueuse/integrations/useCookies";
import {computed, watch} from "vue";
const cookies = useCookies(['mode'])
const hasMode = computed(() => cookies.get('mode'))
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