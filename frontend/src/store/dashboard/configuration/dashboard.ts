import {defineStore} from "pinia";
import {computed, DefineComponent, ref, shallowRef} from "vue";
import useApiFetch from "@/composables/useApiFetch.ts";
import {addFieldSelect} from "@utils/transform-response.ts";
import {required} from "@vuelidate/validators";
import useVuelidate from "@vuelidate/core";
import {toast} from "vue3-toastify";
import {useI18n} from "vue-i18n";
import {useConfirm} from "@store/dashboard/useConfirm.ts";
import {Layout} from "grid-layout-plus";
import useMainStore from "@/store";

export const useConfigurationDashboardStore = defineStore('configuration-dashboard', () => {

    const mainStore = useMainStore()
    const confirmStore = useConfirm()
    const {t} = useI18n()

    // Dashboard Layouts

    const editModel = ref<Layout | null>(null)
    const readModel = ref<Layout | null>(null)
    const viewModel = ref<Layout | null>(null)

    // Dashboard widgets data

    const editWidgets = ref<IWidgetType[] | null>(null)
    const readWidgets = ref<IWidgetType[] | null>(null)
    const viewWidgets = ref<IWidgetType[] | null>(null)

    // Dashboard widgets data

    const editWidget = ref<IWidgetType | null>(null)
    const readWidget = ref<IWidgetType | null>(null)

    // Dashboard state

    const dashboards = ref<IServerResponse<IConfigurationDashboard> | null>(null)
    const dashboard = ref<IConfigurationDashboard | null>(null)

    // Dashboard helpers

    const loading = ref(false)
    const isSettings = ref(false)
    const dashboardSettingsCallback = ref<(confirm: boolean) => void | Promise<void> | null>((confirm) => {console.log(confirm)})
    const error = ref({code: null, msg: null})
    const sortedData = ref({})
    const size = ref<number>(10)

    // Widget helpers

    const isEdit = ref(false)
    const widgetCallback = ref<(confirm: boolean) => void | Promise<void> | null>((confirm) => {console.log(confirm)})
    const selectedComponent = shallowRef<DefineComponent | null>(null)

    // Dashboard state for create

    const state = ref<IConfigurationDashboard>({
        id: "",
        title: "",
        configuration: {},
    })

    const rules = computed(() => ({
        title: {required},
    }))

    const v$ = useVuelidate(rules, state, {$scope: false})
    const getList = async (params: IConfigurationRoomParams) => {
        error.value.code = null
        error.value.msg = null
        loading.value = true
        try {
            const {data} = await useApiFetch<IServerResponse<IConfigurationDashboard>>('/main/dashboard/', {
                method: 'GET',
                params: {
                    ...params, size: size.value
                },
                transformResponse: [(data) => addFieldSelect(data)]
            })

            dashboards.value = data
        }catch (e: any) {
            if (e.response?.status){
                error.value.code = e.response.status
                error.value.msg = e.response.data.detail
                dashboards.value = {results: [], count: 0}
            }
            throw e
        }finally {
            loading.value = false
        }
    }
    const addItem = async (callback: () => void) => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        try {
            await useApiFetch('/main/dashboard/', {method: 'POST', data: state.value})
            await getList(sortedData.value)
            callback()
            await $reset()
            toast.success(t('toast.dashboard_add_success') as string);
        }catch (e: any) {
            throw e
        }
    }
    const editItem = async (callback: () => void) => {
        const isFormCorrect = await v$.value.$validate()
        if (!isFormCorrect) return
        try {
            await useApiFetch('/main/dashboard/' + state.value.id, {method: 'PUT', data: state.value})
            await getList(sortedData.value)
            callback()
            toast.success(t('toast.dashboard_edit_success') as string);
            await $reset()
        }catch (e: any) {
            throw e
        }
    }
    const getItem = async (id: string, isFilled: boolean) => {
        try {
            const {data} = await useApiFetch<IConfigurationDashboard>(`/main/dashboard/${id}`, {method: 'GET'})
            dashboard.value = data
            if (isFilled) {
                state.value.id = data.id
                state.value.title = data.title
                state.value.configuration = data.configuration
            }
        }catch (e: any) {
            throw e
        }
    }
    const deleteItem = async (id: string) => {
        await confirmStore.showConfirm({
            title: t('dashboard.configuration.room_type.confirm.title'),
            content: t('dashboard.configuration.room_type.confirm.subtitle'),
            callback: async (confirmed) => {
                if (confirmed) {
                    try {
                        await useApiFetch('/main/dashboard/' + id, {method: 'DELETE'})
                        await getList(sortedData.value)
                        toast.success(t('toast.dashboard_delete_success') as string);
                    }catch (e: any) {
                        throw e
                    }
                }
            }
        })
    }
    const copyItem = async (item: any) => {
        try {
            const stateObj = JSON.parse(JSON.stringify(item))
            stateObj.title = stateObj.title + ` (Copy)`
            await useApiFetch('/main/dashboard/', {method: 'POST', data: stateObj})
            await getList(sortedData.value)
        }catch (e) {
            throw e
        }
    }
    const searchItems = async (val: string) => {
        await getList({})
        if (val){
            const results = {
                results: dashboards.value?.results.filter(el => (el.title as string)?.toLowerCase().includes(val.toLowerCase())),
                count: dashboards.value?.results.filter(el => (el.title as string)?.toLowerCase().includes(val.toLowerCase())).length
            }
            dashboards.value = results as IServerResponse<IConfigurationDashboard>
        }
    }
    const $reset = async () => {
        editModel.value = null
        readModel.value = null
        viewModel.value = null
        editWidgets.value = null
        readWidgets.value = null
        viewWidgets.value = null
        editWidget.value = null
        readWidget.value = null
        dashboards.value = null
        dashboard.value = null
        loading.value = false
        isSettings.value = false
        state.value = {
            id: "",
            title: "",
            configuration: {},
        }
        v$.value.$reset()
    }
    const sortList = async (output: ISortOutput) => {
        sortedData.value = output
        await getList({...output})
    }
    const loadMore = async () => {
        size.value += 10
        await getList(sortedData.value)
    }
    // Dashboard Inner helpers

    const getDashboardInnerHelpers = async () => {
        try {
            if (dashboard.value && !dashboard.value?.configuration?.widgets){
                dashboard.value.configuration = {widgets: []}
            }
            readModel.value = dashboard.value?.configuration.widgets.map((el: any) => {
                return {
                    ...el.descriptor.dashboard_config,
                    id: el.id,
                    i: mainStore.generateRandomString(12),
                }
            })
            readWidgets.value = dashboard.value?.configuration.widgets
            viewModel.value = readModel.value
            viewWidgets.value = readWidgets.value
        }catch (e: any) {
            throw e
        }
    }
    const setSettings = async (params: IWidgetSettingParams) => {
        editModel.value = JSON.parse(JSON.stringify(readModel.value))
        editWidgets.value = JSON.parse(JSON.stringify(readWidgets.value))
        viewModel.value = editModel.value
        viewWidgets.value = editWidgets.value
        isSettings.value = true
        dashboardSettingsCallback.value = params.callback;
    }
    const handleConfirm = () => {
        isSettings.value = false
        dashboardSettingsCallback.value(true);
    };
    const handleCancel = () => {
        isSettings.value = false
        dashboardSettingsCallback.value(false);
    };
    const addWidget = (obj: any, params: any) => {
        if (params.isEdit){
            editModel.value?.splice(params.key, 1, {
                id: obj.id,
                i: obj.id + editModel.value.length,
                ...obj.descriptor.dashboard_config
            })
            editWidgets.value?.splice(params.key, 1, obj)
        }else {
            editModel.value?.push({
                id: obj.id,
                i: obj.id + editModel.value.length,
                ...obj.descriptor.dashboard_config
            })
            return editWidgets.value?.push(obj)
        }
    }
    const setEditWidget = async (item: IWidgetType, params: IWidgetSettingParams) => {
        editWidget.value = item
        readWidget.value = JSON.parse(JSON.stringify(item))
        isEdit.value = true
        widgetCallback.value = params.callback;
        await checkComponentType(item)
    }
    const clearEditWidget = () => {
        editWidget.value = null
        readWidget.value = null
    }
    const deleteWidget = (key: number) => {
        editModel.value?.splice(key, 1)
        editWidgets.value?.splice(key, 1)
    }
    const saveWidget = (key: number) => {
        if (editModel.value && editModel.value[key]){
            const element = document.querySelector('.widget-card.isEdit')
            if (element){
                editModel.value[key].h = Math.ceil((element.scrollHeight + 16) / 20)
            }
        }
        editWidgets.value?.splice(key, 1, JSON.parse(JSON.stringify({...editWidget.value, updatedAt: (new Date()).toISOString()})))
    }
    const handleConfirmWidget = () => {
        isEdit.value = false
        selectedComponent.value = null
        widgetCallback.value(true);
    };
    const handleCancelWidget = () => {
        isEdit.value = false
        selectedComponent.value = null
        widgetCallback.value(false);
    };
    const saveDashboard = async () => {
        if (!dashboard.value) return
        const dashboardState = {
            id: dashboard.value.id,
            title: dashboard.value.title,
            configuration: {
                widgets: editWidgets.value?.map((item, key) => {
                  return {
                      ...item,
                      descriptor: {
                          ...item.descriptor,
                          dashboard_config: editModel.value ? editModel.value[key] : null
                      }
                  }
                })
            }
        }
        const {data} = await useApiFetch('/main/dashboard/' + state.value.id, {method: 'PUT', data: dashboardState})
        dashboard.value = data
        await getDashboardInnerHelpers()
    }
    const resetDashboard = async () => {
        editModel.value = null
        editWidgets.value = null
        viewModel.value = readModel.value
        viewWidgets.value = readWidgets.value
    }

    const componentImport = import.meta.glob('../../../components/widgets/settings/**.vue');
    const checkComponentType = async (value: IWidgetType) => {
        const type = value?.descriptor?.config_file
        const importFunction = componentImport[`../../../components/widgets/settings/${type}.vue`];

        if (importFunction) {
            const componentModule = await importFunction() as {default: DefineComponent};
            selectedComponent.value = componentModule.default;
        } else {
            console.error(`Component ../../../components/widgets/settings/${type}.vue not found`);
            selectedComponent.value = null;
        }
    }
    return {
        editModel,
        readModel,
        viewModel,
        editWidgets,
        readWidgets,
        viewWidgets,
        editWidget,
        readWidget,
        dashboards,
        dashboard,
        loading,
        isSettings,
        dashboardSettingsCallback,
        error,
        sortedData,
        size,
        isEdit,
        widgetCallback,
        selectedComponent,
        state,
        validation: v$,
        getList,
        getItem,
        addItem,
        editItem,
        deleteItem,
        copyItem,
        searchItems,
        $reset,
        sortList,
        loadMore,
        getDashboardInnerHelpers,
        setSettings,
        handleConfirm,
        handleCancel,
        addWidget,
        setEditWidget,
        clearEditWidget,
        deleteWidget,
        saveWidget,
        handleConfirmWidget,
        handleCancelWidget,
        saveDashboard,
        resetDashboard,
    }
})