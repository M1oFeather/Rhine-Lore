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
const sizeStyle = computed(() => `${props.size}px`);
</script>

<template>
  <svg
    class="game-icon"
    viewBox="0 0 24 24"
    fill="currentColor"
    :aria-hidden="label ? undefined : 'true'"
    :aria-label="label || undefined"
    :style="{width: sizeStyle, height: sizeStyle}"
  >
    <path v-for="(path, index) in icon.paths" :key="`p-${index}`" :d="path" />
  </svg>
</template>

<style scoped>
.game-icon {
  display: inline-block;
  vertical-align: middle;
}
</style>
