import { useI18n } from "vue-i18n";
import { ref } from "vue";
import {defineStore} from "pinia";

interface IConfirmParams {
    icon?: string
    isOpen?: boolean
    title?: string;
    subtitle?: string;
    content?: string;
    buttons?: IConfirmButtons;
    callback: (confirm: boolean) => void | Promise<void> | null;
}

interface IConfirmButtons {
    cancel: IConfirmButtonsParams;
    confirm?: IConfirmButtonsParams;
}

interface IConfirmButtonsParams {
    text: string;
    class: string;
}

export const useConfirm = defineStore('confirm', () => {
    const { t } = useI18n();
    const confirm = ref<IConfirmParams>({
        icon: 'featured',
        isOpen: false,
        title: t('confirm.title'),
        subtitle: '',
        content: '',
        buttons: {
            cancel: {
                text: t('confirm.button_cancel'),
                class: 'text'
            },
            confirm: {
                text: t('confirm.button_confirm'),
                class: 'primary'
            },
        },
        callback: (confirm) => {console.log(confirm)}
    });

    const handleConfirm = () => {
        confirm.value.isOpen = false;
        confirm.value.callback(true);
    };

    const handleCancel = () => {
        confirm.value.isOpen = false;
        confirm.value.callback(false);
    };

    const showConfirm = async (params: IConfirmParams) => {
        confirm.value.isOpen = true;
        confirm.value.icon = typeof params.icon === "string" ? params.icon : 'featured';
        confirm.value.title = params.title || t('confirm.title') || 'Confirm your action';
        confirm.value.subtitle = params.subtitle || '';
        confirm.value.content = params.content || '';
        confirm.value.buttons = params.buttons || {
            cancel: {
                text: t('confirm.button_cancel'),
                class: 'text'
            },
            confirm: {
                text: t('confirm.button_confirm'),
                class: 'primary'
            },
        };
        confirm.value.callback = params.callback;
    };

    return { confirm, showConfirm, handleConfirm, handleCancel };
})