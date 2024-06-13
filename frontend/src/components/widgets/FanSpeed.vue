<template>
  <div class="fan-speed">
    <div class="fan-speed__tablet">
      <div class="fan-speed__control" :class="{disabled: rangeValue === 16}">
        <UiIcon name="minus-circle" filled @click.prevent="rangeValue--"/>
      </div>
      <div class="fan-speed__dashboard">
        <UiCircularInput
            v-model="rangeValue"
            :diameter="200"
            temperature_type="°C"
            :min="16"
            :max="32"
        />
      </div>
      <div class="fan-speed__control" :class="{disabled: rangeValue === 32}">
        <UiIcon name="plus-circle" filled @click.prevent="rangeValue++"/>
      </div>
    </div>
    <div class="fan-speed__buttons">
      <UiButton :class="activeButton === 'Low' ? 'primary': 'secondary'" @click.prevent="activeButton = 'Low'">Low</UiButton>
      <UiButton :class="activeButton === 'Medium' ? 'primary': 'secondary'" @click.prevent="activeButton = 'Medium'">Medium</UiButton>
      <UiButton :class="activeButton === 'High' ? 'primary': 'secondary'" @click.prevent="activeButton = 'High'">High</UiButton>
      <UiButton :class="activeButton === 'Off' ? 'primary': 'secondary'" @click.prevent="activeButton = 'Off'">Off</UiButton>
    </div>
    <div class="fan-speed__toggles">
      <ul>
        <li>
          Master Off
          <UiToggle/>
        </li>
        <li>
          Fan Valve
          <UiToggle/>
        </li>
      </ul>
    </div>
  </div>

</template>
<script setup lang="ts">
import UiIcon from "@components/ui/Icon.vue";
import {ref} from "vue";
import UiCircularInput from "@components/ui/CircularInput.vue";
import UiButton from "@components/ui/Button.vue";
import UiToggle from "@components/ui/Toggle.vue";
const rangeValue = ref(23.3)
const activeButton = ref('Medium')
</script>