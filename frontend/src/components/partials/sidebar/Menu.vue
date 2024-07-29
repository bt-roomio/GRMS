<template>
  <ul class="sidebar__menu">
    <MenuItem ref="items" v-for="item in menu" :key="item.name" :item="item" @click="closeAll(item)"/>
  </ul>
</template>
<script setup lang="ts">
import {computed, defineComponent, ref} from "vue";
import MenuItem from "./Item.vue";
import {useI18n} from "vue-i18n";
import {usePermissions} from "@store/dashboard/user/permissions.ts";
defineComponent({name: 'SidebarMenu'})
const storePermissions = usePermissions()
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
    children: [],
    show: storePermissions.hasPermission('view_dashboard')
  },
  {
    icon: 'key',
    name: t('dashboard.menu.rooms'),
    to: 'rooms',
    children: [],
    show: storePermissions.hasPermission('view_room')
  },
  {
    icon: 'message',
    name: t('dashboard.menu.public_space'),
    to: 'public-space',
    children: [],
    show: true
  },
  {
    icon: 'code-browser',
    name: t('dashboard.menu.configuration'),
    children: [
      {
        icon: 'dashboard',
        to: 'configuration-dashboard',
        name: t('dashboard.menu.dashboard'),
        show: storePermissions.hasPermission('view_dashboard')
      },
      {
        icon: 'user-square',
        to: 'configuration-users',
        name: t('dashboard.menu.users'),
        show: storePermissions.hasPermission('view_user')
      },
      {
        icon: 'user-check',
        to: 'configuration-roles',
        name: t('dashboard.menu.role'),
        show: storePermissions.hasPermission('view_group')
      },
      {
        icon: 'key',
        to: 'configuration-rooms',
        name: t('dashboard.menu.configuration_rooms'),
        show: storePermissions.hasPermission('view_room')
      },
      {
        icon: 'type-square',
        to: 'configuration-room-types',
        name: t('dashboard.menu.room_types'),
        show: storePermissions.hasPermission('view_roomtype')
      },
      {
        icon: 'cpu-chip',
        to: 'configuration-controllers',
        name: t('dashboard.menu.controllers'),
        show: storePermissions.hasPermission('view_device')
      },
    ],
    show: true
  },
  {
    icon: 'settings',
    to: 'settings',
    name: t('dashboard.menu.settings'),
    children: [],
    show: storePermissions.hasPermission('view_adminsettings')
  },
  {
    icon: 'log-in',
    to: 'access',
    name: t('dashboard.menu.access'),
    children: [],
    show: true
  },
  {
    icon: 'presentation-chart',
    to: 'backlog',
    name: t('dashboard.menu.backlog'),
    children: [],
    show: true
  }
].filter(el => el.show) as Item[])
</script>