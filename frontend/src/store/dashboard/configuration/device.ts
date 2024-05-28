import {defineStore} from "pinia";
import {ref} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";

export const useConfigurationDeviceStore = defineStore('configuration-device', () => {
    const devices = ref<IServerResponse<IConfigurationRoomsData> | null>(null)
    const loading = ref(false)

    const getList = async () => {
        loading.value = true
        try {
            const {data} = await useApiFetch<IServerResponse<IConfigurationRoomsData>>('/main/device/', {
                method: 'GET',
            })

            devices.value = data as IServerResponse<IConfigurationRoomsData>
        }catch (e: any) {
            throw e
        }finally {
            loading.value = false
        }
    }


    return {
        devices,
        loading,
        getList,
    }
})