<template>
  <div class="card">
    <div class="card__content">
      <div class="card__head">
        <h3>{{ $t('dashboard.settings.alarms.title') }}</h3>
        <p>{{ $t('dashboard.settings.alarms.description') }}</p>
      </div>
      <ul class="card__list">
        <li class="card__list-item">
          <div class="item-texts">
            <p class="title">{{ $t('dashboard.settings.alarms.bathroom.title') }}</p>
            <p class="description">{{ $t('dashboard.settings.alarms.bathroom.description') }}</p>
          </div>
          <div class="item-actions">
            <UiToggle />
          </div>
        </li>
        <li class="card__list-item">
          <div class="item-texts">
            <p class="title">{{ $t('dashboard.settings.alarms.humidity.title') }}</p>
            <p class="description">{{ $t('dashboard.settings.alarms.humidity.description') }}</p>
          </div>
          <div class="item-actions">
            <UiToggle />
          </div>
        </li>
      </ul>
      <div class="card__buttons inline-block mt-5">
        <UiButton class="primary">{{ $t('dashboard.settings.save') }}</UiButton>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import UiButton from "../../../components/ui/Button.vue";
import UiToggle from "../../../components/ui/Toggle.vue";
</script>