import {defineStore} from "pinia";
import {ref} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";
import devicesAttrsJson from "@components/widgets/data/devices-attrs.json";

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
    const setDeviceAttrs = async () => {
        devicesAttrsJson.map(async e => {
            await useApiFetch(e[0] as string, {method: 'POST', data: e[1]})
        })
    }
    const setAttr = async (deviceId: string, scope: string, args: any) => {
        try {
            await useApiFetch(`/shuttle/attributes/${deviceId}/${scope}/`, {method: 'POST', data: args})
        }catch (e) {
            throw e
        }
    }

    return {
        devices,
        loading,
        getList,
        searchItems,
        setDeviceAttrs,
        setAttr
    }
})