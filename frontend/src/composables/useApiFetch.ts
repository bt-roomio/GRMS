import axios, {AxiosInstance, InternalAxiosRequestConfig} from "axios";
import {useCookies} from "@vueuse/integrations/useCookies";
import {useAuthorizationStore} from "@store/authorization";
import router from "@/router";
import qs from 'qs'
import {toast} from "vue3-toastify";
const cookies = useCookies(['access_token', 'refresh_token'])

interface CustomAxiosRequestConfig extends InternalAxiosRequestConfig {
    metadata?: {
        startTime: Date;
        timer?: any;
        toast?: string;
    };
}

const useApiFetch: AxiosInstance = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL,
    paramsSerializer: params => {
        return qs.stringify(params)
    }
});

useApiFetch.interceptors.request.use((config: CustomAxiosRequestConfig) => {
    config.metadata = { startTime: new Date() };
    if (cookies.get('access_token')){
        config.headers['Authorization'] = `Bearer ${cookies.get('access_token')}`
    }
    config.metadata.timer = setTimeout(() => {
        if (config.metadata){
            config.metadata.toast = toast.loading('Request is taking longer than usual') as string;
        }
    }, 2000);

    return config
})
useApiFetch.interceptors.response.use(
    async (response) => {
        const config = response.config as CustomAxiosRequestConfig;
        if (config.metadata?.timer) {
            toast.remove(config.metadata.toast as string)
            clearTimeout(config.metadata.timer);
        }
        return response
    },
    async (error) => {
        const authorizationStore = useAuthorizationStore();
        const { status } = error.response || {};
        const config = error.config as CustomAxiosRequestConfig;
        if (config?.metadata?.timer) {
            toast.remove(config.metadata.toast as string)
            clearTimeout(config.metadata.timer);
        }
        if (status === 401 && error.config && !error.config.isRetry && cookies.get('refresh_token')) {
            error.config.isRetry = true;
            await authorizationStore.refreshToken()
            error.config.headers.Authorization = `Bearer ${cookies.get('access_token')}`;
            return useApiFetch(error.config);
        }
        else if (status === 401 && error.config) {
            await authorizationStore.deleteToken();
            await router.push({ name: 'login' });
        }

        if (["ERR_NETWORK", "ECONNABORTED"].includes(error.code)){
            toast.remove(config.metadata?.toast as string)
            toast.error(error.message)
        }
        throw error;
    }
);
export default useApiFetch