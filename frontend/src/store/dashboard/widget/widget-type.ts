import {defineStore} from "pinia";
import {ref} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";
import widgetTypesJson from "@/components/widgets/data/widget-types.json"
export const useWidgetType = defineStore('widget-type', () => {
    const widgetTypes = ref<IServerResponse<IWidgetType>>()
    const widgetType = ref<IWidgetType>()

    const getWidgetTypes = async () => {
        const {data} = await useApiFetch<IServerResponse<IWidgetType>>('/main/widget-type/', {method: 'GET'})
        widgetTypes.value = data
    }
    const getWidgetType = async (id: string) => {
        const {data} = await useApiFetch<IWidgetType>(`/main/widget-type/${id}/`, {method: 'GET'})
        widgetType.value = data
    }
    const setWidgetTypes = async () => {
        widgetTypesJson.map(async e => {
            await useApiFetch<IWidgetType>('/main/widget-type/', {method: 'POST', data: e})
        })
    }
    const deleteWidgetTypes = async () => {
        widgetTypes.value?.results.map(async e => {
            await useApiFetch<IWidgetType>(`/main/widget-type/${e.id}/`, {method: 'DELETE'})
        })
    }

    return {
        deleteWidgetTypes,
        setWidgetTypes,
        widgetTypes,
        getWidgetTypes,
        widgetType,
        getWidgetType
    }
})