<template>
  <div class="ui-select" ref="reference">
    <label v-if="label">{{ label }}</label>
    <div class="ui-select__trigger" @click.prevent="isOpen = !isOpen">
      <template v-if="slots.trigger"><slot name="trigger"/></template>
      <template v-else-if="model?.length">
        <span class="line-clamp-1">{{ model?.join(', ') }}</span>
      </template>
      <span class="ui-select__placeholder" v-else>{{$t('dashboard.select_empty')}}</span>
      <UiIcon class="chevron" name="chevron-down" filled/>
    </div>
    <transition name="fade">
      <div class="ui-select__content" ref="floating" :style="floatingStyles" v-if="isOpen">
        <ul class="ui-select__list">
          <li
              :tabindex="key"
              class="ui-select__item"
              v-for="(item, key) in data"
              :key="key"
              @click="selected(item)"
              @keydown.enter="selected(item)"
          >
            <slot v-if="slots.item" name="item" :item="item" :close="close" />
            <template v-else>
              <UiCheckbox :checked="model?.includes(getItem(item))" disabled/>
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
import UiCheckbox from "@components/ui/Checkbox.vue";
const isOpen = ref(false)
const slots = defineSlots()
const model = defineModel<string[]>()
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
  data: {[key: string]: unknown}[],
  name: string,
  label?: string,
  modelKey?: string,
}>()

const selected = (item:any) => {
  if (model.value?.includes(getItem(item))){
    model.value = model.value?.filter((el) => el !== getItem(item))
  }else {
    model.value?.push(getItem(item))
  }
  emit('change', getItem(item))
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
defineComponent({name: 'UiMultiSelect'})
</script>