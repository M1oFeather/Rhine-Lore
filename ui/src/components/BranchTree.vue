<script setup lang="ts">
import {computed} from "vue";

import type {BookBranch} from "../api";
import GameIcon from "./GameIcon.vue";

type LayoutNode = BookBranch & {x: number; y: number};
type LayoutEdge = {id: string; path: string; kind: BookBranch["kind"]};
type LayoutAnchor = {id: string; y: number; label: string};

const props = defineProps<{
  branches: BookBranch[];
  selectedId: string;
  chapterTitle: string;
}>();

const emit = defineEmits<{
  select: [branch: BookBranch];
  create: [];
}>();

const kindMeta = {
  choice: {label: "关键选择", tone: "choice"},
  relationship: {label: "关系变化", tone: "relationship"},
  clue: {label: "新线索", tone: "clue"},
  free: {label: "自由续写", tone: "free"},
} as const;

const layout = computed(() => {
  const byId = new Map(props.branches.map((branch) => [branch.branch_id, branch]));
  const children = new Map<string, BookBranch[]>();
  props.branches.forEach((branch) => {
    const parentId = branch.parent_branch_id || "";
    if (!parentId || !byId.has(parentId)) return;
    const siblings = children.get(parentId) || [];
    siblings.push(branch);
    children.set(parentId, siblings);
  });
  children.forEach((rows) => rows.sort((a, b) => a.created_at.localeCompare(b.created_at)));

  const roots = props.branches
    .filter((branch) => !branch.parent_branch_id || !byId.has(branch.parent_branch_id))
    .sort((a, b) => a.root_offset - b.root_offset || a.created_at.localeCompare(b.created_at));
  const nodes: LayoutNode[] = [];
  let nextLeafY = 52;
  let maxDepth = 0;

  const place = (branch: BookBranch): number => {
    const descendants = children.get(branch.branch_id) || [];
    const descendantYs = descendants.map(place);
    const y = descendantYs.length
      ? descendantYs.reduce((total, value) => total + value, 0) / descendantYs.length
      : nextLeafY;
    if (!descendantYs.length) nextLeafY += 92;
    const depth = Math.max(0, Number(branch.depth) || 0);
    maxDepth = Math.max(maxDepth, depth);
    nodes.push({...branch, x: 164 + depth * 220, y});
    return y;
  };
  roots.forEach(place);

  const placedById = new Map(nodes.map((node) => [node.branch_id, node]));
  const edges: LayoutEdge[] = [];
  nodes.forEach((node) => {
    if (!node.parent_branch_id) return;
    const parent = placedById.get(node.parent_branch_id);
    if (!parent) return;
    const startX = parent.x + 184;
    const endX = node.x;
    const bend = Math.max(28, (endX - startX) * 0.52);
    edges.push({
      id: `${parent.branch_id}-${node.branch_id}`,
      kind: node.kind || "free",
      path: `M ${startX} ${parent.y} C ${startX + bend} ${parent.y}, ${endX - bend} ${node.y}, ${endX} ${node.y}`,
    });
  });

  const rootGroups = new Map<number, LayoutNode[]>();
  nodes.filter((node) => !node.parent_branch_id).forEach((node) => {
    const key = Number(node.root_offset ?? node.offset) || 0;
    const group = rootGroups.get(key) || [];
    group.push(node);
    rootGroups.set(key, group);
  });
  const anchors: LayoutAnchor[] = [...rootGroups.entries()].map(([offset, rows]) => {
    const y = rows.reduce((total, row) => total + row.y, 0) / rows.length;
    return {
      id: String(offset),
      y,
      label: `${Math.round(rows[0]?.progress || 0)}%`,
    };
  });
  rootGroups.forEach((rows, offset) => {
    const anchor = anchors.find((item) => item.id === String(offset));
    if (!anchor) return;
    rows.forEach((node) => {
      edges.push({
        id: `anchor-${offset}-${node.branch_id}`,
        kind: node.kind || "free",
        path: `M 118 ${anchor.y} C 136 ${anchor.y}, 142 ${node.y}, 164 ${node.y}`,
      });
    });
  });

  return {
    nodes,
    edges,
    anchors,
    width: Math.max(760, 164 + (maxDepth + 1) * 220 + 210),
    height: Math.max(260, nextLeafY + 26),
  };
});

const endingCount = computed(() => props.branches.filter((branch) => branch.is_leaf).length);
</script>

<template>
  <section class="branch-tree-shell">
    <header class="branch-tree-summary">
      <div>
        <small>当前章节</small>
        <strong>{{ chapterTitle }}</strong>
      </div>
      <dl>
        <div><dt>{{ branches.length }}</dt><dd>故事节点</dd></div>
        <div><dt>{{ endingCount }}</dt><dd>开放结局</dd></div>
      </dl>
    </header>

    <div class="branch-tree-legend" aria-label="分支类型图例">
      <span v-for="(meta, key) in kindMeta" :key="key" :class="`tone-${meta.tone}`">
        <i />{{ meta.label }}
      </span>
    </div>

    <div v-if="branches.length" class="branch-tree-scroll">
      <div
        class="branch-tree-canvas"
        :style="{width: `${layout.width}px`, height: `${layout.height}px`}"
      >
        <div class="branch-mainline-label">
          <GameIcon name="book-open" :size="15" />
          <span>原作主线</span>
        </div>
        <svg
          class="branch-tree-lines"
          :width="layout.width"
          :height="layout.height"
          :viewBox="`0 0 ${layout.width} ${layout.height}`"
          aria-hidden="true"
        >
          <path
            v-if="layout.anchors.length > 1"
            class="branch-mainline-path"
            :d="`M 118 ${Math.min(...layout.anchors.map((item) => item.y))} L 118 ${Math.max(...layout.anchors.map((item) => item.y))}`"
          />
          <path
            v-for="edge in layout.edges"
            :key="edge.id"
            class="branch-edge"
            :class="`tone-${kindMeta[edge.kind || 'free'].tone}`"
            :d="edge.path"
          />
        </svg>

        <div
          v-for="anchor in layout.anchors"
          :key="anchor.id"
          class="branch-anchor-node"
          :style="{top: `${anchor.y - 15}px`}"
        >
          <span>{{ anchor.label }}</span>
          <i />
        </div>

        <button
          v-for="node in layout.nodes"
          :key="node.branch_id"
          type="button"
          class="branch-tree-node"
          :class="[`tone-${kindMeta[node.kind || 'free'].tone}`, {selected: node.branch_id === selectedId}]"
          :style="{left: `${node.x}px`, top: `${node.y - 31}px`}"
          :aria-current="node.branch_id === selectedId ? 'true' : undefined"
          @click="emit('select', node)"
        >
          <span class="branch-node-kind">{{ kindMeta[node.kind || "free"].label }}</span>
          <strong>{{ node.title || node.guidance || "未命名分支" }}</strong>
          <small>
            <template v-if="node.children_count">{{ node.children_count }} 条后续</template>
            <template v-else>开放结局</template>
            <b>第 {{ node.depth + 1 }} 层</b>
          </small>
        </button>
      </div>
    </div>

    <div v-else class="branch-tree-empty">
      <span><GameIcon name="git-fork" :size="24" /></span>
      <strong>故事还只有一条主线</strong>
      <p>从正文任意段落或当前阅读位置，写下第一个不同选择。</p>
      <button type="button" @click="emit('create')">
        <GameIcon name="sparkles" :size="15" />
        创建第一条分支
      </button>
    </div>
  </section>
</template>

<style scoped>
.branch-tree-shell {
  display: grid;
  min-width: 0;
  min-height: 0;
  grid-template-rows: auto auto minmax(0, 1fr);
  background: var(--panel);
}

.branch-tree-summary {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 16px 18px 11px;
}

.branch-tree-summary > div {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.branch-tree-summary small,
.branch-tree-summary dd {
  color: var(--muted-2);
  font-size: 11px;
}

.branch-tree-summary strong {
  overflow: hidden;
  color: var(--ink-strong);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.branch-tree-summary dl {
  display: flex;
  flex: 0 0 auto;
  gap: 18px;
  margin: 0;
}

.branch-tree-summary dl div {
  display: grid;
  justify-items: end;
}

.branch-tree-summary dt {
  color: var(--ink-strong);
  font-size: 17px;
  font-weight: 700;
}

.branch-tree-summary dd {
  margin: 0;
}

.branch-tree-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 0 18px 12px;
  border-bottom: 1px solid var(--border-soft);
}

.branch-tree-legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--muted-2);
  font-size: 10px;
}

.branch-tree-legend i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}

.branch-tree-scroll {
  min-height: 360px;
  overflow: auto;
  overscroll-behavior: contain;
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--text) 4%, transparent) 1px, transparent 1px),
    linear-gradient(color-mix(in srgb, var(--text) 4%, transparent) 1px, transparent 1px),
    var(--panel-subtle);
  background-size: 24px 24px;
}

.branch-tree-canvas {
  position: relative;
  min-height: 100%;
}

.branch-tree-lines {
  position: absolute;
  inset: 0;
  overflow: visible;
  pointer-events: none;
}

.branch-edge,
.branch-mainline-path {
  fill: none;
  stroke: var(--border-2);
  stroke-linecap: round;
  stroke-width: 2;
}

.branch-mainline-path {
  stroke: color-mix(in srgb, var(--text) 24%, var(--border));
  stroke-dasharray: 3 5;
}

.branch-mainline-label {
  position: absolute;
  top: 12px;
  left: 18px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--muted-2);
  font-size: 10px;
  font-weight: 650;
}

.branch-anchor-node {
  position: absolute;
  left: 76px;
  display: grid;
  width: 54px;
  height: 30px;
  grid-template-columns: 38px 16px;
  align-items: center;
  color: var(--muted-2);
  font-size: 10px;
  text-align: right;
}

.branch-anchor-node i {
  justify-self: end;
  width: 9px;
  height: 9px;
  border: 2px solid var(--panel-subtle);
  border-radius: 50%;
  background: var(--ink-strong);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--text) 20%, transparent);
}

.branch-tree-node {
  position: absolute;
  display: grid;
  width: 184px;
  height: 62px;
  align-content: center;
  gap: 3px;
  padding: 8px 11px 8px 14px;
  overflow: hidden;
  border: 1px solid var(--border-2);
  border-left: 3px solid currentColor;
  border-radius: 7px;
  background: color-mix(in srgb, var(--panel) 96%, currentColor);
  box-shadow: 0 3px 10px color-mix(in srgb, #000 7%, transparent);
  color: var(--blue);
  cursor: pointer;
  text-align: left;
  transition: border-color 140ms ease, box-shadow 140ms ease, transform 140ms ease;
}

.branch-tree-node:hover,
.branch-tree-node:focus-visible {
  z-index: 2;
  box-shadow: 0 7px 18px color-mix(in srgb, #000 13%, transparent);
  outline: none;
  transform: translateY(-2px);
}

.branch-tree-node.selected {
  z-index: 2;
  border-color: currentColor;
  box-shadow: 0 0 0 2px color-mix(in srgb, currentColor 18%, transparent), 0 7px 18px color-mix(in srgb, #000 11%, transparent);
}

.branch-node-kind {
  color: currentColor;
  font-size: 9px;
  font-weight: 700;
}

.branch-tree-node strong {
  overflow: hidden;
  color: var(--ink-strong);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.branch-tree-node small {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: var(--muted-2);
  font-size: 9px;
}

.branch-tree-node b {
  color: inherit;
  font-weight: 500;
}

.tone-choice { color: #3776d4; }
.tone-relationship { color: #c45378; }
.tone-clue { color: #b27616; }
.tone-free { color: #448a73; }

.branch-edge.tone-choice { stroke: #6591d2; }
.branch-edge.tone-relationship { stroke: #cf7895; }
.branch-edge.tone-clue { stroke: #c49a53; }
.branch-edge.tone-free { stroke: #6a9d8c; }

.branch-tree-empty {
  display: grid;
  min-height: 360px;
  place-content: center;
  justify-items: center;
  padding: 28px;
  background: var(--panel-subtle);
  text-align: center;
}

.branch-tree-empty > span {
  display: grid;
  width: 44px;
  height: 44px;
  margin-bottom: 12px;
  place-items: center;
  border: 1px solid var(--border-2);
  border-radius: 8px;
  color: var(--blue);
}

.branch-tree-empty strong {
  color: var(--ink-strong);
  font-size: 14px;
}

.branch-tree-empty p {
  max-width: 320px;
  margin: 6px 0 16px;
  color: var(--muted-2);
  font-size: 11px;
  line-height: 1.6;
}

.branch-tree-empty button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 12px;
  border: 1px solid var(--blue);
  border-radius: 6px;
  background: var(--blue);
  color: #fff;
  cursor: pointer;
  font-size: 12px;
  font-weight: 650;
}

@media (max-width: 720px) {
  .branch-tree-summary {
    padding: 13px 14px 9px;
  }

  .branch-tree-summary dl {
    gap: 10px;
  }

  .branch-tree-summary dl div:first-child {
    display: none;
  }

  .branch-tree-legend {
    gap: 9px;
    padding: 0 14px 10px;
  }

  .branch-tree-scroll,
  .branch-tree-empty {
    min-height: 330px;
  }
}
</style>
