interface IConfigurationRoom {
    block?: string
    building?: null | string
    created_at?: number
    device?: null | string
    door_lock_id?: null | string
    floor?: string
    id?: string
    pan_id?: null | string
    public_area_id?: null | string
    room_number?: number
    status?: string
    suite?: null
    tenant?: string
    type?: null | string
}
interface IConfigurationRoomParams {
    room?: string
    type?: string
    floor?: string
    block?: string
    mac_address?: string
    ip_address?: string
}