<template>
  <div class="ui-table__search" v-if="isSearchOpen">
    <div class="ui-select">
      <Multiselect
          v-model="searchType"
          label="name"
          :value-prop="'key'"
          :options="searchTypes"
          :canClear="false"
      />
    </div>
    <UiSearch v-model="searchValue"/>
  </div>
  <div :class="{pointer}" class="ui-table__container">
    <table v-if="(!error?.code || !error?.msg) && isEmpty" class="ui-table">
      <UiLoader v-if="loading"/>
      <thead>
      <tr>
        <th
            v-for="(header, i) in headers"
            :key="`${header}${i}`"
            scope="col"
        >
          <slot v-if="$slots['header-' + i]" :name="'header-' + i" :entity="header" />
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
          @click.prevent="clickTrHandle(entity)"
      >
        <td
            v-for="([key], i) in Object.entries(headers)"
            :key="`${key}-${i}`"
        >
          <slot v-if="$slots[key]" :name="key" :entity="entity as {[key: string]: any}" />
          <template v-else>
            {{entity[key] || '-'}}
          </template>
        </td>
      </tr>
      </tbody>
    </table>
    <table v-else-if="(!error?.code || !error?.msg) && !isEmpty" class="ui-table">
      <UiLoader v-if="loading"/>
      <tbody>
      <tr>
        <td class="ui-table__error">
          <p class="error-title">{{ $t('dashboard.table.no_data_title') }}</p>
          <p class="error-subtitle">{{ $t('dashboard.table.no_data_subtitle') }}</p>
        </td>
      </tr>
      </tbody>
    </table>
    <table v-else-if="(error?.code || error?.msg) && !isEmpty" class="ui-table">
      <tbody>
      <tr>
        <td class="ui-table__error">
          <p class="error-title">{{ $t('dashboard.table.error') }} {{error.code}}</p>
          <p class="error-subtitle">{{error.msg}}</p>
        </td>
      </tr>
      </tbody>
    </table>
  </div>
  <div class="ui-table__pagination" v-if="isPagination">
    <UiButton class="primary" @click="emits('more')">{{ $t('dashboard.table.load_more') }}</UiButton>
  </div>
</template>
<script setup lang="ts" generic="T">
import {computed, defineComponent, ref} from "vue";
import UiIcon from "@components/ui/Icon.vue";
import UiSearch from "@components/ui/Search.vue";
import UiLoader from "@components/ui/Loader.vue";
import UiButton from "@components/ui/Button.vue";
import Multiselect from "@vueform/multiselect";
const emits = defineEmits(['sorted', 'more', 'click'])
const searchValue = defineModel('searchValue')
const searchType = defineModel<string>('searchType')
const sortObject = ref<string | null>('')
defineComponent({
  name: 'UiTable'
})
const handleSort = (field: string) => {
  if (sortObject.value !== '-' + field){
    sortObject.value = '-' + field
    emits('sorted', {
      sort_by: ['-' + field]
    })
  }else {
    sortObject.value = field
    emits('sorted', {
      sort_by: [field]
    })
  }
}
const props = defineProps<{
  headers: Record<string, T>
  searchTypes?: { [key: string]: unknown | undefined; }[]
  isSearchOpen?: boolean
  sort?: string[]
  data: Record<string, T>[] | undefined
  error?: { code: number | null, msg: string | null}
  loading?: boolean
  isPagination?: boolean
  pointer?: boolean
}>()
const isEmpty = computed(() => !!props.data?.length)

const clickTrHandle = (entity: any) => {
  emits('click', entity)
}
</script>