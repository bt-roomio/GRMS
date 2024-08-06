import {defineStore} from "pinia";
import {computed, ref, watch} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";
import {toast} from "vue3-toastify";
import {addFieldSelect} from "@utils/transform-response.ts";
import {useI18n} from "vue-i18n";
import {required} from "@vuelidate/validators";
import useVuelidate from "@vuelidate/core";
import {useConfirm} from "@store/dashboard/useConfirm.ts";
import router from "@/router";

export const useConfigurationRoomsStore = defineStore('configuration-rooms', () => {
    const confirmStore = useConfirm()
    const {t} = useI18n()
    const size = ref<number>(10)
    const room = ref<IConfigurationRoom | null>(null)
    const rooms = ref<IServerResponse<IConfigurationRoom>>({results: [], count: 0})
    const searchValue = ref('')
    const searchType = ref('room_number')
    const itemLoading = ref(false)
    const itemError = ref({code: null, msg: null})
    const loading = ref(false)
    const error = ref({code: null, msg: null})
    const sortedData = ref({})
    const state = ref<IConfigurationRoom>({
        id: '',
        type: "",
        room_number: null,
        floor: "",
        block: "",
        devices: [],
    })

    const rules = computed(() => ({
        type: {required},
        room_number: {required},
        floor: {required},
        block: {required},
    }))

    const v$ = useVuelidate(rules, state, {$scope: false})

    const getList = async (params: IConfigurationRoomParams) => {
        loading.value = true
        error.value.code = null
        error.value.msg = null
        try {
            const {data} = await useApiFetch<IServerResponse<IConfigurationRoom>>('/main/room/', {
                method: 'GET',
                params: {
                    ...params,
                    size: size.value
                },
                transformResponse: [(data) => addFieldSelect(data)]
            })

            rooms.value = data
        }catch (e: any) {
            if (e.response?.status){
                error.value.code = e.response.status
                error.value.msg = e.response.data.detail
                rooms.value = {results: [], count: 0}
            }
            throw e
        }finally {
            loading.value = false
        }
    }
    const sortList = async (output: ISortOutput) => {
        sortedData.value = output
        await getList(searchValue.value ? {
            ...output,
            ...router.currentRoute.value.query,
            search_value: searchValue.value,
            search_field: searchType.value
        } : {...output, ...router.currentRoute.value.query})
    }
    const loadMore = async () => {
        size.value += 10
        await getList(searchValue.value ? {
            ...sortedData.value,
            ...router.currentRoute.value.query,
            search_value: searchValue.value,
            search_field: searchType.value
        } : {...router.currentRoute.value.query})
    }
    const getItem = async (id: string, isFilled: boolean) => {
        itemLoading.value = true
        itemError.value.code = null
        itemError.value.msg = null
        try {
            const {data} = await useApiFetch<IConfigurationRoom>(`/main/room/${id}/`, {method: 'GET'})
            room.value = data
            if (isFilled) {
                state.value.id = data.id
                state.value.type = data.type
                state.value.room_number = data.room_number
                state.value.floor = data.floor
                state.value.block = data.block
                state.value.devices = data.devices.map((el: any) => el.id)
            }
        }catch (e: any) {
            if (e.response?.status){
                itemError.value.code = e.response.status
                itemError.value.msg = e.response.data.detail
            }
            throw e
        }finally {
            itemLoading.value = false
        }
    }
    const addItem = async (callback: () => void) => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        let obj = JSON.parse(JSON.stringify(state.value))
        try {
            await useApiFetch<IConfigurationRoom>('/main/room/', {method: 'POST', data: obj})
            await getList(searchValue.value ? {
                ...sortedData.value,
                ...router.currentRoute.value.query,
                search_value: searchValue.value,
                search_field: searchType.value,
            }: {...sortedData.value,...router.currentRoute.value.query})
            callback()
            await $reset()
            toast.success(t('toast.room_add_success') as string);
        }catch (e: any) {
            for (const eKey in e.response.data) {
                toast.error(e.response.data[eKey] || t('toast.unknown_error') as string);
            }
            throw e
        }
    }
    const editItem = async (callback: () => void) => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        let obj = JSON.parse(JSON.stringify(state.value))
        try {
            await useApiFetch<IConfigurationRoom>(`/main/room/${obj.id}/`, {method: 'PUT', data: obj})
            await getList(searchValue.value ? {
                ...sortedData.value,
                ...router.currentRoute.value.query,
                search_value: searchValue.value,
                search_field: searchType.value,
            }: {...sortedData.value, ...router.currentRoute.value.query})
            callback()
            await $reset()
            toast.success(t('toast.room_edit_success') as string);
        }catch (e: any) {
            for (const eKey in e.response.data) {
                toast.error(e.response.data[eKey] || t('toast.unknown_error') as string);
            }
            throw e
        }
    }
    const deleteItem = async (id: string) => {
        await confirmStore.showConfirm({
            title: t('dashboard.configuration.rooms.confirm.title'),
            content: t('dashboard.configuration.rooms.confirm.subtitle'),
            callback: async (confirmed) => {
                if (confirmed) {
                    try {
                        await useApiFetch<IConfigurationRoom>(`/main/room/${id}/`, {method: 'DELETE'})
                        await getList(searchValue.value ? {
                            ...sortedData.value,
                            ...router.currentRoute.value.query,
                            search_value: searchValue.value,
                            search_field: searchType.value,
                        }: {...sortedData.value, ...router.currentRoute.value.query})
                        toast.success(t('toast.room_delete_success') as string);
                    }catch (e: any) {
                        toast.error(e.response.data.detail || t('toast.unknown_error') as string);
                        throw e
                    }
                }
            }
        })

    }
    const $reset = async () => {
        state.value = {
            id: null,
            type: "",
            room_number: null,
            floor: "",
            block: "",
            devices: [],
        }
        v$.value.$reset()
    }
    const $resetData = async () => {
        size.value = 10
        room.value = null
        rooms.value = {results: [], count: 0}
        searchValue.value = ''
        searchType.value = 'room_number'
        itemError.value = {code: null, msg: null}
        error.value = {code: null, msg: null}
        sortedData.value = {}
    }
    watch(searchType, async value => {
        if (searchValue.value) {
            await getList({
                ...sortedData.value,
                ...router.currentRoute.value.query,
                search_value: searchValue.value,
                search_field: value,
            })
        }

    })
    watch(searchValue, async value => {
        await getList(searchValue.value ? {
            ...sortedData.value,
            ...router.currentRoute.value.query,
            search_value: value,
            search_field: searchType.value,
        }: {...sortedData.value, ...router.currentRoute.value.query})
    })
    return {
        state,
        rooms,
        room,
        itemLoading,
        getList,
        addItem,
        deleteItem,
        getItem,
        editItem,
        size,
        error,
        loading,
        sortList,
        loadMore,
        sortedData,
        searchValue,
        searchType,
        validation: v$,
        $reset,
        $resetData
    }
})