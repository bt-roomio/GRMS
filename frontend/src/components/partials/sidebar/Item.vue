<template>
  <li class="sidebar__menu-item">
    <RouterLink v-if="!item.children?.length" :to="{name: item.to}" class="item-content">
      <UiIcon class="item-icon" :name="item.icon" filled/>
      <div class="item-text">{{ item.name }}</div>
    </RouterLink>
    <div v-else class="item-content" @click="open = !open">
      <UiIcon class="item-icon" :name="item.icon" filled/>
      <div class="item-text">{{ item.name }}</div>
      <div class="item-action"><UiIcon name="chevron-down" filled/></div>
    </div>
    <transition name="dropdown">
      <ul ref="submenu" class="item-submenu overflow-hidden" v-if="item.children?.length && open">
        <li class="sidebar__menu-item" v-for="child in item.children" :key="child.name">
          <RouterLink :to="{name: child.to}" class="item-content">
            <UiIcon class="item-icon opacity-0" name="dashboard" filled/>
            <div class="item-text">{{ child.name }}</div>
          </RouterLink>
        </li>
      </ul>
    </transition>

  </li>
</template>
<script setup lang="ts">
import UiIcon from "../../ui/Icon.vue";
import {defineComponent, ref} from "vue";
const open = ref(false)
const submenu = ref<HTMLElement | null>(null)
defineProps<{
  item: Item
}>()

defineExpose({open})
defineComponent({name: 'MenuItem'})

// onMounted(() => {
//   console.log(submenu.value?.querySelector(`[href="${fullPath}"]`))
// })
</script>

<style>
.dropdown-enter-active {
  animation: dropdown-in 0.5s;
  overflow: hidden;
}
.dropdown-leave-active {
  animation: dropdown-in 0.5s reverse;
}
@keyframes dropdown-in {
  0% {
    height: 0;
  }
  100% {
    height: 176px;
  }
}
</style>