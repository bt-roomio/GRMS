import {createRouter, createWebHistory} from 'vue-router'

import Authorization from "../layouts/Authorization.vue";
import Login from "../pages/authorization/Login.vue";

import LayoutsDashboard from "../layouts/Dashboard.vue";
import Main from "../pages/dashboard/Main.vue";
import ForgotPassword from "../pages/authorization/ForgotPassword.vue";
import ResetPassword from "../pages/authorization/ResetPassword.vue";
import Rooms from "../pages/dashboard/Rooms.vue";
import ConfigurationRooms from "../pages/dashboard/configuration/Rooms.vue";
import PublicSpace from "../pages/dashboard/PublicSpace.vue";
import Settings from "../pages/dashboard/settings/Settings.vue";
import Access from "../pages/dashboard/Access.vue";
import Backlog from "../pages/dashboard/Backlog.vue";
import Controllers from "../pages/dashboard/configuration/Controllers.vue";
import RoomTypes from "../pages/dashboard/configuration/RoomTypes.vue";
import Users from "../pages/dashboard/configuration/Users.vue";
import General from "../pages/dashboard/settings/General.vue";
import Alarms from "../pages/dashboard/settings/Alarms.vue";
import EmailSetup from "../pages/dashboard/settings/EmailSetup.vue";
import auth from "@router/middleware/auth.ts";
import Dashboard from "@/pages/dashboard/configuration/Dashboard.vue";


const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/',
            component: LayoutsDashboard,
            children: [
                {
                    path: '',
                    name: 'main',
                    component: Main,
                },
                {
                    path: 'rooms',
                    name: 'rooms',
                    component: Rooms
                },
                {
                    path: 'public-space',
                    name: 'public-space',
                    component: PublicSpace
                },
                {
                    path: 'configuration',
                    name: 'configuration',
                    redirect: '/configuration/users',
                    children: [
                        {
                            path: 'dashboard',
                            name: 'configuration-dashboard',
                            component: Dashboard
                        },
                        {
                            path: 'users',
                            name: 'configuration-users',
                            component: Users
                        },
                        {
                            path: 'rooms',
                            name: 'configuration-rooms',
                            component: ConfigurationRooms
                        },
                        {
                            path: 'room-types',
                            name: 'configuration-room-types',
                            component: RoomTypes
                        },
                        {
                            path: 'controllers',
                            name: 'configuration-controllers',
                            component: Controllers
                        },
                    ]
                },
                {
                    path: 'settings',
                    name: 'settings',
                    component: Settings,
                    redirect: '/settings/general',
                    children: [
                        {
                            path: 'general',
                            name: 'settings-general',
                            component: General
                        },
                        {
                            path: 'alarms',
                            name: 'settings-alarms',
                            component: Alarms
                        },
                        {
                            path: 'email-setup',
                            name: 'settings-email-setup',
                            component: EmailSetup
                        },
                    ]
                },
                {
                    path: 'access',
                    name: 'access',
                    component: Access
                },
                {
                    path: 'backlog',
                    name: 'backlog',
                    component: Backlog
                }
            ]
        },
        {
            path: '/auth',
            component: Authorization,
            redirect: '/auth/login',
            children: [{
                path: 'login',
                name: 'login',
                component: Login
            }]
        },
        {
            path: '/forgot-password',
            name: 'forgot-password',
            component: ForgotPassword
        },
        {
            path: '/reset-password',
            name: 'reset-password',
            component: ResetPassword
        },
    ],
    scrollBehavior() {
        return {
            top: 0,
            behavior: 'smooth',
        }
    },
})



router.beforeEach(auth)
export default router