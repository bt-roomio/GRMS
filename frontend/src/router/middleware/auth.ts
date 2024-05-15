import {NavigationGuardNext, RouteLocationNormalized, useRouter} from "vue-router";
import {computed} from "vue";
import {useCookies} from "@vueuse/integrations/useCookies";


export default function (to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext){
    const cookies = useCookies(['access_token', 'refresh_token'])
    const isAuth = computed(() => (!!cookies.get('access_token') || !!cookies.get('refresh_token')))
    if (!to.matched.find((el) => el.path === '/')) {
        next()
        return
    }
    const {push} = useRouter()
    if (!isAuth.value) {
        push({name: 'login'}).then(r => {
            console.log(r, from)
        });
        return
    }
    next();
}
