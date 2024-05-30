<template>
  <div class="ui-select">
    <label class="ui-select__label" v-if="label">{{ label }}</label>
    <div v-if="model?.length" class="ui-select__active-box">
      <UiIcon class="ui-select__delete-all" name="x-close" @click.prevent="model = []" filled/>
      <span v-for="item in model">
        {{ item }}
        <UiIcon name="x-close" @click.prevent="model = model.filter(el => el !== item)" filled/>
      </span>
    </div>
    <div class="ui-select__body" ref="selectBody">
      <div class="ui-select__trigger" @click.prevent="toggle()" ref="reference">
        <template v-if="slots.trigger"><slot name="trigger"/></template>
        <UiInput v-else type="text" name="select" @input="performSearch($event.target.value)" :placeholder="$t('dashboard.select_empty')" />
        <UiIcon class="chevron" name="chevron-down" filled />
      </div>
      <transition name="fade">
        <div class="ui-select__content" ref="floating" :style="floatingStyles" v-if="isOpen">
          <ul class="ui-select__list">
            <li
                :tabindex="key"
                class="ui-select__item"
                :class="{selected: model?.includes(getItem(item))}"
                v-for="(item, key) in data"
                :key="key"
                @click="selected(item)"
                @keydown.enter="selected(item)"
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

  </div>

</template>
<script setup lang="ts" generic="T">
import {defineComponent, ref, watch} from "vue";
import UiIcon from "@components/ui/Icon.vue";
import {flip, offset, useFloating} from "@floating-ui/vue";
import {onClickOutside} from "@vueuse/core";
import UiInput from "@components/ui/Input.vue";
const isOpen = ref(false)
const slots = defineSlots()
const model = defineModel<string[]>()
const reference = ref<HTMLElement | null>(null)
const floating = ref<HTMLElement | null>(null)
const selectBody = ref<HTMLElement | null>(null)
const {floatingStyles} = useFloating(reference, floating, {
  middleware: [flip(), offset(5)],
});

onClickOutside(selectBody, () => {
  close()
})
const close = () => isOpen.value = false
const toggle = () => {
  isOpen.value = !isOpen.value
}
const getItem = (item:any) => props.modelKey ? item[props.modelKey] : item
const emit = defineEmits(['change', 'search'])
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
const performSearch = debounce(async (query: string) => {
  emit('search', query)
}, 500);
function debounce<T extends (...args: any[]) => void>(func: T, wait: number): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>): void => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}
defineComponent({name: 'UiMultiSelect'})
</script>