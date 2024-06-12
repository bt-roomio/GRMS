import {defineStore} from "pinia";
import {ref} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";
import {toast} from "vue3-toastify";
import {useI18n} from "vue-i18n";
export const useAlarmStore = defineStore('settings-alarm', () => {
    const {t} = useI18n()
    const state = ref<IAlarm>({
        bathroom_enable: false,
        humidity_enable: false,
    })
    const getAlarm = async () => {
        const {data} = await useApiFetch<IAlarm>('/main/alarm-settings/', {method: 'GET'})
        state.value = data
    }
    const submit = async () => {
        const {data} = await useApiFetch('/main/alarm-settings/', {
            method: 'PUT',
            data: state.value
        })
        state.value = data
        toast.success(t('toast.save_success') as string);
    }

    return { state, getAlarm, submit }
})