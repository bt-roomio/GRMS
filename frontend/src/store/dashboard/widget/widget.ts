import {defineStore} from "pinia";
import {ref} from "vue";
import data from "@/components/widgets/data/dashboard.json"


export const useMainWidgetSetting = defineStore('widget-setting', () => {
    const dashboardSettings = ref<IWidgetSettingValue[] | null>(null)
    const isDashboardSettings = ref(false)
    const dashboardSettingsCallback = ref<(confirm: boolean) => void | Promise<void> | null>((confirm) => {console.log(confirm)})
    const dashboardSettingsConfig = ref<IWidgetSettingValue[] | null>(null)
    const sortWidgets = ref(4)
    const state = ref<IWidgetSettingState>({
        device: "",
        device_data_key: "",
        type: "",
        config: {}
    })
    const getMainDashboardSettings = async () => {
        if (!dashboardSettings.value){
            dashboardSettings.value = data.dashboard.widgets
        }
    }
    const setMainDashboardSettings = async () => {
        dashboardSettings.value = JSON.parse(JSON.stringify(dashboardSettingsConfig.value))
        dashboardSettingsConfig.value = null
    }
    const setSettings = async (params: IWidgetSettingParams) => {
        dashboardSettingsConfig.value = JSON.parse(JSON.stringify(dashboardSettings.value))
        isDashboardSettings.value = true
        dashboardSettingsCallback.value = params.callback;
    }
    const handleConfirm = () => {
        isDashboardSettings.value = false
        dashboardSettingsCallback.value(true);
    };
    const handleCancel = () => {
        isDashboardSettings.value = false
        dashboardSettingsCallback.value(false);
    };

    const addItem = async (state: any, callback: () => void) => {
        console.log()
        dashboardSettingsConfig.value?.push(
            {
                i: JSON.stringify(new Date().getMilliseconds()),
                ...state.type.descriptor.config,
                type: state.type.descriptor.type,
                config: state.config,
                device: state.device,
                device_data_key: state.device_data_key
            }
        )
        await $reset()
        callback()
    }

    const getWidgetList = () => {
        return [
            {
                name: "Progress Bar",
                type: 'progress-bar'
            },
        ]
    }

    const editItem = async (value:any) => {
        state.value.device = value.device
        state.value.type = value.type
        state.value.config = value.config
    }

    const $reset = async () => {
        state.value = {
            device: "",
            type: "",
            config: {}
        }
    }
    return {
        dashboardSettings,
        dashboardSettingsConfig,
        isDashboardSettings,
        getMainDashboardSettings,
        setSettings,
        handleConfirm,
        handleCancel,
        setMainDashboardSettings,
        addItem,
        editItem,
        getWidgetList,
        $reset,
        state,
        sortWidgets
    };
})