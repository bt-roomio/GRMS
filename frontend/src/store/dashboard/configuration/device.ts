import {defineStore} from "pinia";
import {ref} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";

export const useConfigurationDeviceStore = defineStore('configuration-device', () => {
    const devices = ref<IServerResponse<IConfigurationDevice> | null>(null)
    const loading = ref(false)

    const getList = async () => {
        loading.value = true
        try {
            const {data} = await useApiFetch<IServerResponse<IConfigurationDevice>>('/main/device/', {
                method: 'GET',
            })

            devices.value = data as IServerResponse<IConfigurationDevice>
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
                results: devices.value?.results.filter(el => (el.name)?.toLowerCase().includes(val.toLowerCase())),
                count: devices.value?.results.filter(el => (el.name)?.toLowerCase().includes(val.toLowerCase())).length
            }
            devices.value = results as IServerResponse<IConfigurationDevice>
        }
    }


    return {
        devices,
        loading,
        getList,
        searchItems,
    }
})