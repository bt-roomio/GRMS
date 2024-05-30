type IConfigurationRoom = {
    id?: any
    block: any
    devices?: any
    floor: any
    room_number: any
    type?: any
}
interface IConfigurationRoomTypes {
    id?: string
    title?: string
    check_in_out_address?: string | null
    check_in_value?: string | null
    check_out_value?: string | null
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