import {defineStore} from "pinia";
import {ref} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";
import {toast} from "vue3-toastify";
import i18nStore from "@/store";

export const useConfigurationRoomsStore = defineStore('configuration-rooms', () => {
    const t = i18nStore()
    const state = ref<IConfigurationRoom>({})
    const getList = async (params: IConfigurationRoomParams) => {
        try {
            const {data} = await useApiFetch<IConfigurationRoom>('/main/room/', {method: 'GET', params})
            console.log(data)
        }catch (e: any) {
            toast.error(e.response.data.detail || t('toast.unknown_error') as string);
        }
    }

    const deleteItem = async (id: string) => {
        try {
            const {data} = await useApiFetch<IConfigurationRoom>('/main/room/' + id, {method: 'DELETE'})
            console.log(data)
        }catch (e: any) {
            toast.error(e.response.data.detail || t('toast.unknown_error') as string);
        }
    }

    const addItem = async () => {
        try {
            const {data} = await useApiFetch<IConfigurationRoom>('/main/room/', {method: 'POST'})
            console.log(data)
        }catch (e: any) {
            toast.error(e.response.data.detail || t('toast.unknown_error') as string);
        }
    }

    return { state, getList, addItem, deleteItem }
})