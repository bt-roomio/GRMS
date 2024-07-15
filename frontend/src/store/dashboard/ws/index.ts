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
        attrs: new Map<string, any>()
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
                state.value.events.set(originalRequest.cmds[0].entityId + '_' + originalRequest.cmds[0].scope, data);
                state.value.attrs.set(originalRequest.cmds[0].entityId + '_' + originalRequest.cmds[0].scope, Object.keys(data?.data));
            }
        }
    } : () => console.log('Socket not found');
    const send = (data: any) => {
        if (state.value.isFirstRequest) {
            sendAuth()
        }
        const cmdId = state.value.requests.size;
        const requestObj: any = {
            cmds: [{
                ...data,
                cmdId
            }]
        };
        if (!state.value.requests.has(data.entityId + '_' + data.scope)) {
            state.value.requests.set(data.entityId + '_' + data.scope, requestObj);
            socket.send(JSON.stringify(requestObj));
        }
    };

    const sendAuth = () => {
        const authObj = {
            cmds: [],
            authCmd: { cmdId: 0, token: cookies.get('access_token') }
        }
        state.value.requests.set('auth', authObj);
        socket.send(JSON.stringify(authObj));
        state.value.isFirstRequest = false;
    }

    const unSubscription = (obj: any) => {
        const originalEvent = JSON.parse(JSON.stringify(state.value.events.get(obj.entityId + '_' + obj.scope)));
        if (!originalEvent) return
        const request = JSON.stringify({
            cmds: [{
                ...obj,
                type: `${obj.type}_UNSUBSCRIBE`,
                cmdId: originalEvent.subscriptionId
            }]
        })
        socket.send(request);
        state.value.attrs.clear()
    }


    return { socket, state, send, unSubscription };
});
