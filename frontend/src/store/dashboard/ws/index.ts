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
        requests: new Map<number, any>(),
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
        const data = JSON.parse(wsMessage.data);
        state.value.error = data.error_code;
        if (data.error_code === 401) {
            try {
                const originalRequest = state.value.requests.get(data.subscriptionId);
                if (originalRequest) {
                    const tokens = await authorizationStore.refreshToken();

                    originalRequest.authCmd.token = tokens.access;
                    socket.send(JSON.stringify(originalRequest));
                }
            } catch (error) {
                console.error("Token update error:", error);
            }
        } else {
            const originalRequest = state.value.requests.get(data.subscriptionId);
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
        if (!state.value.requests.has(cmdId)) {
            state.value.requests.set(cmdId, requestObj);
            socket.send(JSON.stringify(requestObj));
        }
    };

    const sendAuth = () => {
        const authObj = {
            cmds: [],
            authCmd: { cmdId: 0, token: cookies.get('access_token') }
        }
        state.value.requests.set(0, authObj);
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
