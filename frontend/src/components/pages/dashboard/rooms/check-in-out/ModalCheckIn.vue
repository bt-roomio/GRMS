<template>
  <Modal ref="modal">
    <template #head>
      <h2>Check In guest</h2>
      <p>for room #242</p>
    </template>
    <form class="ui-form" @submit.prevent>
      <UiInput
          name="check_out_date"
          v-model="state.check_out"
          type="datetime-local"
          label="Checkout date"
          :min="moment().format('YYYY-MM-DDTHH:mm')"
      />
      <UiCheckbox v-model="state.auto_check_out">Auto checkout</UiCheckbox>
      <UiInput
          name="first_name"
          :label="$t('dashboard.configuration.users.form.first_name')"
          :placeholder="$t('dashboard.configuration.users.form.name_placeholder')"
          v-model="state.name"
      />
      <UiInput
          name="last_name"
          :label="$t('dashboard.configuration.users.form.last_name')"
          :placeholder="$t('dashboard.configuration.users.form.name_placeholder')"
          v-model="state.lastname"
      />
      <div class="ui-multiselect">
        <label>Nationality</label>
        <Multiselect
            v-model="state.nationality"
            :options="nationalities.getNames('en')"
            :canClear="false"
            :canDeselect="false"
            :close-on-select="true"
            :searchable="true"
            placeholder="Choose nationality"
        />
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
      <UiButton class="primary" @click.prevent="storeCheckInOut.checkIn(close)">
        {{$t('dashboard.settings.save')}}
      </UiButton>
      <UiButton class="text" @click.prevent="close()">
        {{ $t('dashboard.configuration.rooms.modals.add_new_rooms.cancel') }}
      </UiButton>
    </template>
  </Modal>
</template>
<script setup lang="ts">
import nationalities from 'i18n-nationality'
import en from 'i18n-nationality/langs/en.json'
import Modal from "@components/ui/Modal.vue";
import {ref} from "vue";
import UiInput from "@components/ui/Input.vue";
import {useCheckInOutStore} from "@store/dashboard/check-in-out";
import {storeToRefs} from "pinia";
import UiCheckbox from "@components/ui/Checkbox.vue";
import Multiselect from "@vueform/multiselect";
import UiButton from "@components/ui/Button.vue";
import moment from "moment/moment";
const storeCheckInOut = useCheckInOutStore()
const {state} = storeToRefs(storeCheckInOut)
const modal = ref<IModal | null>(null)
nationalities.registerLocale(en);
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