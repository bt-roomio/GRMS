<template>
  <span
      class="ui-icon"
      :class="{ 'ui-icon--fill': !filled, 'ui-icon--stroke': hasStroke && !filled }"
      v-html="icon"
  />
</template>

<script setup lang="ts">
import {defineComponent, onMounted, ref, watchEffect} from "vue";

const props = withDefaults(defineProps<{
  name: string;
  filled?: boolean
}>(), { filled: false, name: 'x-close' })


const icon = ref<string | Record<string, any>>('')
let hasStroke = false

async function getIcon () {
  try {
    const iconsImport = import.meta.glob('../../assets/icons/**/**.svg', {
      import: 'default',
      query: 'raw',
      eager: false
    }) as any
    const rawIcon = await iconsImport[`../../assets/icons/${props.name}.svg`]()
    if (rawIcon.includes('stroke')) { hasStroke = true }
    icon.value = rawIcon
  } catch {
    console.error(
        `[nuxt-icons] Icon '${props.name}' doesn't exist in 'assets/icons'`
    )
  }
}
onMounted(async () => {
  await getIcon()
})

watchEffect(async () => {
  await getIcon()
})
defineComponent({name: 'UiIcon'})
</script>
