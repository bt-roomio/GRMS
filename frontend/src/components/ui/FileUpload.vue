<template>
  <div
      v-bind:class="$attrs.class"
      class="file-upload"
      @drop.prevent="handleDrop"
      @dragover.prevent
  >
    <label
        for="file-upload"
    >
      <div class="file-upload__content">
        <UiIcon name="import" filled/>
        <template v-if="!file">
          <p class="top-text"><span class="font-semibold">{{ $t('dashboard.file_upload.click_to_upload') }}</span> {{ $t('dashboard.file_upload.or_drag_and_drop') }}</p>
          <p class="format">{{ getFormats(accept) }} {{ $t('dashboard.file_upload.format') }}</p>
        </template>
        <div v-else class="mt-4">
          <p class="top-text"><span class="font-semibold">{{ $t('dashboard.file_upload.selected_file') }}</span>: {{ file.name }}</p>
        </div>
      </div>
      <input id="file-upload" type="file" :accept="accept.toString()" class="hidden" @change="handleFileSelect" />
    </label>
  </div>

</template>

<script setup lang="ts">
import UiIcon from "@components/ui/Icon.vue";

const file = defineModel<File | null>()

const props = defineProps<{
  accept: string[]
}>()
const handleFileSelect = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    const selectedFile = input.files[0]
    if (isAcceptedFile(selectedFile)) {
      file.value = selectedFile
    } else {
      alert(`Please upload a ${getFormats(props.accept)} file.`)
    }
  }
}

const handleDrop = (event: DragEvent) => {
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    const droppedFile = files[0]
    if (isAcceptedFile(droppedFile)) {
      file.value = droppedFile
    } else {
      alert(`Please upload a ${getFormats(props.accept)} file.`)
    }
  }
}

const isAcceptedFile = (file: File) => {
  const fileExtension = file.name.split('.').pop()?.toLowerCase()
  return props.accept.includes(`.${fileExtension}`)
}
const getFormats = (formats: string[]) => {
  return formats.map((el) => (el.replace('.', '').toUpperCase() as string)).join(' or ')
}
</script>