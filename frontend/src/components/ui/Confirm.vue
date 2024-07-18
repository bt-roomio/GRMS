<template>
  <teleport to="body">
    <transition>
    <div class="ui-confirm" :class="cookies.get('mode')" v-if="confirm.isOpen">
      <div class="ui-confirm__wrapper"></div>
      <div class="ui-confirm__scroller">
        <div class="ui-confirm__body" ref="refConfirm">
          <div class="ui-confirm__head">
            <UiIcon v-if="confirm.icon" :name="confirm.icon" filled/>
            <UiIcon class="close" name="x-close" @click.prevent="confirmStore.handleCancel" filled/>
          </div>
          <div class="ui-confirm__content" v-if="confirm.content">
            <h2>{{ confirm.title }}</h2>
            <p class="break-words break-all" v-html="confirm.content"></p>
          </div>
          <div class="ui-confirm__footer">
            <UiButton class="w-full" v-if="confirm.buttons?.cancel" :class="confirm.buttons?.cancel?.class" @click="confirmStore.handleCancel">{{ confirm.buttons?.cancel.text }}</UiButton>
            <UiButton class="w-full" v-if="confirm.buttons?.confirm" :class="confirm.buttons?.confirm?.class" @click="confirmStore.handleConfirm">{{ confirm.buttons?.confirm.text }}</UiButton>
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
import {useCookies} from "@vueuse/integrations/useCookies";
const cookies = useCookies(['mode'])
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