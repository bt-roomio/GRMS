import { createApp } from 'vue'
import 'vue3-toastify/dist/index.css';
import './style.css'
import './assets/styles/styles.scss'
import App from './App.vue'
import {createPinia} from "pinia";
import Vue3Toasity, { type ToastContainerOptions } from 'vue3-toastify';
import i18n from "./i18n";
import router from "./router";
import {Tooltip} from "@/directives/tooltip.ts";

const app = createApp(App)

const pinia = createPinia()
app.use(pinia)

app.use(Vue3Toasity,
    { autoClose: 3000 } as ToastContainerOptions,
)

app.use(i18n)

app.use(router)

app.directive('tooltip', Tooltip);
app.mount('#app')
