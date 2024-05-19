<template>
  <div class="ui-table__container">
    <div class="ui-table__search" v-if="isSearchOpen">
      <UiSelect
          name="name"
          model-key="name"
          v-model="searchType"
          :data="searchTypes"
      />
      <UiInput name="search" :placeholder="$t('dashboard.search')" v-model="searchValue"/>
    </div>
    <table class="ui-table">
      <thead>
      <tr>
        <th
            v-for="(header, i) in headers"
            :key="`${header}${i}`"
            scope="col"
        >
          <slot v-if="$slots['header-' + i]" :name="'header-' + i" :entity="i" />
          <template v-else>
            {{header}}
          </template>
        </th>
      </tr>
      </thead>
      <tbody>
      <tr
          v-for="(entity, index) in data"
          :key="`entity-${index}`"
      >
        <td
            v-for="([key], i) in Object.entries(headers)"
            :key="`${key}-${i}`"
        >
          <slot v-if="$slots[key]" :name="key" :entity="entity" />
          <template v-else>
            {{entity[key] || '-'}}
          </template>
        </td>
      </tr>
      </tbody>
    </table>
  </div>
</template>
<script setup lang="ts" generic="T">
import {defineComponent} from "vue";
import UiInput from "@components/ui/Input.vue";
import UiSelect from "@components/ui/Select.vue";
const searchValue = defineModel('searchValue')
const searchType = defineModel('searchType')
defineComponent({
  name: 'UiTable'
})

defineProps<{
  headers: Record<string, T>
  searchTypes: { [key: string]: unknown; }[]
  isSearchOpen?: boolean
  data: Record<string, T>[]
}>()
</script>