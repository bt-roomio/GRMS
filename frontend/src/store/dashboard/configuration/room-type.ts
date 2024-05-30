import {defineStore} from "pinia";
import {ref} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";

export const useConfigurationRoomTypeStore = defineStore('configuration-room-type', () => {
    const room_types = ref<IServerResponse<IConfigurationRoomTypes> | null>(null)
    const loading = ref(false)

    const getList = async () => {
        loading.value = true
        try {
            const {data} = await useApiFetch<IServerResponse<IConfigurationRoomTypes>>('/main/room-type/', {
                method: 'GET',
            })

            room_types.value = data as IServerResponse<IConfigurationRoomTypes>
        }catch (e: any) {
            throw e
        }finally {
            loading.value = false
        }
    }
    const searchItems = async (val: string) => {
        await getList()
        if (val){
            const results = {
                results: room_types.value?.results.filter(el => (el.title)?.toLowerCase().includes(val.toLowerCase())),
                count: room_types.value?.results.filter(el => (el.title)?.toLowerCase().includes(val.toLowerCase())).length
            }
            room_types.value = results as IServerResponse<IConfigurationRoomTypes>
        }
    }


    return {
        room_types,
        loading,
        getList,
        searchItems,
    }
})