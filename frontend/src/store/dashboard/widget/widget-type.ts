import {defineStore} from "pinia";
import {ref} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";

export const useWidgetType = defineStore('widget-type', () => {
    const widgetTypes = ref<IServerResponse<IWidgetType>>()
    const widgetType = ref<IWidgetType>()

    const getWidgetTypes = async () => {
        const {data} = await useApiFetch<IServerResponse<IWidgetType>>('/main/widget-type/', {method: 'GET'})
        widgetTypes.value = data
    }
    const getWidgetType = async (id: string) => {
        const {data} = await useApiFetch<IWidgetType>('/main/widget-type/' + id, {method: 'GET'})
        widgetType.value = data
    }

    return {
        widgetTypes,
        getWidgetTypes,
        widgetType,
        getWidgetType
    }
})