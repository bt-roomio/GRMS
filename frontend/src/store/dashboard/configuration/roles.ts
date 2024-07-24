import {defineStore} from "pinia";
import {computed, ref} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";
import {addFieldSelectArray} from "@utils/transform-response.ts";
import {required} from "@vuelidate/validators";
import useVuelidate from "@vuelidate/core";
import {toast} from "vue3-toastify";
import {useI18n} from "vue-i18n";
import {useConfirm} from "@store/dashboard/useConfirm.ts";

export const useConfigurationRolesStore = defineStore('configuration-roles', () => {
    const confirmStore = useConfirm()
    const {t} = useI18n()
    const permissions = ref<IConfigurationPermissions[]>([])
    const roles = ref<IConfigurationRole[]>([])
    const role = ref<IConfigurationRole | null>(null)
    const loading = ref(false)
    const error = ref({code: null, msg: null})
    const editID = ref<string | null>(null)
    const state = ref<IConfigurationRole>({
        name: "",
        permissions: [],
    })

    const rules = computed(() => ({
        name: {required},
        permissions: {required},
    }))

    const v$ = useVuelidate(rules, state, {$scope: false})

    const getList = async (params: IConfigurationRoomParams) => {
        error.value.code = null
        error.value.msg = null
        loading.value = true
        try {
            const {data} = await useApiFetch<IConfigurationRole[]>('/users/groups/', {
                method: 'GET',
                params: {
                    ...params
                },
                transformResponse: [(data) => addFieldSelectArray(data)]
            })

            roles.value = data
        }catch (e: any) {
            if (e.response?.status){
                error.value.code = e.response.status
                error.value.msg = e.response.data.detail
                roles.value = []
            }
            throw e
        }finally {
            loading.value = false
        }
    }
    const addItem = async (callback: () => void) => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        try {
            await useApiFetch('/users/groups/', {method: 'POST', data: state.value})
            await getList({})
            callback()
            await $reset()
            toast.success(t('toast.role_add_success') as string);
        }catch (e: any) {
            throw e
        }
    }
    const editItem = async (callback: () => void) => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        try {
            await useApiFetch('/users/group/' + editID.value, {method: 'PUT', data: state.value})
            await getList({})
            callback()
            await $reset()
            toast.success(t('toast.role_edit_success') as string);
        }catch (e: any) {
            throw e
        }
    }
    const getItem = async (id: string, isFilled: boolean) => {
        try {
            const {data} = await useApiFetch<IConfigurationRole>('/users/group/' + id, {method: 'GET'})
            role.value = data
            if (isFilled) {
                state.value.name = data.name
                state.value.permissions = data.permissions || []
            }
        }catch (e: any) {
            throw e
        }
    }
    const getPermissions = async () => {
        try {
            const {data} = await useApiFetch<IConfigurationPermissions[]>('/users/permissions/', {method: 'GET'})
            permissions.value = data
        }catch (e: any) {
            throw e
        }
    }
    const deleteItem = async (id: string) => {
        await confirmStore.showConfirm({
            title: t('dashboard.configuration.roles.confirm.title'),
            content: t('dashboard.configuration.roles.confirm.subtitle'),
            callback: async (confirmed) => {
                if (confirmed) {
                    try {
                        await useApiFetch('/users/group/' + id, {method: 'DELETE'})
                        await getList({})
                        toast.success(t('toast.role_delete_success') as string);
                    }catch (e: any) {
                        throw e
                    }
                }
            }
        })

    }

    const $reset = async () => {
        state.value = {
            name: "",
            permissions: [],
        }
        editID.value = null
        v$.value.$reset()
    }
    const loadMore = async () => {
        await getList({})
    }

    return {
        roles,
        role,
        editID,
        loading,
        error,
        getList,
        getItem,
        addItem,
        editItem,
        deleteItem,
        loadMore,
        state,
        validation: v$,
        getPermissions,
        permissions,
        $reset
    }
})