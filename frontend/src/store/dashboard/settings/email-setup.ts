import {defineStore} from "pinia";
import {computed, ref} from "vue";
import {email, minLength, required} from "@vuelidate/validators";
import useVuelidate from "@vuelidate/core";
import useApiFetch from "@/composables/useApiFetch.ts";
import {toast} from "vue3-toastify";
import i18nStore from "@/store";

export const useEmailSetupStore = defineStore('settings-email-setup', () => {
    const t = i18nStore()

    const state = ref<IEmailSetup>({
        tenant: "",
        email: "",
        host: "",
        username: "",
        password: "",
        port: "",
        use_tls: true
    })
    const rules = computed(() => ({
        email: {
            required,
            minLength: minLength(1),
            email
        },
        host: {required},
        username: {required},
        password: {required},
        port: {required},
    }))

    const v$ = useVuelidate(rules, state, {$scope: false})

    const getEmailSetup = async () => {
        try {
            const {data} = await useApiFetch<IEmailSetup>('/main/email-config/', {method: 'GET'})
            state.value = data
        }catch (e: any) {
            toast.error(e.response.data.detail || t('toast.unknown_error') as string);
        }
    }
    const submit = async () => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        try {
            const {data} = await useApiFetch('/main/email-config/', {
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

    return { state, getEmailSetup, validation: v$, submit }
})