import {computed} from "vue";
import {defineStore, storeToRefs} from "pinia";
import {useUserStore} from "@store/dashboard/user";

export const useTemplateStore = defineStore('template', () => {
    const storeUser = useUserStore()
    const {profile} = storeToRefs(storeUser)
    const sidebarIsOpen = computed(() => typeof profile.value?.additional_info?.sidebar?.isOpen === 'boolean' ? profile.value?.additional_info?.sidebar?.isOpen : true)
    async function toggleSidebar() {
        await storeUser.saveUserConfiguration('sidebar', { isOpen: !sidebarIsOpen.value });
    }
    return {toggleSidebar, sidebarIsOpen}
})