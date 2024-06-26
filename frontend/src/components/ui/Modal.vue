<template>
  <teleport to="body">
    <transition>
      <div class="modal" v-if="isOpen">
        <div class="modal__wrapper" @click.prevent="close()"></div>
        <div class="modal__body">
          <div class="modal__head">
            <slot name="head"/>
            <UiIcon name="x-close" @click.prevent="close()"/>
          </div>
          <div class="modal__content" v-if="$slots.default">
            <slot />
          </div>
          <div class="modal__footer">
            <slot name="footer" :close="close" :closeWithoutEvents="closeWithoutEvents"/>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>
<script setup lang="ts">
import {defineComponent, nextTick, ref} from "vue";
import UiIcon from "@components/ui/Icon.vue";

const isOpen = ref(false)
const emit = defineEmits(['closed', 'opened'])

const close = () => {
  isOpen.value = false
  nextTick(() => {
    emit('closed')
  })
}
const closeWithoutEvents = () => {
  isOpen.value = false
}
const open = () => {
  isOpen.value = true
  nextTick(() => {
    emit('opened')
  })
}
defineComponent({name: 'UiModal'})
defineExpose({close, open, closeWithoutEvents})
</script>