import {defineStore} from "pinia";
import {computed, ref} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";
import useVuelidate from "@vuelidate/core";
import {minLength, required, sameAs} from "@vuelidate/validators";
import {toast} from "vue3-toastify";
import {useI18n} from "vue-i18n";
import {useRouter} from "vue-router";
import router from "@/router";

export const useNewPasswordStore = defineStore('new-password', () => {
    const {t} = useI18n()
    const {push} = useRouter()
    const loading = ref(false)
    const state = ref({
        key: '',
        new_password: '',
        confirm_password: ''
    })

    const rules = computed(() => ({
        new_password: { required, minLength: minLength(8)},
        confirm_password: { required, sameAsPassword: sameAs(computed(() => state.value.new_password))}
    }))

    const v$ = useVuelidate(rules, state, {$scope: false})

    const submit = async () => {
        loading.value = true
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) {
            loading.value = false
            throw new Error('The check is invalid')
        }
        try {
            state.value.key = router.currentRoute.value.query.key as string
            await useApiFetch('/users/reset-password/', {
                method: 'PUT',
                data: state.value
            })
            await push({name: 'login'})
            toast.success(t('toast.password_updated__success') as string);
        }catch (e) {
            throw e
        }finally {
            loading.value = false
        }
    }

    return { state, validation: v$, submit, loading }
})