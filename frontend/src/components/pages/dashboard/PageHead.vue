<template>
  <div class="page-head">
    <div class="page-head__back" v-if="back && backTo">
      <Button class="text" @click.prevent="$router.push(backTo)">
        <UiIcon name="arrow-left" filled />
        {{back}}
      </Button>
    </div>
    <div class="page-head__content">
      <div class="page-head__title">
        <h1>{{title}}</h1>
        <p>{{description}}</p>
      </div>
      <div class="page-head__action" v-if="button !== undefined">
        <Button :class="buttonClass ? buttonClass: 'primary'">
          <UiIcon v-if="buttonIcon" :name="buttonIcon" filled />
          {{button}}
        </Button>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import Button from "../../ui/Button.vue";
import UiIcon from "../../ui/Icon.vue";
import {RouteLocationRaw} from "vue-router";

defineEmits(['clickButton'])
defineProps<{
  title: string,
  description?: string,
  button?: string,
  buttonIcon?: string,
  buttonClass?: string | null,
  back?: string | null,
  backTo?: RouteLocationRaw
}>()
</script>