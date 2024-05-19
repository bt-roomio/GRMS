<template>
  <div class="weather">
    <div class="weather__image">
      <img src="https://source.unsplash.com/random/1200x200/?city" alt="">
    </div>
    <div class="weather__content">
      <div class="weather__info" v-if="weatherData.country_name && weatherData.name">
        <p>
          {{ weatherData.country_name }},
          {{ weatherData.name }},
          {{ new Date().toLocaleDateString('en-US', {day: 'numeric', month: "short", year: "numeric"}) }}
        </p>
        <h2>Welcome back, Satoshi Nakamoto</h2>
      </div>
      <div class="weather__info" v-else>
        <p>&nbsp;</p>
        <h2>&nbsp;</h2>
      </div>
      <div class="weather__detail" v-if="weatherData.icon && weatherData.temp">
        <UiIcon :name="weatherData.icon" filled/>
        {{ weatherData.temp || 0 }} °C
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import {useWeather} from "@store/dashboard/weather";
import {onMounted} from "vue";
import {storeToRefs} from "pinia";
import UiIcon from "@components/ui/Icon.vue";

const storeWeather = useWeather()
const {weatherData} = storeToRefs(storeWeather)

onMounted(async () => {
  await storeWeather.getWeather()
})
</script>