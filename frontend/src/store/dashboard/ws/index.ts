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
        events: new Map<number, any>()
    });

    const authorizationStore = useAuthorizationStore();
    const cookies = useCookies(['access_token']);
    const socket = useWebSocket(`${import.meta.env.VITE_WS_BASE_URL}`, {
        autoReconnect: true,
        onMessage(ws) {
            ws.onmessage = async (wsMessage) => {
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
                        console.error("Ошибка обновления токена:", error);
                    }
                } else {
                    const originalRequest = state.value.requests.get(data.subscriptionId);
                    if (originalRequest) {
                        state.value.events.set(originalRequest.cmds[0].entityId, data);
                    }
                }
            }
        },
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

    const unSubscription = (cmdId: number) => {
        const originalRequest = JSON.parse(JSON.stringify(state.value.requests.get(cmdId)));
        if (!originalRequest) return
        delete originalRequest?.authCmd
        originalRequest.cmds[0].type = `${originalRequest.cmds[0].type}_UNSUBSCRIBE`
        socket.send(JSON.stringify(originalRequest));
    }

    return { socket, state, send, unSubscription };
});
