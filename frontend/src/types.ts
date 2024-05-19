
interface ILocales {
    name: string
    code: string
    icon: string
}

interface ITab {
    name: string
    to: unknown
    badge?: string
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

interface ICheckAll {
    select: boolean
}

interface IModal {close: () => void, open: () => void}

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
