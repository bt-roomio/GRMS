import {defineStore} from "pinia";
import {computed, ref} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";
import {addFieldSelect} from "@utils/transform-response.ts";
import {required} from "@vuelidate/validators";
import useVuelidate from "@vuelidate/core";
import {toast} from "vue3-toastify";
import {useI18n} from "vue-i18n";
import {useConfirm} from "@store/dashboard/useConfirm.ts";

export const useConfigurationRoomTypeStore = defineStore('configuration-room-type', () => {
    const confirmStore = useConfirm()
    const {t} = useI18n()
    const room_types = ref<IServerResponse<IConfigurationRoomTypesData> | null>(null)
    const room_type = ref<IConfigurationRoomTypes | null>(null)
    const loading = ref(false)
    const error = ref({code: null, msg: null})
    const sortedData = ref({})
    const size = ref<number>(10)
    const state = ref<IConfigurationRoomTypes>({
        id: "",
        title: "",
        dashboards: null,
    })

    const rules = computed(() => ({
        title: {required},
    }))

    const v$ = useVuelidate(rules, state.value, {$scope: false})

    const getList = async (params: IConfigurationRoomParams) => {
        error.value.code = null
        error.value.msg = null
        loading.value = true
        try {
            const {data} = await useApiFetch<IServerResponse<IConfigurationRoomTypesData>>('/main/room-type/', {
                method: 'GET',
                params: {
                    ...params, size: size.value
                },
                transformResponse: [(data) => addFieldSelect(data)]
            })

            room_types.value = data as IServerResponse<IConfigurationRoomTypesData>
        }catch (e: any) {
            if (e.response?.status){
                error.value.code = e.response.status
                error.value.msg = e.response.data.detail
                room_types.value = {results: [], count: 0}
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
            await useApiFetch('/main/room-type/', {method: 'POST', data: state.value})
            await getList(sortedData.value)
            callback()
            await $reset()
            toast.success(t('toast.room_type_add_success') as string);
        }catch (e: any) {
            toast.error(e.response.data.detail || t('toast.unknown_error') as string);
            throw e
        }
    }
    const editItem = async (callback: () => void) => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        try {
            await useApiFetch('/main/room-type/' + state.value.id, {method: 'PUT', data: state.value})
            await getList(sortedData.value)
            callback()
            await $reset()
            toast.success(t('toast.room_type_edit_success') as string);
        }catch (e: any) {
            toast.error(e.response.data.detail || t('toast.unknown_error') as string)
            throw e
        }
    }
    const getItem = async (id: string, isFilled: boolean) => {
        try {
            const {data} = await useApiFetch<IConfigurationRoomTypes>('/main/room-type/' + id, {method: 'GET'})
            room_type.value = data
            if (isFilled) {
                state.value.id = data.id
                state.value.title = data.title
            }
        }catch (e: any) {
            throw e
        }
    }
    const deleteItem = async (id: string) => {
        await confirmStore.showConfirm({
            title: t('dashboard.configuration.room_type.confirm.title'),
            content: t('dashboard.configuration.room_type.confirm.subtitle'),
            callback: async (confirmed) => {
                if (confirmed) {
                    try {
                        await useApiFetch('/main/room-type/' + id, {method: 'DELETE'})
                        await getList(sortedData.value)
                        toast.success(t('toast.room_type_delete_success') as string);
                    }catch (e: any) {
                        toast.error(e.response.data.detail || t('toast.unknown_error') as string);
                        throw e
                    }
                }
            }
        })

    }
    const searchItems = async (val: string) => {
        await getList({})
        if (val){
            const results = {
                results: room_types.value?.results.filter(el => (el.title as string)?.toLowerCase().includes(val.toLowerCase())),
                count: room_types.value?.results.filter(el => (el.title as string)?.toLowerCase().includes(val.toLowerCase())).length
            }
            room_types.value = results as IServerResponse<IConfigurationRoomTypesData>
        }
    }
    const $reset = async () => {
        state.value = {
            id: "",
            title: "",
            dashboards: "",
        }
        v$.value.$reset()
    }
    const sortList = async (output: ISortOutput) => {
        sortedData.value = output
        await getList({...output})
    }
    const loadMore = async () => {
        size.value += 10
        await getList(sortedData.value)
    }

    return {
        room_types,
        loading,
        error,
        getList,
        getItem,
        addItem,
        editItem,
        deleteItem,
        searchItems,
        loadMore,
        sortList,
        state,
        validation: v$,
        $reset
    }
})