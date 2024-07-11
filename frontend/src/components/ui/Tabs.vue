<template>
  <div class="tabs" ref="tabs">
    <div class="tabs__list">
      <RouterLink
          v-if="type !== 'hash'"
          v-for="(item, key) in list"
          :key="key"
          @mouseenter="mouseEnterHandle"
          @mouseleave="mouseLeaveHandle"
          :to="item.to as RouteLocationRaw"
          class="tabs__item"
      >
        {{item.name}} <div v-if="item.badge" class="tabs__badge">{{item.badge}}</div>
      </RouterLink>
      <div
          v-else
          v-for="item in list"
          :key="item.name"
          @mouseenter="mouseEnterHandle"
          @mouseleave="mouseLeaveHandle"
          :data-hash="item.hash"
          class="tabs__item"
          @click="model = item.hash"
      >
        {{item.name}} <div v-if="item.badge" class="tabs__badge">{{item.badge}}</div>
      </div>

      <span class="tabs__line" :style="`left: ${linePosition.left}px; top: ${linePosition.top}px; width: ${lineWidth}px`"></span>
    </div>
  </div>
</template>
<script setup lang="ts">
import {nextTick, onMounted, ref, watch} from "vue";
import {RouteLocationRaw} from "vue-router";
import router from "@/router";
defineEmits(['change'])
const model = defineModel()
const props = defineProps<{ list: ITab[], type?: string}>()
const tabs = ref<HTMLElement | null>(null)
const linePosition = ref({
  left: 0,
  top: 0
})
const lineWidth = ref(0)
const mouseEnterHandle = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  setPosition(target)
}
const mouseLeaveHandle = () => {
  setActiveLine()
}

watch(props, () => {
  nextTick(() => {
    setActiveLine()
  })
})
const setActiveLine = () => {
  if (props.type !== 'hash'){
    const activeElement = tabs.value?.querySelector(`[href="${router.currentRoute.value.fullPath}"]`) as HTMLElement
    setPosition(activeElement)
  }else {
    if (model.value) {
      const activeElement = tabs.value?.querySelector(`[data-hash="${model.value}"]`) as HTMLElement
      setPosition(activeElement)
    }
  }
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