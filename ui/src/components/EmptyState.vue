<script setup lang="ts">
import type { GameIconName } from "../icons/gameIconPack";

import GameIcon from "./GameIcon.vue";

withDefaults(
  defineProps<{
    title: string;
    description?: string;
    icon?: GameIconName;
    compact?: boolean;
  }>(),
  {
    description: "",
    icon: undefined,
    compact: false,
  },
);
</script>

<template>
  <div class="empty-state" :class="{compact}">
    <span v-if="icon" class="empty-state-icon">
      <GameIcon :name="icon" :size="compact ? 24 : 30" />
    </span>
    <strong>{{ title }}</strong>
    <p v-if="description">{{ description }}</p>
    <div v-if="$slots.default" class="empty-state-actions">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.empty-state {
  display: grid;
  justify-items: center;
  gap: 8px;
  padding: 28px 20px;
  text-align: center;
  color: var(--text);
}

.empty-state.compact {
  gap: 6px;
  padding: 16px 12px;
}

.empty-state-icon {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 16px;
  background: var(--blue-soft);
  color: var(--blue);
}

.empty-state.compact .empty-state-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
}

.empty-state strong {
  font-size: 15px;
}

.empty-state p {
  max-width: 320px;
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.6;
}

.empty-state-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-top: 4px;
}

.empty-state-actions .el-button {
  margin-left: 0;
}
</style>
