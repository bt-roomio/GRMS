<template>
  <teleport to="body">
    <transition>
    <div class="ui-confirm" v-if="confirm.isOpen">
      <div class="ui-confirm__wrapper"></div>
      <div class="ui-confirm__scroller">
        <div class="ui-confirm__body" ref="refConfirm">
          <div class="ui-confirm__head">
            <h2>{{ confirm.title }}</h2>
            <p v-if="confirm.subtitle">{{ confirm.subtitle }}</p>
            <UiIcon name="x-close" @click.prevent="confirmStore.handleCancel"/>
          </div>
          <div class="ui-confirm__content" v-if="confirm.content">
            {{confirm.content}}
          </div>
          <div class="ui-confirm__footer">
            <UiButton :class="confirm.buttons?.cancel.class" @click="confirmStore.handleCancel">{{ confirm.buttons?.cancel.text }}</UiButton>
            <UiButton :class="confirm.buttons?.confirm.class" @click="confirmStore.handleConfirm">{{ confirm.buttons?.confirm.text }}</UiButton>
          </div>
        </div>
      </div>
    </div>
    </transition>
  </teleport>

</template>
<script setup lang="ts">
import {defineComponent, onMounted, ref} from "vue";
import {useConfirm} from "@store/dashboard/useConfirm.ts";
import UiButton from "@components/ui/Button.vue";
import {storeToRefs} from "pinia";
import UiIcon from "@components/ui/Icon.vue";
import {onClickOutside} from "@vueuse/core";
const refConfirm = ref(null)
onClickOutside(refConfirm, () => {
  confirmStore.handleCancel()
})
const confirmStore = useConfirm()
const {confirm} = storeToRefs(confirmStore)
onMounted(() => {
  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' || event.key === 'Esc') {
      confirmStore.handleCancel()
    }
  });
})

defineComponent({name: 'UiConfirm'})
</script>