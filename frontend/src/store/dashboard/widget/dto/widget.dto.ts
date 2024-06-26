
interface IWidgetSettingValue {
    [key: string]: any
}
interface IWidgetSettingState { [key: string]: any }
interface IWidgetSettingParams {
    callback: (confirm: boolean) => void | Promise<void> | null;
}
interface IWidgetType {
    id?: string,
    name: string,
    deprecated?: boolean,
    fqn?: string,
    descriptor: IDescriptor,
    image?: string,
    description?: string,
    tags?: string,
    external_id?: string,
    [key: string]: any
}
interface IDescriptor {
    icon?: string
    config_file?: string
    dashboard_config?: { [key: string]: any }
    default_config?: { [key: string]: any }
}