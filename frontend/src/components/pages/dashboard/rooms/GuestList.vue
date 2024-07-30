<template>
  <div class="card guest-list">
    <UiTable :headers="headers" :data="data">
      <template #name="{entity}">
        <div class="flex items-center gap-4">
          <UiIcon class="flex-shrink-0 w-5 h-5 stroke-primary-600" name="user" filled/>
          <div>
            <p class="text-lg font-semibold">{{entity.name}}</p>
            <p class="text-sm font-normal">Birth Date: 2024-07-03</p>
          </div>
        </div>
      </template>
      <template #actions>
        <div class="ui-table__actions col-2">
          <UiButton class="text" @click.prevent="storeCheckInOut.checkOut()">
            <UiIcon name="x-circle" filled @click.prevent/> Check-out
          </UiButton>
        </div>
      </template>
    </UiTable>
  </div>
</template>
<script setup lang="ts">
import UiTable from "@components/ui/Table.vue";
import {computed, ref} from "vue";
import UiButton from "@components/ui/Button.vue";
import UiIcon from "@components/ui/Icon.vue";
import {useCheckInOutStore} from "@store/dashboard/check-in-out";
const storeCheckInOut = useCheckInOutStore()
const headers = computed<IConfigurationRoomsHead>(() => ({
  name: '',
  date: '',
  actions: '',
}))
const data = ref([
  {name: 'Guest name 1', date: '09.07.2024-11.07.2024'},
  {name: 'Guest name 1', date: '09.07.2024-11.07.2024'},
  {name: 'Guest name 1', date: '09.07.2024-11.07.2024'}
])
</script>