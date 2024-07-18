import {h} from "vue";
import CustomSuccessIcon from "@components/ui/CustomSuccessIcon.vue";
import CustomErrorIcon from "@components/ui/CustomErrorIcon.vue";

export const VNodeIcon = ({ type } : any) => {
    return type === 'success' ? h(CustomSuccessIcon) : h(CustomErrorIcon)
};