<template>
  <div class="dropdown" ref="dropdown">
    <div class="dropdown__trigger" ref="reference" @click="handleTrigger">
      <slot
          name="trigger"
          :open="open"
      ></slot>
    </div>
    <transition name="fade">
      <div ref="floating" :style="floatingStyles" class="dropdown__content" v-if="open">
        <slot name="content" :close="close"></slot>
      </div>
    </transition>
  </div>
</template>
<script setup lang="ts">
import {defineComponent, onMounted, onUnmounted, ref} from "vue";
import {onClickOutside} from "@vueuse/core";
import {flip, shift, useFloating} from "@floating-ui/vue";
const reference = ref(null)
const floating = ref(null)
const {floatingStyles} = useFloating(reference, floating, {
  middleware: [flip(), shift({padding: 15})],
});
const open = ref<boolean>(false)
const dropdown = ref(null)

onClickOutside(dropdown, () => {
  open.value = false
})

const handleTrigger = () => {
  open.value = !open.value
}
const close = () => {
  open.value = false
}

onMounted(() => {
  window.addEventListener('scroll', () => {open.value = false})
})

onUnmounted(() => {
  window.removeEventListener('scroll', () => {open.value = false})
})
defineComponent({name: 'UiDropdown'})
</script>