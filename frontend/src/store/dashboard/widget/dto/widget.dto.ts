
interface IWidgetSettingValue { i: string, x: number, y:number, w: number, h:number, minH?: number, minW?: number }
interface IWidgetSettingParams {
    callback: (confirm: boolean) => void | Promise<void> | null;
}