import {defineStore} from "pinia";
import {ref} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";

export const useConfigurationRoomTypeStore = defineStore('configuration-room-type', () => {
    const room_types = ref<IServerResponse<IConfigurationRoomsData> | null>(null)
    const loading = ref(false)

    const getList = async () => {
        loading.value = true
        try {
            const {data} = await useApiFetch<IServerResponse<IConfigurationRoomsData>>('/main/room-type/', {
                method: 'GET',
            })

            room_types.value = data as IServerResponse<IConfigurationRoomsData>
        }catch (e: any) {
            throw e
        }finally {
            loading.value = false
        }
    }


    return {
        room_types,
        loading,
        getList,
    }
})