<template>
  <li class="sidebar__menu-item" >
    <RouterLink v-if="!item.children?.length" :to="{name: item.to}" class="item-content">
      <UiIcon class="item-icon" :name="item.icon" filled/>
      <div class="item-text">{{ item.name }}</div>
    </RouterLink>
    <div v-else class="item-content" @click="open = !open">
      <UiIcon class="item-icon" :name="item.icon" filled/>
      <div class="item-text">{{ item.name }}</div>
      <div class="item-action"><UiIcon name="chevron-down" filled/></div>
    </div>
    <ul ref="submenu" class="item-submenu overflow-hidden" v-if="item.children?.length && open" @click="sidebarIsOpen ? open = false : null">
      <li class="sidebar__menu-head">
        {{ item.name }}
      </li>
      <li class="sidebar__menu-item" v-for="child in item.children" :key="child.name">
        <RouterLink :to="{name: child.to}" class="item-content">
          <UiIcon class="item-icon" name="dashboard" filled/>
          <div class="item-text">{{ child.name }}</div>
        </RouterLink>
      </li>
    </ul>
  </li>
</template>
<script setup lang="ts">
import UiIcon from "../../ui/Icon.vue";
import {defineComponent, ref} from "vue";
import {useTemplateStore} from "@store/template.ts";
import {storeToRefs} from "pinia";
const storeTemplate = useTemplateStore()
const {sidebarIsOpen} = storeToRefs(storeTemplate)
const open = ref(false)
const submenu = ref<HTMLElement | null>(null)
defineProps<{
  item: Item
}>()

defineExpose({open})
defineComponent({name: 'MenuItem'})
</script>