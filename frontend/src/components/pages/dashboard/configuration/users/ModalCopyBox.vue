<template>
  <Modal ref="copyBox" @closed="copyText = ''">
    <template #head>
      <h2>{{copyTitle}}</h2>
    </template>
    <div class="relative bg-gray-50 rounded-lg dark:bg-gray-700 p-4 break-words break-all mb-4 border-dashed border-2" ref="copyElement">{{copyText}}</div>
    <UiButton class="primary w-full" @click.prevent="copy">{{$t('dashboard.widget.form.copy')}}</UiButton>
    <template #footer="{close}">
      <UiButton class="text" @click.prevent="close()">
        {{ $t('dashboard.configuration.rooms.modals.add_new_rooms.cancel') }}
      </UiButton>
    </template>
  </Modal>
</template>
<script setup lang="ts">
import Modal from "@components/ui/Modal.vue";
import UiButton from "@components/ui/Button.vue";
import {ref} from "vue";
import {toast} from "vue3-toastify";
const copyBox = ref<IModal | null>(null)
const copyElement = ref<HTMLElement | null>()
const copyText = ref('')
const copyTitle = ref('')

const close = () => {
  copyBox.value?.close()
}
const open = ({title, text}: {title: string, text: string}) => {
  copyTitle.value = title
  copyText.value = text
  copyBox.value?.open()
}
const copy = () => {
  if (copyElement.value) {
    const range = document.createRange();
    range.selectNode(copyElement.value);
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(range);

    try {
      const successful = document.execCommand('copy');
      const msg = successful ? 'successful' : 'unsuccessful';
      toast.success('Text copied: ' + msg);
    } catch (err) {
      console.error('Oops, unable to copy', err);
    }
    selection?.removeAllRanges();
  }
}

defineExpose({
  close,
  open,
})
</script>