
interface ILocales {
    name: string
    value: string
    icon: string
}

interface ITab {
    name: string
    to?: unknown
    badge?: string
    hash?: string
}

interface Item {
    icon: string;
    name: string;
    to: string;
    children?: { icon: string; to: string; name: string; }[];
}

interface IConfigurationRoomsHead {
    [key: string]: unknown
}

interface IConfigurationRoomsData {
    [key: string]: unknown,
    select: boolean
}
interface IConfigurationRoomTypeData {
    [key: string]: unknown,
    select: boolean
}

interface IServerResponse<T> {
    results: T[]
    count: number
}

interface ISortOutput {
    sort_by: string[]
}

interface ICheckAll {
    [key: string]: unknown
    select?: boolean
}

interface IModal {
    closeWithoutEvents: () => void,
    close: () => void,
    open: () => void,
    [key: string]: any
}

interface IModalAddRoom {
    add_room: IModal
}
interface IModalEditRoom {
    edit_room: IModal
}
interface IConfigurationRoomsActions {
    add_room: IModal
    edit_room: IModal
}
interface IConfigurationUsersActions {
    add_user: IModal
    add_role: IModal
    edit_user: IModal
}
interface IStatisticsCard {
    name: string
    difference_value: string
    difference_sign: string
    value: string
}
