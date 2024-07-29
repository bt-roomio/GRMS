interface IUser {
    id?: string
    first_name?: string
    last_name?: string
    email?: string
    additional_info?: null | any
    phone?: null | any
    created_at?: number
    tenant_id?: string
    groups?: IGroup[] | []
}

interface IGroup {
    id: number
    name: string,
    permissions: IPermission[]
}
interface IPermission {
    id: number
    name: string,
    codename: string,
    content_type: number,
}