import {
    NavigationGuardNext,
    RouteLocationNormalized,
    RouteRecordNormalized,
} from "vue-router";
import {usePermissions} from "@store/dashboard/user/permissions.ts";
import {storeToRefs} from "pinia";
import {useUserStore} from "@store/dashboard/user";
import {useCookies} from "@vueuse/integrations/useCookies";
import router from "@/router";
export default async function (to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext){
    if (!to.matched.find((el) => el.path === '/')) {
        next()
        return
    }
    const cookies = useCookies(['user_id'])
    const storeUser = useUserStore()
    const storePermissions = usePermissions()
    const {access} = to.meta as {access: string[]}
    const {profile} = storeToRefs(storeUser)
    if (!profile.value) {
        if (cookies.get('user_id')) {
            await storeUser.getProfile(cookies.get('user_id'))
        }else {
            next({name: 'login'})
            return
        }
    }
    await storePermissions.setPermissions(profile.value?.groups || [])
    if (!access.length) {
        next()
        return
    }
    const isAccessProblem = access.map(value => storePermissions.hasPermission(value)).find(el => !el)
    if (isAccessProblem === undefined) {
        next()
        return
    }else {
        const routers = router.getRoutes()
        const routerAccess = routers.filter(el => el.meta.access)
        const accessIsAllowed = routerAccess.filter(el => {
            return (el.meta.access as []).map(value => storePermissions.hasPermission(value)).find(element => !element) === undefined
        }) as RouteRecordNormalized[]
        if (accessIsAllowed.length) {
            next(accessIsAllowed[0]);
        }else {
            next(from);
            return
        }
    }
}