import {defineStore} from "pinia";
import {useWebSocket} from "@vueuse/core";
import {useCookies} from "@vueuse/integrations/useCookies";
import {computed} from "vue";
let cmdId = 0
export const useWS = defineStore('web-socket', () => {
    const cookies = useCookies(['access_token'])
    const { status, data: dataWs, send: sendWS, open, close } = useWebSocket(`${import.meta.env.VITE_WS_BASE_URL}?token=${cookies.get('access_token')}`, {
        autoReconnect: true
    })
    const data = computed(() => JSON.parse(dataWs.value))
    const send = (data: WsSendDataDto) => {
        if (!data.entityId) return
        cmdId++
        return sendWS(JSON.stringify({"cmds": [{...data, cmdId}]}))
    }

    return {
        status,
        data,
        send,
        open,
        close
    };
})