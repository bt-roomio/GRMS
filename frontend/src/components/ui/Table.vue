<template>
  <div class="ui-table__container">
    <div class="ui-table__search" v-if="isSearchOpen">
      <UiSelect
          name="name"
          v-model="searchType"
          :data="searchTypes"
      />
      <UiSearch v-model="searchValue"/>
    </div>
    <table v-if="!error?.code || !error?.msg" class="ui-table">
      <UiLoader v-if="loading"/>
      <thead>
      <tr>
        <th
            v-for="(header, i) in headers"
            :key="`${header}${i}`"
            scope="col"
        >
          <slot v-if="$slots['header-' + i]" :name="'header-' + i" :entity="i" />
          <template v-else>
            <template v-if="sort?.includes(i)">
              <span class="sort-th" @click="handleSort(i)">
                {{header}}
                <UiIcon name="arrow-down" class="transition" :class="{'rotate-180': sortObject === '-' + i}" filled/>
              </span>
            </template>
            <template v-else>{{header}}</template>

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
    <table v-else class="ui-table">
      <tbody>
      <tr>
        <td class="ui-table__error ">
          <p class="error-title">Error {{error.code}}</p>
          <p class="error-subtitle">{{error.msg}}</p>
        </td>
      </tr>
      </tbody>
    </table>
  </div>
</template>
<script setup lang="ts" generic="T">
import {defineComponent, ref} from "vue";
import UiSelect from "@components/ui/Select.vue";
import UiIcon from "@components/ui/Icon.vue";
import UiSearch from "@components/ui/Search.vue";
import UiLoader from "@components/ui/Loader.vue";
const emit = defineEmits(['sorted'])
const searchValue = defineModel('searchValue')
const searchType = defineModel<{[key: string]: unknown}>('searchType')
const sortObject = ref<string | null>('')
defineComponent({
  name: 'UiTable'
})
const handleSort = (field: string) => {
  if (sortObject.value !== '-' + field){
    sortObject.value = '-' + field
    emit('sorted', {
      sort_by: ['-' + field]
    })
  }else {
    sortObject.value = field
    emit('sorted', {
      sort_by: [field]
    })
  }
}
defineProps<{
  headers: Record<string, T>
  searchTypes: { [key: string]: unknown; }[]
  isSearchOpen?: boolean
  sort?: string[]
  data: Record<string, T>[]
  error?: { code: number | null, msg: string | null}
  loading?: boolean
}>()

</script>