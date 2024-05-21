import axios from "axios";
import {useCookies} from "@vueuse/integrations/useCookies";
import {useAuthorizationStore} from "@store/authorization";
import router from "@/router";
import qs from 'qs'
const cookies = useCookies(['access_token', 'refresh_token'])
const useApiFetch = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL,
    paramsSerializer: params => {
        return qs.stringify(params)
    }
});

useApiFetch.interceptors.request.use(response => {
    if (cookies.get('access_token')){
        response.headers['Authorization'] = `Bearer ${cookies.get('access_token')}`
    }
    return response
})
useApiFetch.interceptors.response.use(
    async (response) => response,
    async (error) => {
        const authorizationStore = useAuthorizationStore();
        const { status } = error.response || {};
        if (status === 401 && error.config && !error.config.isRetry && cookies.get('refresh_token')) {
            error.config.isRetry = true;
            await authorizationStore.refreshToken()
            error.config.headers.Authorization = `Bearer ${cookies.get('access_token')}`;
            return useApiFetch(error.config);
        } else if (status === 401 && error.config) {
            await authorizationStore.deleteToken();
            await router.push({ name: 'login' });
        }

        throw error;
    }
);
export default useApiFetch