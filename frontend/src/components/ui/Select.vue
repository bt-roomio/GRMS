<template>
  <div class="ui-select" ref="reference">
    <label v-if="slots.label"><slot name="label"/></label>
    <div class="ui-select__trigger" @click.prevent="isOpen = !isOpen">
      <slot name="trigger"/>
      <UiIcon class="chevron" name="chevron-down" filled/>
    </div>
    <transition name="fade">
      <div class="ui-select__content" ref="floating" :style="floatingStyles" v-if="isOpen">
        <ul class="ui-select__list">
          <li
              :tabindex="key"
              :class="{selected: getItem(item) === modal}"
              class="ui-select__item"
              v-for="(item, key) in data"
              :key="key"
              @click="selected(getItem(item))"
              @keydown.enter="selected(getItem(item))"
          >
            <slot v-if="slots.item" name="item" :item="item" :close="close" />
            <template v-else>
              {{ name ? item[name] : item }}
            </template>
          </li>
        </ul>
      </div>
    </transition>
  </div>
</template>
<script setup lang="ts" generic="T">
import {defineComponent, ref, watch} from "vue";
import UiIcon from "@components/ui/Icon.vue";
import {flip, useFloating} from "@floating-ui/vue";
import {onClickOutside} from "@vueuse/core";
const isOpen = ref(false)
const slots = defineSlots()
const modal = defineModel()
const reference = ref<HTMLElement | null>(null)
const floating = ref<HTMLElement | null>(null)
const {floatingStyles} = useFloating(reference, floating, {middleware: [flip()],});

onClickOutside(reference, () => {
  isOpen.value = false
})
const close = () => isOpen.value = false
const getItem = (item:any) => props.modelKey ? item[props.modelKey] : item
const emit = defineEmits(['change'])
const props = defineProps<{
  data: Record<string, T>[],
  name?: string,
  modelKey?: string,
}>()

const selected = (item:any) => {
  modal.value = item
  emit('change', item)
  close()
}
const arrowControls = (event: KeyboardEvent) => {
  let selectedItem = floating.value?.querySelector(".ui-select__item.selected");
  if (!selectedItem) {
    selectedItem = floating.value?.querySelector(".ui-select__item") as HTMLElement;
    selectedItem?.classList.add("selected");
    return;
  }

  if (event.key === "ArrowDown") {
    event.preventDefault();
    let nextItem = selectedItem.nextElementSibling as HTMLElement;
    if (nextItem) {
      selectedItem.classList.remove("selected");
      nextItem.classList.add("selected");
      nextItem.focus()
    }
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    let prevItem = selectedItem.previousElementSibling as HTMLElement;
    if (prevItem) {
      selectedItem.classList.remove("selected");
      prevItem.classList.add("selected");
      prevItem.focus()
    }
  }
}
watch(isOpen, (value) => {
  if (value){
    window.addEventListener('keydown', arrowControls)
  }else {
    window.removeEventListener('keydown', arrowControls)
  }
})
defineComponent({name: 'UiSelect'})
</script>