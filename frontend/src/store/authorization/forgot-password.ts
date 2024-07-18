import {defineStore} from "pinia";
import {computed, ref} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";
import useVuelidate from "@vuelidate/core";
import {email, required } from "@vuelidate/validators";
import {toast} from "vue3-toastify";
import {useI18n} from "vue-i18n";
import {useRouter} from "vue-router";

export const useForgotPasswordStore = defineStore('forgot-password', () => {
    const {t} = useI18n()
    const {push} = useRouter()
    const loading = ref(false)
    const state = ref({
        email: ''
    })

    const rules = computed(() => ({
        email: { required, email },
    }))

    const v$ = useVuelidate(rules, state, {$scope: false})

    const submit = async () => {
        loading.value = true
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) {
            loading.value = false
            throw new Error('The check is invalid')
        }
        await useApiFetch('/users/send-link/', {
            method: 'POST',
            data: state.value
        })
        loading.value = false
        $reset()
        await push({name: 'reset-password'})
        toast.success(t('toast.request_processed_success') as string);
    }

    const $reset = () => {
        state.value = {
            email: "",
        }
        v$.value.$reset()
    }

    return { state, validation: v$, submit, loading }
})