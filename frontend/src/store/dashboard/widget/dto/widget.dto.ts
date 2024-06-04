
interface IWidgetSettingValue { i: string, x: number, y:number, w: number, h:number, minH?: number, minW?: number, config?: {[key: string]: unknown} }
interface IWidgetSettingState { widget_name: string, configs?: {[key: string]: unknown} | null }
interface IWidgetSettingParams {
    callback: (confirm: boolean) => void | Promise<void> | null;
}