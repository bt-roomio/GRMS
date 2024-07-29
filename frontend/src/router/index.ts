import {createRouter, createWebHistory} from 'vue-router'

import Authorization from "../layouts/Authorization.vue";
import Login from "../pages/authorization/Login.vue";

import LayoutsDashboard from "../layouts/Dashboard.vue";
import Main from "../pages/dashboard/Main.vue";
import ForgotPassword from "../pages/authorization/ForgotPassword.vue";
import ResetPassword from "../pages/authorization/ResetPassword.vue";
import Rooms from "../pages/dashboard/rooms/Rooms.vue";
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
import Room from "@/pages/dashboard/rooms/Room.vue";
import DashboardInner from "@/pages/dashboard/configuration/DashboardInner.vue";
import NewPassword from "@/pages/authorization/NewPassword.vue";
import Default from "@/layouts/Default.vue";
import Roles from "@/pages/dashboard/configuration/Roles.vue";
import permission from "@router/middleware/permission.ts";


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
                    meta: {
                        access: ['view_dashboard']
                    }
                },
                {
                    path: 'rooms',
                    name: 'rooms',
                    redirect: '/rooms/room-list',
                    children: [
                        {
                            path: 'room-list',
                            name: 'room-list',
                            component: Rooms,
                            meta: {
                                access: ['view_room']
                            }
                        },
                        {
                            path: '/rooms/room-list/:id',
                            name: 'room-inner',
                            component: Room,
                            meta: {
                                access: ['view_room']
                            }
                        }
                    ]
                },
                {
                    path: 'public-space',
                    name: 'public-space',
                    component: PublicSpace,
                    meta: {
                        access: []
                    }
                },
                {
                    path: 'configuration',
                    name: 'configuration',
                    redirect: '/configuration/users',
                    children: [
                        {
                            path: 'dashboard',
                            name: 'configuration-dashboard',
                            component: Dashboard,
                            meta: {
                                access: ['view_dashboard']
                            }
                        },
                        {
                            path: 'dashboard/:id',
                            name: 'configuration-dashboard-inner',
                            component: DashboardInner,
                            meta: {
                                access: ['view_dashboard', 'change_dashboard']
                            }
                        },
                        {
                            path: 'users',
                            name: 'configuration-users',
                            component: Users,
                            meta: {
                                access: ['view_user']
                            }
                        },
                        {
                            path: 'roles',
                            name: 'configuration-roles',
                            component: Roles,
                            meta: {
                                access: ['view_group']
                            }
                        },
                        {
                            path: 'rooms',
                            name: 'configuration-rooms',
                            component: ConfigurationRooms,
                            meta: {
                                access: ['view_room']
                            }
                        },
                        {
                            path: 'room-types',
                            name: 'configuration-room-types',
                            component: RoomTypes,
                            meta: {
                                access: ['view_roomtype']
                            }
                        },
                        {
                            path: 'controllers',
                            name: 'configuration-controllers',
                            component: Controllers,
                            meta: {
                                access: ['view_device']
                            }
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
                            component: General,
                            meta: {
                                access: ['view_adminsettings']
                            }
                        },
                        {
                            path: 'alarms',
                            name: 'settings-alarms',
                            component: Alarms,
                            meta: {
                                access: ['view_adminsettings']
                            }
                        },
                        {
                            path: 'email-setup',
                            name: 'settings-email-setup',
                            component: EmailSetup,
                            meta: {
                                access: ['view_adminsettings']
                            }
                        },
                    ]
                },
                {
                    path: 'access',
                    name: 'access',
                    component: Access,
                    meta: {
                        access: ['view_permission']
                    }
                },
                {
                    path: 'backlog',
                    name: 'backlog',
                    component: Backlog,
                    meta: {
                        access: []
                    }
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
            path: '/password',
            component: Default,
            children: [
                {
                    path: 'forgot',
                    name: 'forgot-password',
                    component: ForgotPassword
                },
                {
                    path: 'reset',
                    name: 'reset-password',
                    component: ResetPassword
                },
                {
                    path: 'new',
                    name: 'new-password',
                    component: NewPassword
                },
            ]
        }

    ],
    scrollBehavior() {
        return {
            top: 0,
            behavior: 'smooth',
        }
    },
})



router.beforeEach(auth)
router.beforeEach(permission)
export default router