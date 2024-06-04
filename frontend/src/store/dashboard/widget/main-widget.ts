import {defineStore} from "pinia";
import {ref} from "vue";



export const useMainWidgetSetting = defineStore('main-widget-setting', () => {
    const dashboardSettings = ref<IWidgetSettingValue[] | null>(null)
    const isDashboardSettings = ref(false)
    const dashboardSettingsCallback = ref<(confirm: boolean) => void | Promise<void> | null>((confirm) => {console.log(confirm)})
    const dashboardSettingsConfig = ref<IWidgetSettingValue[] | null>(null)
    const sortWidgets = ref(365)
    const state = ref<IWidgetSettingState>({
        widget_name: 'OccupancyRate',
        configs: null,
    })
    const getMainDashboardSettings = async () => {
        if (!dashboardSettings.value){
            dashboardSettings.value = [
                { i: 'OccupancyRate', x: 0, y: 0, w: 6, h: 4 },
                { i: 'RoomAvailability', x: 6, y: 0, w: 6, h: 4 },
            ]
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

    const addItem = async (callback: () => void) => {
        const stepX = 6;
        const stepY = 4;
        const config = {
            x: (((dashboardSettingsConfig.value?.length || 0) + 1) % 3) * stepX,
            y: Math.floor(((dashboardSettingsConfig.value?.length || 0) + 1) / 3) * stepY,
            w: 6,
            h: 4,
        }
        dashboardSettingsConfig.value?.push({ i: state.value.widget_name, ...config, config: state.value?.configs || {} })
        callback()
    }

    const getWidget = () => {
        return [
            {name: 'OccupancyRate'},
            {name: 'RoomAvailability'},
            {
                name: 'Percent',
                configs: {
                    title: 'Percent',
                    value: '20'
                }
            }
        ]
    }

    const editItem = async () => {

    }

    const $reset = async () => {
        state.value.widget_name = 'OccupancyRate'
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
        getWidget,
        $reset,
        state,
        sortWidgets
    };
})