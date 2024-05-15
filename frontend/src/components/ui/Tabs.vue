<template>
  <div class="tabs" ref="tabs">
    <div class="tabs__list">
      <RouterLink
          v-for="item in list"
          :key="item.to"
          @mouseenter="mouseEnterHandle"
          @mouseleave="mouseLeaveHandle"
          :to="{name: item.to}"
          class="tabs__item"
      >
        {{item.name}}
      </RouterLink>
      <span class="tabs__line" :style="`left: ${linePosition}px; width: ${lineWidth}px`"></span>
    </div>
  </div>
</template>
<script setup lang="ts">
import {nextTick, onMounted, ref, watch} from "vue";

const props = defineProps<{ list: ITab[]}>()
const tabs = ref<HTMLElement | null>(null)
const linePosition = ref(0)
const lineWidth = ref(0)

const mouseEnterHandle = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  linePosition.value = target.offsetLeft
  lineWidth.value = target.offsetWidth
}
const mouseLeaveHandle = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (target.hasAttribute('aria-current')){
    linePosition.value = target.offsetLeft
    lineWidth.value = target.offsetWidth
  }else {
    setActiveLine()
  }
}

watch(props, () => {
  nextTick(() => {
    setActiveLine()
  })
})
const setActiveLine = () => {
  const activeElement = tabs.value?.querySelector('[aria-current="page"]') as HTMLElement
  linePosition.value = activeElement.offsetLeft
  lineWidth.value = activeElement.offsetWidth
}
onMounted(() => {
  setActiveLine()
})


</script>