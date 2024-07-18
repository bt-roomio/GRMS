import {ref} from "vue";
import {defineStore} from "pinia";

export const useTemplateStore = defineStore('template', () => {
    const sidebarIsOpen = ref(false)
    function toggleSidebar() {
        sidebarIsOpen.value = !sidebarIsOpen.value
    }
    return {toggleSidebar, sidebarIsOpen}
})