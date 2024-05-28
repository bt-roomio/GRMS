<template>
  <div class="sidebar__head">
    <div class="sidebar__head-logo">
      <RouterLink :to="{name: 'main'}">
        <UiIcon name="logo-text"/>
      </RouterLink>
    </div>
    <div class="sidebar__head-burger">
      <UiIcon name="menu" filled/>
    </div>
  </div>
</template>
<script setup lang="ts">
import UiIcon from "../../ui/Icon.vue";
import {defineComponent} from "vue";
defineComponent({name: 'SidebarHead'})
</script>