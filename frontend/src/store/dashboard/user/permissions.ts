import {defineStore} from "pinia";
import {ref} from "vue";

export const usePermissions = defineStore('permissions', () => {
    const permissions = ref(new Map())
    const loading = ref(true)
    const setPermissions = async (groups: IGroup[]) => {
        permissions.value.clear()
        groups.map(value => value.permissions.map(el => permissions.value.set(el.codename, el.content_type)))
        loading.value = false
    }
    const hasPermission = (access: string) => {
        return permissions.value.has(access)
    }

    return {setPermissions, hasPermission, permissions, loading}
})