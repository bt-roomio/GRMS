<template>
  <Modal ref="modal">
    <template #head>
      <h2>Check In guest</h2>
      <p>for room #242</p>
    </template>
    <form class="ui-form" @submit.prevent>
      <UiInput
          name="check_in_date"
          v-model="state.check_in_date"
          type="date"
          label="Check-in date"
      />
      <UiInput
          name="check_out_date"
          v-model="state.check_out_date"
          type="date"
          label="Checkout date"
      />
      <UiInput
          name="check_out_time"
          v-model="state.check_out_time"
          type="time"
          label="Checkout time"
      />
      <UiCheckbox v-model="state.auto_check_out">Auto checkout</UiCheckbox>
      <UiInput
          name="first_name"
          :label="$t('dashboard.configuration.users.form.first_name')"
          :placeholder="$t('dashboard.configuration.users.form.name_placeholder')"
          v-model="state.first_name"
      />
      <UiInput
          name="last_name"
          :label="$t('dashboard.configuration.users.form.last_name')"
          :placeholder="$t('dashboard.configuration.users.form.name_placeholder')"
          v-model="state.last_name"
      />
      <div class="ui-multiselect">
        <label>Nationality</label>
        <Multiselect
            v-model="state.nationality"
            :value-prop="'demonym'"
            label="demonym"
            :options="nationality"
            :canClear="false"
            :canDeselect="false"
            :close-on-select="true"
            :searchable="true"
            placeholder="Choose nationality"
        >
          <template #option="{option}">
            {{option.demonym}} ({{option.country}})
          </template>
        </Multiselect>
      </div>
      <div class="ui-multiselect">
        <label>Gender</label>
        <Multiselect
            v-model="state.gender"
            :options="['Man', 'Woman', 'Other']"
            :canClear="false"
            :canDeselect="false"
            placeholder="Choose gender"
        />
      </div>
    </form>
    <template #footer="{close}">
      <UiButton class="primary">
        {{$t('dashboard.settings.save')}}
      </UiButton>
      <UiButton class="text" @click.prevent="close()">
        {{ $t('dashboard.configuration.rooms.modals.add_new_rooms.cancel') }}
      </UiButton>
    </template>
  </Modal>
</template>
<script setup lang="ts">
import nationality from './nationalities.json'
import Modal from "@components/ui/Modal.vue";
import {ref} from "vue";
import UiInput from "@components/ui/Input.vue";
import {useCheckInOutStore} from "@store/dashboard/check-in-out";
import {storeToRefs} from "pinia";
import UiCheckbox from "@components/ui/Checkbox.vue";
import Multiselect from "@vueform/multiselect";
import UiButton from "@components/ui/Button.vue";
const storeCheckInOut = useCheckInOutStore()
const {state} = storeToRefs(storeCheckInOut)
const modal = ref<IModal | null>(null)
const close = () => {
  modal.value?.close()
}
const open = () => {
  modal.value?.open()
}
defineExpose({
  close,
  open,
})
</script>