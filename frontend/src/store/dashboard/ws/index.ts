import { defineStore } from "pinia";
import { useWebSocket } from "@vueuse/core";
import { useCookies } from "@vueuse/integrations/useCookies";
import { ref } from "vue";
import { useAuthorizationStore } from "@store/authorization";

export const useWS = defineStore('web-socket', () => {
    const state = ref({
        isConnected: false,
        error: null,
        isFirstRequest: true,  // Флаг для первого запроса
        requests: new Map<string, any>(),
        events: new Map<string, any>(),
        attrs: new Map<string, any>(),
        cmdId: 0,
    });

    const authorizationStore = useAuthorizationStore();
    const cookies = useCookies(['access_token']);
    const socket = useWebSocket(`${import.meta.env.VITE_WS_BASE_URL}`, {
        autoReconnect: true,
        onConnected() {
            state.value.isConnected = true;
        },
        onDisconnected() {
            state.value.isConnected = false;
        },
        onError(err) {
            console.error("WebSocket error:", err);
        }
    });
    socket.ws.value ? socket.ws.value.onmessage = async (wsMessage) => {
        let originalRequest: any = null

        const data = JSON.parse(wsMessage.data);
        // Получаю original request
        state.value.requests.forEach(el => {
            if (el.cmds.length){
                if (el.cmds.at(0).cmdId === data.subscriptionId){
                    originalRequest = el
                }
            }
            if (el.authCmd){
                if (el.authCmd.cmdId === data.subscriptionId){
                    originalRequest = el
                }
            }
        });

        state.value.error = data.error_code;
        if (data.error_code === 401) {
            try {
                if (originalRequest) {
                    const tokens = await authorizationStore.refreshToken();
                    originalRequest.authCmd.token = tokens.access;
                    socket.send(JSON.stringify(originalRequest));
                }
            } catch (error) {
                console.error("Token update error:", error);
            }
        } else {
            if (originalRequest && originalRequest.cmds.length) {
                const objKey = originalRequest.cmds[0].entityId + '_' + originalRequest.cmds[0].scope
                state.value.events.set(objKey, data);
                state.value.attrs.set(objKey, Object.keys(data?.data));
            }
        }
    } : () => console.log('Socket not found');
    const send = (data: any) => {
        if (state.value.isFirstRequest) {
            sendAuth()
        }

        const requestObj: any = {
            cmds: [{
                ...data,
                cmdId: state.value.cmdId
            }]
        };
        const objKey = data.entityId + '_' + data.scope
        if (!state.value.requests.has(objKey)) {
            state.value.requests.set(objKey, requestObj);
            socket.send(JSON.stringify(requestObj));
            state.value.cmdId++
        }
    };

    const sendAuth = () => {
        const authObj = {
            cmds: [],
            authCmd: { cmdId: 0, token: cookies.get('access_token') }
        }
        state.value.requests.set('auth', authObj);
        socket.send(JSON.stringify(authObj));
        state.value.cmdId++
        state.value.isFirstRequest = false;
    }

    const unSubscription = (obj: any) => {
        const unSubKey = obj.entityId + '_' + obj.scope
        const originalEvent = state.value.events?.get(unSubKey) ? JSON.parse(JSON.stringify(state.value.events.get(unSubKey))) : null;
        if (!originalEvent) return
        const request = JSON.stringify({
            cmds: [{
                ...obj,
                type: `${obj.type}_UNSUBSCRIBE`,
                cmdId: originalEvent.subscriptionId
            }]
        })
        if (state.value.requests.has(unSubKey)){
            socket.send(request);
            state.value.requests.delete(unSubKey)
        }
        state.value.attrs.clear()
    }

    return { socket, state, send, unSubscription };
});
