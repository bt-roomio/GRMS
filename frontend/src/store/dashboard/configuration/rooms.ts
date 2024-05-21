import {defineStore} from "pinia";
import {computed, ref, watch} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";
import {toast} from "vue3-toastify";
import {addFieldSelect} from "@utils/transform-response.ts";
import {useI18n} from "vue-i18n";
import {AxiosError} from "axios";
import {required} from "@vuelidate/validators";
import useVuelidate from "@vuelidate/core";

export const useConfigurationRoomsStore = defineStore('configuration-rooms', () => {
    const {t} = useI18n()
    const room = ref<IConfigurationRoom>()
    const rooms = ref<IServerResponse | null>(null)
    const searchValue = ref('')
    const searchType = ref({
        name: t('dashboard.configuration.rooms.room'),
        key: 'room_number'
    })
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
        device: "",
    })

    const rules = computed(() => ({
        room_number: {required},
        floor: {required},
        block: {required},
    }))

    const v$ = useVuelidate(rules, state.value, {$scope: false})

    const getList = async (params: IConfigurationRoomParams) => {
        loading.value = true
        error.value.code = null
        error.value.msg = null
        try {
            const {data} = await useApiFetch<IConfigurationRoomResponse>('/main/room/', {
                method: 'GET',
                params,
                transformResponse: [(data) => addFieldSelect(data)]
            })

            rooms.value = data as IServerResponse
        }catch (e: any) {
            if ((e as AxiosError).name === "AxiosError"){
                error.value.code = e.response.status
                error.value.msg = e.response.data.detail
                rooms.value = {results: [], count: 0}
            }
        }finally {
            loading.value = false
        }
    }
    const sortList = async (output: ISortOutput) => {
        sortedData.value = output
        await getList(searchValue.value ? {
            ...output,
            search_value: searchValue.value,
            search_field: searchType.value.key
        } : {...output})
    }
    const getItem = async (id: string, isFilled: boolean) => {
        itemLoading.value = true
        itemError.value.code = null
        itemError.value.msg = null
        try {
            const {data} = await useApiFetch<IConfigurationRoom>('/main/room/' + id, {method: 'GET'})
            room.value = data
            if (isFilled) {
                state.value.id = data.id
                state.value.type = data.type
                state.value.room_number = data.room_number
                state.value.floor = data.floor
                state.value.block = data.block
                state.value.device = data.device
            }
        }catch (e: any) {
            if ((e as AxiosError).name === "AxiosError"){
                itemError.value.code = e.response.status
                itemError.value.msg = e.response.data.detail
            }
        }finally {
            itemLoading.value = false
        }
    }
    const addItem = async (callback: () => void) => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        try {
            await useApiFetch<IConfigurationRoom>('/main/room/', {method: 'POST', data: state.value})
            await getList(searchValue.value ? {
                ...sortedData.value,
                search_value: searchValue.value,
                search_field: searchType.value.key,
            }: {...sortedData.value})
            callback()
            await $reset()
            toast.success(t('toast.room_add_success') as string);
        }catch (e: any) {
            toast.error(e.response.data.detail || t('toast.unknown_error') as string);
        }
    }
    const editItem = async (callback: () => void) => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        try {
            await useApiFetch<IConfigurationRoom>('/main/room/' + state.value.id, {method: 'PUT', data: state.value})
            await getList(searchValue.value ? {
                ...sortedData.value,
                search_value: searchValue.value,
                search_field: searchType.value.key,
            }: {...sortedData.value})
            callback()
            await $reset()
            toast.success(t('toast.room_edit_success') as string);
        }catch (e: any) {
            toast.error(e.response.data.detail || t('toast.unknown_error') as string);
        }
    }
    const deleteItem = async (id: string) => {
        try {
            await useApiFetch<IConfigurationRoom>('/main/room/' + id, {method: 'DELETE'})
            await getList(searchValue.value ? {
                ...sortedData.value,
                search_value: searchValue.value,
                search_field: searchType.value.key,
            }: {...sortedData.value})
            toast.success(t('toast.room_delete_success') as string);
        }catch (e: any) {
            toast.error(e.response.data.detail || t('toast.unknown_error') as string);
        }
    }

    const $reset = async () => {
        state.value = {
            id: null,
            type: "",
            room_number: null,
            floor: "",
            block: "",
            device: "",
        }
        v$.value.$reset()
    }
    watch(searchType, async value => {
        if (searchValue.value) {
            await getList({
                ...sortedData.value,
                search_value: searchValue.value,
                search_field: value,
            })
        }

    })
    watch(searchValue, async value => {
        await getList(searchValue.value ? {
            ...sortedData.value,
            search_value: value,
            search_field: searchType.value.key,
        }: {...sortedData.value})
    })

    return {
        state,
        rooms,
        getList,
        addItem,
        deleteItem,
        getItem,
        editItem,
        error,
        loading,
        sortList,
        sortedData,
        searchValue,
        searchType,
        validation: v$,
        $reset
    }
})