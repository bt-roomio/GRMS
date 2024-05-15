import {createI18n} from "vue-i18n";
import ru from '@/i18n/locales/ru.json'
import en from '@/i18n/locales/en.json'
import uz from '@/i18n/locales/uz.json'
import {useCookies} from "@vueuse/integrations/useCookies";
const cookies = useCookies(['locale'])
const i18n = createI18n({
    allowComposition: true,
    legacy: false,
    locale: cookies.get('locale') || 'en',
    fallbackLocale: 'en',
    messages: Object.assign({ ru, en, uz }),
});

export default i18n