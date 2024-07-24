<template>
  <ul class="sidebar__menu">
    <MenuItem ref="items" v-for="item in menu" :key="item.name" :item="item" @click="closeAll(item)"/>
  </ul>
</template>
<script setup lang="ts">
import {computed, defineComponent, ref} from "vue";
import MenuItem from "./Item.vue";
import {useI18n} from "vue-i18n";
defineComponent({name: 'SidebarMenu'})
const {t} = useI18n()
const items = ref<object[] | null>(null)
const closeAll = (item: any) => {
  if (items.value) {
      items.value.map((el: any) => {
        if (!item.children.length){
          el.open = false
        }
      })
  }
}
const menu = computed<Item[]>(() => [
  {
    icon: 'dashboard',
    name: t('dashboard.menu.dashboard'),
    to: 'main',
    children: []
  },
  {
    icon: 'key',
    name: t('dashboard.menu.rooms'),
    to: 'rooms',
    children: []
  },
  {
    icon: 'message',
    name: t('dashboard.menu.public_space'),
    to: 'public-space',
    children: []
  },
  {
    icon: 'code-browser',
    name: t('dashboard.menu.configuration'),
    children: [
      {
        icon: 'dashboard',
        to: 'configuration-dashboard',
        name: t('dashboard.menu.dashboard')
      },
      {
        icon: 'user-square',
        to: 'configuration-users',
        name: t('dashboard.menu.users')
      },
      {
        icon: 'user-check',
        to: 'configuration-roles',
        name: t('dashboard.menu.role')
      },
      {
        icon: 'key',
        to: 'configuration-rooms',
        name: t('dashboard.menu.configuration_rooms')
      },
      {
        icon: 'type-square',
        to: 'configuration-room-types',
        name: t('dashboard.menu.room_types')
      },
      {
        icon: 'cpu-chip',
        to: 'configuration-controllers',
        name: t('dashboard.menu.controllers')
      },
    ]
  },
  {
    icon: 'settings',
    to: 'settings',
    name: t('dashboard.menu.settings'),
    children: []
  },
  {
    icon: 'log-in',
    to: 'access',
    name: t('dashboard.menu.access'),
    children: []
  },
  {
    icon: 'presentation-chart',
    to: 'backlog',
    name: t('dashboard.menu.backlog'),
    children: []
  }
] as Item[])
</script>