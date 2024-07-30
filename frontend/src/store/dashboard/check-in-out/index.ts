import {defineStore} from "pinia";
import {toast} from "vue3-toastify";
import {useConfirm} from "@store/dashboard/useConfirm.ts";
import {useI18n} from "vue-i18n";
import {ref} from "vue";
import moment from "moment";

export const useCheckInOutStore = defineStore('check-in-out', () => {
    const confirmStore = useConfirm()
    const {t} = useI18n()
    const state = ref({
        check_in_date: moment().format('YYYY-MM-DD'),
        check_out_date: moment().format('YYYY-MM-DD'),
        check_out_time: '',
        auto_check_out: false,
        first_name: '',
        last_name: '',
        nationality: '',
        gender: 'Man'
    })
    const checkIn = async () => {

    }

    const checkOut = async () => {
        await confirmStore.showConfirm({
            title: 'Checkout',
            content: 'Are you sure want to checkout selected guests in the room?',
            callback: async (confirmed) => {
                if (confirmed) {
                    toast.success(t('toast.user_delete_success') as string);
                }
            }
        })

    }

    const move = async () => {
        await confirmStore.showConfirm({
            title: 'Checkout',
            content: 'Are you sure want to checkout selected guests in the room?',
            callback: async (confirmed) => {
                if (confirmed) {
                    toast.success(t('toast.user_delete_success') as string);
                }
            }
        })
    }

    return { checkIn, checkOut, move, state }
})