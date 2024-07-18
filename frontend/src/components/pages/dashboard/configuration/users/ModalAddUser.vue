<template>
  <Modal ref="add_user"  @closed="storeUser.$reset()">
    <template #head v-if="editID">
      <h2>{{$t('dashboard.configuration.users.modal.edit_user_title')}} </h2>
      <p>{{$t('dashboard.configuration.users.modal.edit_user_subtitle')}}</p>
    </template>
    <template #head>
      <h2>{{$t('dashboard.configuration.users.modal.add_user_title')}} </h2>
      <p>{{$t('dashboard.configuration.users.modal.add_user_subtitle')}}</p>
    </template>
    <form class="ui-form">
      <UiInput
          name="email"
          :label="$t('dashboard.configuration.users.form.email_address')"
          :placeholder="$t('dashboard.configuration.users.form.email_address_placeholder')"
          v-model="state.email"
          :errors="validation?.$dirty ? validation?.$silentErrors : []"
          :disabled="editID"
      />
<!--        <div class="ui-multiselect">-->
<!--          <label>{{ $t('dashboard.configuration.users.form.user_role') }}</label>-->
<!--          <Multiselect-->
<!--              v-model="state.role"-->
<!--              :options="['Admin', 'Editor', 'User']"-->
<!--              :canClear="false"-->
<!--          />-->
<!--        </div>-->
      <UiInput
          name="phone"
          :label="$t('dashboard.configuration.users.form.phone')"
          :placeholder="'+357-XX-XX-XX-XX'"
          v-model="state.phone"
          :errors="validation?.$dirty ? validation?.$silentErrors : []"
      />
      <UiInput
          name="first_name"
          :label="$t('dashboard.configuration.users.form.first_name')"
          :placeholder="$t('dashboard.configuration.users.form.name_placeholder')"
          v-model="state.first_name"
          :errors="validation?.$dirty ? validation?.$silentErrors : []"
      />
      <UiInput
          name="last_name"
          :label="$t('dashboard.configuration.users.form.last_name')"
          :placeholder="$t('dashboard.configuration.users.form.name_placeholder')"
          v-model="state.last_name"
          :errors="validation?.$dirty ? validation?.$silentErrors : []"
      />
      <div class="ui-multiselect" v-if="!editID">
        <label>{{ $t('dashboard.configuration.users.form.activation_method') }}</label>
        <Multiselect
            v-model="invite"
            :options="activation_methods"
            :canClear="false"
            :canDeselect="false"
        />
      </div>
      <div v-if="editID">
        <h3 class="mb-2">Action with user</h3>
        <p @click="resendHandle" class="hover:text-primary-700 cursor-pointer mb-2 font-medium">Resend activation link</p>
        <p @click="displayHandle" class="hover:text-primary-700 cursor-pointer mb-2 font-medium">Demonstrate activation link</p>
        <p class="hover:text-primary-700 cursor-pointer font-medium">Delete user</p>
      </div>
    </form>
    <template #footer="{close}">
      <UiButton class="primary" @click.prevent="storeUser.editUser(close)" v-if="editID">
        {{$t('dashboard.configuration.users.button_save')}}
      </UiButton>
      <UiButton class="primary" @click.prevent="submit" v-else>
        {{$t('dashboard.widget.form.add')}}
      </UiButton>
      <UiButton class="text" @click.prevent="close()">
        {{ $t('dashboard.configuration.rooms.modals.add_new_rooms.cancel') }}
      </UiButton>
    </template>
  </Modal>
  <ModalCopyBox ref="copyBox"/>
</template>
<script setup lang="ts">
import Modal from "@components/ui/Modal.vue";
import UiButton from "@components/ui/Button.vue";
import Multiselect from "@vueform/multiselect";
import {computed, ref} from "vue";
import {useI18n} from "vue-i18n";
import UiInput from "@components/ui/Input.vue";
import {useUserStore} from "@store/dashboard/user";
import {storeToRefs} from "pinia";
import {toast} from "vue3-toastify";
import useApiFetch from "@/composables/useApiFetch.ts";
import ModalCopyBox from "@components/pages/dashboard/configuration/users/ModalCopyBox.vue";
const {t} = useI18n()
const add_user = ref<IModal | null>(null)
const copyBox = ref<IModal | null>(null)
const storeUser = useUserStore()
const {state, validation, editID} = storeToRefs(storeUser)
const role = ref('Admin')
const invite = ref('display')
const activation_methods = computed(() => [
  {label: t('dashboard.configuration.users.form.display_activation_link'), value: 'display'},
  {label: t('dashboard.configuration.users.form.send_activation_mail'), value: 'mail'},
])

const submit = async () =>  {
  const data = await storeUser.addUser(close)
  if (invite.value === 'display'){
    const toastId = toast.loading(t('toast.user_wait_activation_link') as string);
    const {data: activationData} = await useApiFetch(`/users/activation-link/${data?.id}/?send_activation_mail=false`, {method: 'GET'})
    copyBox.value?.open({
      title: `This link is for activating the user ${data?.first_name} ${data?.last_name}`,
      text: activationData
    })
    toast.remove(toastId)
  }else if (invite.value === 'mail') {
    await useApiFetch(`/users/activation-link/${data?.id}/?send_activation_mail=true`, {method: 'GET'})
  }
  toast.success(t('toast.user_add_success') as string);
}
const resendHandle = async () => {
  await useApiFetch(`/users/activation-link/${editID.value}/?send_activation_mail=true`, {method: 'GET'})
  toast.success('Success');
}
const displayHandle = async () => {
  close()
  const toastId = toast.loading(t('toast.user_wait_activation_link') as string);
  try {
    const {data: activationData} = await useApiFetch(`/users/activation-link/${editID.value}/?send_activation_mail=false`, {method: 'GET'})
    copyBox.value?.open({
      title: `This link is for activating the user ${state.value?.first_name} ${state.value?.last_name}`,
      text: activationData
    })
  }catch (e) {
    console.log(e)
  }finally {
    toast.remove(toastId)
  }
}
const close = () => {
  add_user.value?.close()
}
const open = () => {
  add_user.value?.open()
}

defineExpose({
  close,
  open,
})
</script>