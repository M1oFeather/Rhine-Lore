<script setup lang="ts">
import { computed } from "vue";

import { type GameIconName, gameIcons } from "../icons/gameIconPack";

const props = withDefaults(
  defineProps<{
    name: GameIconName;
    label?: string;
    size?: number;
  }>(),
  {
    label: "",
    size: 20,
  },
);

const icon = computed(() => gameIcons[props.name]);
</script>

<template>
  <component
    :is="icon"
    class="game-icon"
    :size="size"
    :stroke-width="1.8"
    :aria-hidden="label ? undefined : 'true'"
    :aria-label="label || undefined"
  />
</template>

<style scoped>
.game-icon {
  display: block;
  flex: 0 0 auto;
  stroke-linecap: round;
  stroke-linejoin: round;
  vertical-align: middle;
}
</style>
