import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";
import { useCookies } from "@vueuse/integrations/useCookies";
import { useAuthorizationStore } from "@store/authorization";
import router from "@/router";
import qs from 'qs';
import { toast } from "vue3-toastify";

const cookies = useCookies(['access_token', 'refresh_token']);

interface CustomAxiosRequestConfig extends InternalAxiosRequestConfig {
    metadata?: {
        startTime: Date;
        timer?: any;
        toast?: string;
    };
    _retry?: boolean
}

const useApiFetch: AxiosInstance = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL,
    paramsSerializer: params => {
        return qs.stringify(params);
    }
});

let isRefreshing = false;
let failedQueue: Array<any> = [];

const processQueue = (error: any, token: string | null = null) => {
    failedQueue.forEach(prom => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });

    failedQueue = [];
};

useApiFetch.interceptors.request.use((config: CustomAxiosRequestConfig) => {
    config.metadata = { startTime: new Date() };
    if (cookies.get('access_token')) {
        config.headers['Authorization'] = `Bearer ${cookies.get('access_token')}`;
    }
    config.metadata.timer = setTimeout(() => {
        if (config.metadata) {
            config.metadata.toast = toast.loading('Request is taking longer than usual') as string;
        }
    }, 2000);
    return config;
});

useApiFetch.interceptors.response.use(
    async (response) => {
        const config = response.config as CustomAxiosRequestConfig;
        if (config.metadata?.timer) {
            toast.remove(config.metadata.toast as string);
            clearTimeout(config.metadata.timer);
        }
        return response;
    },
    async (error) => {

        const { status } = error.response || {};
        const config = error.config as CustomAxiosRequestConfig;
        if (config?.metadata?.timer) {
            toast.remove(config.metadata.toast as string);
            clearTimeout(config.metadata.timer);
        }

        if (status === 401 && !config._retry) {
            const authorizationStore = useAuthorizationStore();
            if (cookies.get('refresh_token')) {
                if (isRefreshing) {
                    return new Promise(function (resolve, reject) {
                        failedQueue.push({ resolve, reject });
                    }).then(token => {
                        config.headers['Authorization'] = 'Bearer ' + token;
                        return useApiFetch(config);
                    }).catch(err => {
                        return Promise.reject(err);
                    });
                }

                config._retry = true;
                isRefreshing = true;

                return new Promise(function (resolve, reject) {
                    authorizationStore.refreshToken().then(() => {
                        config.headers['Authorization'] = 'Bearer ' + cookies.get('access_token');
                        processQueue(null, cookies.get('access_token'));
                        resolve(useApiFetch(config));
                    }).catch((err) => {
                        processQueue(err, null);
                        authorizationStore.deleteToken();
                        router.push({ name: 'login' });
                        reject(err);
                    }).finally(() => {
                        isRefreshing = false;
                    });
                });
            } else {
                await authorizationStore.deleteToken();
                await router.push({ name: 'login' });
            }
        }

        if (["ERR_NETWORK", "ECONNABORTED"].includes(error.code)) {
            toast.remove(config.metadata?.toast as string);
            toast.error(error.message);
        }
        if (typeof error.response.data === 'object'){
            for (const eKey in error.response.data) {
                toast.error(error.response.data[eKey]);
            }
        }else {
            toast.remove(config.metadata?.toast as string);
            toast.error(error.response.statusText);
        }

        throw error;
    }
);

export default useApiFetch;
