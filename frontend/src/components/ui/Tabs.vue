<template>
  <div class="tabs" ref="tabs">
    <div class="tabs__list">
      <RouterLink
          v-for="item in list"
          :key="item.name"
          @mouseenter="mouseEnterHandle"
          @mouseleave="mouseLeaveHandle"
          :to="item.to as RouteLocationRaw"
          class="tabs__item"
      >
        {{item.name}} <div v-if="item.badge" class="tabs__badge">{{item.badge}}</div>
      </RouterLink>
      <span class="tabs__line" :style="`left: ${linePosition.left}px; top: ${linePosition.top}px; width: ${lineWidth}px`"></span>
    </div>
  </div>
</template>
<script setup lang="ts">
import {nextTick, onMounted, ref, watch} from "vue";
import {RouteLocationRaw, useRoute} from "vue-router";
const props = defineProps<{ list: ITab[]}>()
const tabs = ref<HTMLElement | null>(null)
const linePosition = ref({
  left: 0,
  top: 0
})
const lineWidth = ref(0)
const {fullPath} = useRoute()
const mouseEnterHandle = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  setPosition(target)
}
const mouseLeaveHandle = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (target.hasAttribute('aria-current')){
    setPosition(target)
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
  const activeElement = tabs.value?.querySelector(`[href="${fullPath}"]`) as HTMLElement
  setPosition(activeElement)
}

const setPosition = (element: HTMLElement) => {
  linePosition.value.left = element.offsetLeft
  linePosition.value.top = element.offsetTop + element.offsetHeight - 2
  lineWidth.value = element.offsetWidth
}

onMounted(() => {
  setActiveLine()
})


</script>