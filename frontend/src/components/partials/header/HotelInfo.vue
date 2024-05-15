<template>
  <UiDropdown>
    <template #trigger>
      <div class="header__hotel">
        <UiIcon name="hotel" filled/>
        {{ currentHotel }}
        <UiIcon name="chevron-down" filled/>
      </div>
    </template>
    <template #content="{close}">
      <ul class="dropdown__menu">
        <li v-for="item in hotels.filter(e => e !== currentHotel)" :key="item" @click="changeHotel(item, close)">
          <UiIcon name="hotel" filled/>
          {{item}}
        </li>
      </ul>
    </template>
  </UiDropdown>

</template>
<script setup lang="ts">
import UiIcon from "../../ui/Icon.vue";
import UiDropdown from "../../ui/Dropdown.vue";
import {ref} from "vue";
const currentHotel = ref('Hilton Larnaca 5* (id 459)')
const hotels = ref([
    'Hilton Larnaca 5* (id 459)',
    'Hilton Antalya-Kemer 5* (id 450)',
    'Hilton Dalaman 5* (id 453)',
    'Hilton Bodrum Isil 5* (id 451)',
])
const changeHotel = (hotel: string, callback: () => void) => {
  currentHotel.value = hotel
  callback()
}
</script>