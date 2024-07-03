<template>
  <div class="fan-speed">
    <div class="fan-speed__tablet">
      <div class="fan-speed__control" :class="{disabled: rangeValue === value.min}">
        <UiIcon name="minus-circle-control" filled @click.prevent="minus"/>
      </div>
      <div class="fan-speed__dashboard">
        <UiCircularInput
            v-model="rangeValue"
            :temperature_type="units[value.unit]"
            :min="value.min"
            :max="value.max"
        />
      </div>
      <div class="fan-speed__control" :class="{disabled: rangeValue === value.max}">
        <UiIcon name="plus-circle-control" filled @click.prevent="plus"/>
      </div>
    </div>
    <div class="fan-speed__buttons" :class="{'col-2': value.controls_type !== 'line'}" v-if="value.controls.length">
      <UiButton
          v-for="item in value.controls"
          :class="activeButton === item.value ? 'primary': 'secondary'"
          @click.prevent="activeButton = item.value"
      >
        {{ item.power_level_name || $t('dashboard.widget.form.power_level_empty') }}
      </UiButton>
    </div>
    <div class="fan-speed__toggles">
      <ul>
        <li v-if="value.master_off">
          {{ $t('dashboard.widget.form.master_off') }}
          <UiToggle/>
        </li>
        <li v-if="value.fan_valve">
          {{ $t('dashboard.widget.form.fan_valve') }}
          <UiToggle/>
        </li>
      </ul>
    </div>
  </div>

</template>
<script setup lang="ts">
import UiIcon from "@components/ui/Icon.vue";
import {computed, ref} from "vue";
import UiCircularInput from "@components/ui/CircularInput.vue";
import UiButton from "@components/ui/Button.vue";
import UiToggle from "@components/ui/Toggle.vue";
const props = defineProps(['value'])
const rangeValue = ref(props.value.default_temperature)
const activeButton = ref('0')
const plus = () => {
  if (rangeValue.value !== undefined) {
    rangeValue.value += 0.5;
  }
}
const minus = () => {
  if (rangeValue.value !== undefined && rangeValue.value > 0) {
    rangeValue.value -= 0.5;
  }
}

const units = computed(() => ({
  "Celsius": '°C',
  "Fahrenheit": '°F',
}) as  {[key: string]: any})

</script>