import {defineStore} from "pinia";
import {computed, ref} from "vue";
import {required} from "@vuelidate/validators";
import useVuelidate from "@vuelidate/core";
import useApiFetch from "@/composables/useApiFetch.ts";
import {toast} from "vue3-toastify";
import {useCookies} from "@vueuse/integrations/useCookies";
import {useI18n} from "vue-i18n";
const cookies = useCookies(['locale'])
export const useGeneralSettingStore = defineStore('settings-general', () => {
    const {t} = useI18n()

    const state = ref<IGeneralSetting>({
        lang: cookies.get('locale') || 'en',
        timezone: 0,
        controllers_sync: false,
        check_in_out: false,
        vip_status: false,
        suite_rooms_controls_sync: false,
        laundry: false,
        visionline: false,
        opera_integration: false,
        visionline_card_system: false,
        aperio_locks: false,
        door_lock: {
            ving_card: false,
            kaba: false
        },
        auto_checkout: false
    })
    const rules = computed(() => ({
        lang: {required},
    }))

    const v$ = useVuelidate(rules, state, {$scope: false})

    const getGeneralSetting = async () => {
        try {
            const {data} = await useApiFetch<IGeneralSetting>('/main/general-settings/', {method: 'GET'})
            state.value = data
        }catch (e: any) {
            toast.error(e.response.data.detail || t('toast.unknown_error') as string);
        }
    }
    const submit = async () => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        try {
            const {data} = await useApiFetch('/main/general-settings/', {
                method: 'PUT',
                data: state.value
            })
            state.value = data
            toast.success(t('toast.save_success') as string);
            v$.value.$reset()
        }catch (e: any) {
            toast.error(e.response.data.detail || t('toast.unknown_error') as string);
        }
    }

    return { state, getGeneralSetting, validation: v$, submit }
})