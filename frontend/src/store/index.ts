import {useI18n} from "vue-i18n";

export default function i18nStore() {
    const {t} = useI18n()

    return t
}