import {defineStore} from "pinia";
import useApiFetch from "@/composables/useApiFetch.ts";
import {ref} from "vue";

export const useUserStore = defineStore('user', () => {
    const user = ref<IUser | null>(null)
    const getUser = async () => {
        try {
            const {data} = await useApiFetch<IUser>('/users/user/', {method: 'GET'})
            user.value = data
        }catch (e: any) {
            console.log(e)
        }
    }


    return {user, getUser }
})