import {defineStore} from "pinia";
import useApiFetch from "@/composables/useApiFetch.ts";
import {computed, ref} from "vue";
import {addFieldSelectArray} from "@utils/transform-response.ts";
import {email, minLength, required} from "@vuelidate/validators";
import useVuelidate from "@vuelidate/core";
import {toast} from "vue3-toastify";
import {useI18n} from "vue-i18n";
import {useConfirm} from "@store/dashboard/useConfirm.ts";

export const useUserStore = defineStore('user', () => {
    const {t} = useI18n()
    const confirmStore = useConfirm()
    const loading = ref(false)
    const editID = ref<string | null>(null)
    const user = ref<IUser | null>(null)
    const users = ref<IUser[]>([])
    const state = ref({
        email: '',
        phone: '',
        first_name: '',
        last_name: '',
        password: '',
        groups: []
    })
    const rules = computed(() => ({
        email: {
            required,
            minLength: minLength(1),
            email
        },
        phone: {required},
        first_name: {required},
        last_name: {required},
    }))

    const v$ = useVuelidate(rules, state, {$scope: false})
    const getUsers = async () => {
        loading.value = true
        const {data} = await useApiFetch<IUser[]>('/users/users/', {
            method: 'GET',
            transformResponse: [(data) => addFieldSelectArray(data)]
        })
        users.value = data
        loading.value = false
    }
    const getUser = async (id: string, isFilled: boolean = false) => {
        const {data} = await useApiFetch<IUser>('/users/user/' + id, {method: 'GET'})
        if (isFilled) {
            state.value.first_name = data.first_name || ''
            state.value.last_name = data.last_name || ''
            state.value.email = data.email || ''
            state.value.phone = data.phone || ''
        }
        user.value = data
    }
    const addUser = async (callback: () => void) => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        try {
            await useApiFetch<IUser[]>('/users/users/', {method: 'POST', data: state.value})
            await getUsers()
            callback()
            await $reset()
            toast.success(t('toast.user_add_success') as string);
        }catch (e) {
            throw e
        }
    }
    const editUser = async (callback: () => void) => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        try {
            await useApiFetch<IUser[]>('/users/user/' + editID.value, {method: 'PUT', data: state.value})
            await getUsers()
            callback()
            await $reset()
            toast.success(t('toast.user_edit_success') as string);
        }catch (e) {
            throw e
        }
    }
    const deleteUser = async (id: string) => {
        await confirmStore.showConfirm({
            title: t('dashboard.configuration.users.confirm.title'),
            content: t('dashboard.configuration.users.confirm.subtitle'),
            callback: async (confirmed) => {
                if (confirmed) {
                    try {
                        await useApiFetch('/users/user/' + id, {method: 'DELETE'})
                        await getUsers()
                        toast.success(t('toast.user_delete_success') as string);
                    }catch (e: any) {
                        throw e
                    }
                }
            }
        })
    }

    const $reset = async () => {
        state.value = {
            email: "",
            phone: "",
            first_name: "",
            last_name: "",
            password: "",
            groups: []
        }
        editID.value = null
        v$.value.$reset()
    }
    return {users, state, editID, validation: v$, getUsers, getUser, addUser, editUser, deleteUser, $reset }
})