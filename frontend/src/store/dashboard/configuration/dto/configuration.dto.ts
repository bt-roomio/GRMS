type IConfigurationRoom = {
    id?: any
    block: any
    devices?: any
    status?: any
    state?: any
    floor: any
    room_number: any
    type: IConfigurationRoomTypes | any
}
interface IConfigurationRoomTypes {
    id?: string
    type?: string | null
    title: string
    check_in_out_address?: string | null
    check_in_value?: string | null
    check_out_value?: string | null
    dashboard?: {[key: string]: unknown} | null | any
}
interface IConfigurationDashboard {
    id?: string
    title: string | null
    configuration: { [key: string]: any }
    assigned_customers?: string | null
    mobile_hide?: boolean | null
    mobile_order?: number | null
    external_id?: string | null
}
interface IConfigurationRoomTypesData {
    select?: boolean,
    [key: string]: any,
}
type IConfigurationDevice = {
    id?: string
    created_at?: number
    name?: string
    type?: string
    status?: boolean
    tenant?: string,
    customer?: string,
    room?: string,
    device_profile?: string,
    label?: string | null,
    additional_info?: {
        description: string
    },
    device_data?: {
        configuration: {
            type: string
        },
        transportConfiguration: {
            type: string
        }
    },
    external_id?: string | null
}
type IConfigurationRoomResponse = {
    results: IConfigurationRoom[]
    count: number
}
type IConfigurationRoomParams = {
    sort_by?: string[]
    [key: string]: unknown
}
