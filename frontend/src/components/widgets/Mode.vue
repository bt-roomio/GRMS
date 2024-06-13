<template>
  <div class="mode">
    <ul>
      <li>
        DND
        <UiToggle :model-value="true"/>
      </li>
      <li>
        MUR
        <UiToggle :model-value="true"/>
      </li>
      <li>
        Door contact
        <UiToggle :model-value="false"/>
      </li>
      <li>
        Door open
        <UiToggle :model-value="true"/>
      </li>
      <li>
        Main Relay
        <UiToggle :model-value="true"/>
      </li>
      <li>
        Check-In
        <UiToggle :model-value="true"/>
      </li>
      <li>
        Balcony scenario
        <UiToggle :model-value="true"/>
      </li>
    </ul>
  </div>
</template>
<script setup lang="ts">
import UiToggle from "@components/ui/Toggle.vue";
</script>