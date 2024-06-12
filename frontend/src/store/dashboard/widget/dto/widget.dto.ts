
interface IWidgetSettingValue {
    [key: string]: any
}
interface IWidgetSettingState { [key: string]: any }
interface IWidgetSettingParams {
    callback: (confirm: boolean) => void | Promise<void> | null;
}
interface IWidgetType {
    name: string,
    deprecated?: boolean,
    fqn?: string,
    descriptor?: {[key: string]: any},
    image?: string,
    description?: string,
    tags?: string,
    external_id?: string
}