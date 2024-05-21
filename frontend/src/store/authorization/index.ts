import {defineStore} from "pinia";
import {computed, ref} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";
import {useCookies} from "@vueuse/integrations/useCookies";
import {toast} from "vue3-toastify";
import useVuelidate from "@vuelidate/core";
import {email, minLength, required} from "@vuelidate/validators";
import {useRouter} from "vue-router";
import axios from "axios";
import {useI18n} from "vue-i18n";

export const useAuthorizationStore = defineStore('authorization', () => {
    const {t} = useI18n()
    const cookies = useCookies(['access_token', 'refresh_token'])
    const isAuth = computed(() => (!!cookies.get('access_token') || !!cookies.get('refresh_token')))
    const {push} = useRouter()

    const state = ref({
        email: 'admin@gmail.com',
        password: 'password',
        remember_me: true
    })

    const rules = computed(() => ({
        email: {
            required,
            minLength: minLength(1),
            email
        },
        password: {
            required,
            minLength: minLength(8),
        }
    }))

    const v$ = useVuelidate(rules, state.value)
    const login = async (args: IAuthorization) => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return

        try {
            const { data } = await useApiFetch('/users/access-token/', {
                method: 'POST',
                data: args
            })
            await setToken(data, args.remember_me)
            await push({name: 'main'})

            toast.success(t('toast.authorization_success') as string);
        }catch (e: any) {
            toast.error(e.response.data.detail || t('toast.unknown_error') as string);
            throw e
        }
    }
    const refreshToken = async () => {
        try {
            const { data } = await axios('/users/refresh-token/', {
                baseURL: import.meta.env.VITE_API_BASE_URL,
                method: 'POST',
                data: {
                    refresh: cookies.get('refresh_token')
                }
            })
            await setToken(data, true)
        }catch (e: any) {
            await logout()
            throw e
        }

    }
    const logout = async () => {
        await deleteToken()
        await push({name: 'login'})
    }

    const getExpires = () => {
        const now = new Date()
        const access = new Date(now.setHours(now.getHours() + 1))
        const refresh = new Date(now.setDate(now.getDate() + 30))
        return {
            access,
            refresh
        }
    }

    const setToken = async (data: ITokens, isExpires: boolean) => {
        cookies.set('access_token', data['access'], isExpires ? {
            expires: getExpires().access,
            path: '/'
        }: {path: '/'})
        if (data['refresh']){
            cookies.set('refresh_token', data['refresh'], isExpires ? {
                expires: getExpires().refresh,
                path: '/'
            }: {path: '/'})
        }
    }

    const deleteToken = async () => {
        cookies.remove('access_token')
        cookies.remove('refresh_token')
    }

    return { isAuth, login, refreshToken, logout, setToken, deleteToken, state, validation: v$ }
})