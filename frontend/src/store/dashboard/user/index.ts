import {defineStore} from "pinia";
import useApiFetch from "@/composables/useApiFetch.ts";
import {computed, ref, watch} from "vue";
import {addFieldSelect} from "@utils/transform-response.ts";
import {email, minLength, required} from "@vuelidate/validators";
import useVuelidate from "@vuelidate/core";
import {toast} from "vue3-toastify";
import {useConfirm} from "@store/dashboard/useConfirm.ts";
import router from "@/router";
import i18n from "@/i18n";

export const useUserStore = defineStore('user', () => {
    const confirmStore = useConfirm()
    // @ts-ignore
    const t = (key: string) => i18n.global.t(key)
    const size = ref<number>(10)
    const profile = ref<IUser | null>(null)
    const user = ref<IUser | null>(null)
    const users = ref<IServerResponse<IUser>>({count: 0, results: []})
    const searchValue = ref('')
    const searchType = ref('first_name')
    const loading = ref(false)
    const error = ref({code: null, msg: null})
    const sortedData = ref({})
    const editID = ref<string | null>(null)
    const state = ref({
        email: '',
        phone: '',
        first_name: '',
        last_name: '',
        password: '',
        groups: [] as IGroup[]
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
    const getUsers = async (params: IParams) => {
        loading.value = true
        error.value.code = null
        error.value.msg = null
        try {
            const {data} = await useApiFetch<IServerResponse<IUser>>('/users/users/', {
                method: 'GET',
                params: {
                    ...params,
                    size: size.value
                },
                transformResponse: [(data) => addFieldSelect(data)]
            })
            users.value = data
        } catch (e: any) {
            if (e.response?.status) {
                error.value.code = e.response.status
                error.value.msg = e.response.data.detail
                users.value = {results: [], count: 0}
            }
            throw e
        } finally {
            loading.value = false
        }
    }
    const sortList = async (output: ISortOutput) => {
        sortedData.value = output
        await getUsers(searchValue.value ? {
            ...output,
            ...router.currentRoute.value.query,
            search_value: searchValue.value,
            search_field: searchType.value
        } : {...output, ...router.currentRoute.value.query})
    }
    const loadMore = async () => {
        size.value += 10
        await getUsers(searchValue.value ? {
            ...sortedData.value,
            ...router.currentRoute.value.query,
            search_value: searchValue.value,
            search_field: searchType.value
        } : {...router.currentRoute.value.query})
    }
    const getUser = async (id: string, isFilled: boolean = false) => {
        const {data} = await useApiFetch<IUser>('/users/user/' + id, {method: 'GET'})
        if (isFilled) {
            state.value.first_name = data.first_name || ''
            state.value.last_name = data.last_name || ''
            state.value.email = data.email || ''
            state.value.phone = data.phone || ''
            state.value.groups = data.groups || []
        }
        user.value = data
    }
    const getProfile = async (id: string) => {
        const {data} = await useApiFetch<IUser>('/users/user/' + id, {method: 'GET'})
        profile.value = data
    }
    const addUser = async (callback: () => void) => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        try {
            const {data} = await useApiFetch<IUser>('/users/users/', {method: 'POST', data: state.value})
            await getUsers(searchValue.value ? {
                ...sortedData.value,
                ...router.currentRoute.value.query,
                search_value: searchValue.value,
                search_field: searchType.value,
            } : {...sortedData.value, ...router.currentRoute.value.query})
            callback()
            await $reset()
            return data
        } catch (e) {
            throw e
        }
    }
    const editUser = async (callback: () => void) => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        try {
            await useApiFetch<IUser[]>('/users/user/' + editID.value, {method: 'PUT', data: state.value})
            await getUsers(searchValue.value ? {
                ...sortedData.value,
                ...router.currentRoute.value.query,
                search_value: searchValue.value,
                search_field: searchType.value,
            } : {...sortedData.value, ...router.currentRoute.value.query})
            callback()
            await $reset()
            toast.success(t('toast.user_edit_success') as string);
        } catch (e) {
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
                        await getUsers(searchValue.value ? {
                            ...sortedData.value,
                            ...router.currentRoute.value.query,
                            search_value: searchValue.value,
                            search_field: searchType.value,
                        } : {...sortedData.value, ...router.currentRoute.value.query})
                        toast.success(t('toast.user_delete_success') as string);
                    } catch (e: any) {
                        throw e
                    }
                }
            }
        })
    }

    const saveUserConfiguration = async (page: string, config: Record<string, any>) => {
        if (profile.value) {
            if (!profile.value.additional_info) {
                profile.value.additional_info = {}
            }
            profile.value.additional_info[page] = config
            await useApiFetch('/users/user/' + profile.value.id, {method: 'PUT', data: {additional_info: profile.value.additional_info}})
        }
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
    watch(searchType, async value => {
        if (searchValue.value) {
            await getUsers({
                ...sortedData.value,
                ...router.currentRoute.value.query,
                search_value: searchValue.value,
                search_field: value,
            })
        }

    })
    watch(searchValue, async value => {
        await getUsers(searchValue.value ? {
            ...sortedData.value,
            ...router.currentRoute.value.query,
            search_value: value,
            search_field: searchType.value,
        } : {...sortedData.value, ...router.currentRoute.value.query})
    })
    return {
        users,
        user,
        profile,
        state,
        editID,
        getUsers,
        getUser,
        getProfile,
        addUser,
        editUser,
        saveUserConfiguration,
        deleteUser,
        size,
        error,
        loading,
        sortList,
        loadMore,
        sortedData,
        searchValue,
        searchType,
        validation: v$,
        $reset
   }
})