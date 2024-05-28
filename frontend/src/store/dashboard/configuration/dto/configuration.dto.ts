type IConfigurationRoom = {
    id?: any
    block: any
    devices?: any
    floor: any
    room_number: any
    type?: any
}
type IConfigurationRoomResponse = {
    results: IConfigurationRoom[]
    count: number
}
type IConfigurationRoomParams = {
    sort_by?: string[]
    [key: string]: unknown
}