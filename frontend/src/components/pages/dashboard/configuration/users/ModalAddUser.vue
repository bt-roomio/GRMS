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
<!--    <Tabs class="fill" :list="list" type="hash" v-model="currentTab"/>-->
<!--    <transition name="slide-up" >-->
<!--      <form v-if="currentTab === 'invite'" class="ui-form">-->
<!--        <UiInputSelect-->
<!--            :select-position="'right'"-->
<!--            :select-options="['Admin', 'Editor', 'User']"-->
<!--            name="email_address"-->
<!--            :args="{placeholder: $t('dashboard.configuration.users.form.email_address_placeholder')}"-->
<!--            :label="$t('dashboard.configuration.users.form.email_address')"-->
<!--        ></UiInputSelect>-->
<!--        <h3>{{$t('dashboard.configuration.users.modal.contacts_from')}}</h3>-->
<!--        <div class="ui-form__row items-center col-2-auto hover:bg-gray-50 rounded-lg cursor-pointer">-->
<!--          <UiIcon class="w-10 h-10" name="microsoft-office" filled/>-->
<!--          Microsoft office 365-->
<!--        </div>-->
<!--        <div class="ui-form__row items-center col-2-auto hover:bg-gray-50 rounded-lg cursor-pointer">-->
<!--          <UiIcon class="w-10 h-10" name="gmail" filled/>-->
<!--          Gmail-->
<!--        </div>-->
<!--      </form>-->
      <form class="ui-form">
<!--      <form v-else-if="currentTab === 'add'" class="ui-form">-->
<!--        <UiToggle>Active user</UiToggle>-->
        <UiInput
            name="email"
            :label="$t('dashboard.configuration.users.form.email_address')"
            :placeholder="$t('dashboard.configuration.users.form.email_address_placeholder')"
            v-model="state.email"
            :errors="validation?.$dirty ? validation?.$silentErrors : []"
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
        <UiInput
            name="password"
            :label="$t('dashboard.configuration.users.form.password')"
            :placeholder="$t('dashboard.configuration.users.form.password_placeholder')"
            v-model="state.password"
        >
          <UiButton @click.prevent="generatePassword" class="text">{{ $t('dashboard.configuration.users.form.generate') }}</UiButton>
        </UiInput>
      </form>
<!--    </transition>-->
    <template #footer="{close}">
<!--      <UiButton v-if="currentTab === 'invite'" class="primary" @click.prevent="close()">-->
<!--        {{$t('dashboard.configuration.users.modal.send_invite')}}-->
<!--      </UiButton>-->
      <UiButton class="primary" @click.prevent="storeUser.editUser(close)" v-if="editID">
        {{$t('dashboard.configuration.users.button_save')}}
      </UiButton>
      <UiButton class="primary" @click.prevent="storeUser.addUser(close)" v-else>
        {{$t('dashboard.widget.form.add')}}
      </UiButton>
      <UiButton class="text" @click.prevent="close()">
        {{ $t('dashboard.configuration.rooms.modals.add_new_rooms.cancel') }}
      </UiButton>
    </template>
  </Modal>
</template>
<script setup lang="ts">
import Modal from "@components/ui/Modal.vue";
import UiButton from "@components/ui/Button.vue";
import {onMounted, ref} from "vue";
// import {useI18n} from "vue-i18n";
import UiInput from "@components/ui/Input.vue";
import useMainStore from "@/store";
import {useUserStore} from "@store/dashboard/user";
import {storeToRefs} from "pinia";
const storeMain = useMainStore()
// const {t} = useI18n()
const add_user = ref<IModal | null>(null)
// const currentTab = ref('invite')
const storeUser = useUserStore()
const {state, validation, editID} = storeToRefs(storeUser)

const close = () => {
  add_user.value?.close()
}
const open = () => {
  add_user.value?.open()
}
const generatePassword = () => {
  state.value.password = storeMain.generateRandomString(8)
}

onMounted(async () => {})

// const list = computed(() => [
//   {
//     name: t('dashboard.configuration.users.modal.send_invite'),
//     hash: 'invite'
//   },
//   {
//     name: t('dashboard.configuration.users.button'),
//     hash: 'add'
//   }
// ])


defineExpose({
  close,
  open,
})
</script>