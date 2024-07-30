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
      <template v-if="$slots.button">
        <slot name="button" />
      </template>
      <template v-else>
        <div class="page-head__action" v-if="button !== undefined">
          <Button @click.prevent="$emit('clickButton')" :class="buttonClass ? buttonClass: 'primary'">
            <UiIcon v-if="buttonIcon" :name="buttonIcon" filled />
            {{button}}
          </Button>
        </div>
        <div class="page-head__action row" v-if="buttons !== undefined">
          <Button v-for="item in buttons" :key="item.id" @click.prevent="$emit('clickButton', item)" :class="item.class ? item.class : 'primary'">
            <UiIcon v-if="item.icon" :name="item.icon" filled />
            {{item.name}}
          </Button>
        </div>
      </template>
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
  buttons?: { [key: string]: any }[],
  buttonIcon?: string,
  buttonClass?: string | null,
  back?: string | null,
  backTo?: RouteLocationRaw
}>()
</script>