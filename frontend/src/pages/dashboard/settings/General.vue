<template>
  <div class="card">
    <form class="card__content" @submit.prevent="submit()">
      <div class="card__head">
        <h3>{{ $t('dashboard.settings.general.title') }}</h3>
        <p>{{ $t('dashboard.settings.general.description') }}</p>
      </div>
      <ul class="card__list">
        <li class="card__list-item">
          <div class="item-texts">
            <p class="title">{{ $t('dashboard.settings.general.admin_panel_language.title') }}</p>
            <span class="description">{{ $t('dashboard.settings.general.admin_panel_language.description') }}</span>
          </div>
          <div class="item-actions">
            <ChangeLocale v-model="state.lang"/>
          </div>
        </li>
        <li class="card__list-item">
          <div class="item-texts">
            <p class="title">{{ $t('dashboard.settings.general.controllers_sync.title') }}</p>
          </div>
          <div class="item-actions">
            <UiToggle v-model="state.controllers_sync" />
          </div>
        </li>
        <li class="card__list-item">
          <div class="item-texts">
            <p class="title">{{ $t('dashboard.settings.general.check_in_out.title') }}</p>
          </div>
          <div class="item-actions">
            <UiToggle v-model="state.check_in_out"/>
          </div>
        </li>
        <li class="card__list-item">
          <div class="item-texts">
            <p class="title">{{ $t('dashboard.settings.general.vip_status.title') }}</p>
          </div>
          <div class="item-actions">
            <UiToggle v-model="state.vip_status"/>
          </div>
        </li>
        <li class="card__list-item">
          <div class="item-texts">
            <p class="title">{{ $t('dashboard.settings.general.suite_rooms_controls_sync.title') }}</p>
          </div>
          <div class="item-actions">
            <UiToggle v-model="state.suite_rooms_controls_sync"/>
          </div>
        </li>
        <li class="card__list-item">
          <div class="item-texts">
            <p class="title">{{ $t('dashboard.settings.general.laundry.title') }}</p>
          </div>
          <div class="item-actions">
            <UiToggle v-model="state.laundry"/>
          </div>
        </li>
      </ul>
      <div class="card__buttons inline-block mt-5">
        <UiButton class="primary" @click.prevent="submit()">{{ $t('dashboard.settings.save') }}</UiButton>
      </div>
    </form>
  </div>
</template>
<script setup lang="ts">
import UiButton from "@components/ui/Button.vue";
import UiToggle from "@components/ui/Toggle.vue";
import ChangeLocale from "@components/widgets/ChangeLocale.vue";
import {storeToRefs} from "pinia";
import {onMounted} from "vue";
import {useGeneralSettingStore} from "@store/dashboard/settings/general.ts";
import {useI18n} from "vue-i18n";
import {useCookies} from "@vueuse/integrations/useCookies";
const {locale} = useI18n()
const cookies = useCookies(['locale'])
const generalSettingStore = useGeneralSettingStore()
const {state} = storeToRefs(generalSettingStore)

const submit = async () => {
  try {
    await generalSettingStore.submit()
    locale.value = state.value.lang
    cookies.set('locale', state.value.lang, {path: '/'})
  }catch (e) {
    console.log(e)
  }
}


onMounted(async () => {
  await generalSettingStore.getGeneralSetting()
  locale.value = state.value.lang
  cookies.set('locale', state.value.lang, {path: '/'})
})
</script>