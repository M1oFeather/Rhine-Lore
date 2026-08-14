<script setup lang="ts">
import {computed} from "vue";

import GameIcon from "./GameIcon.vue";

const props = withDefaults(defineProps<{showPageMode?: boolean}>(), {showPageMode: true});

const pageMode = defineModel<"scroll" | "page">("pageMode", {required: true});
const theme = defineModel<"day" | "sepia" | "night">("theme", {required: true});
const fontFamily = defineModel<"serif" | "sans" | "system">("fontFamily", {required: true});
const fontSize = defineModel<number>("fontSize", {required: true});
const lineHeight = defineModel<number>("lineHeight", {required: true});
const paragraphSpacing = defineModel<number>("paragraphSpacing", {required: true});
const measure = defineModel<number>("measure", {required: true});
const brightness = defineModel<number>("brightness", {required: true});
const justify = defineModel<boolean>("justify", {required: true});
const indent = defineModel<boolean>("indent", {required: true});
const autoAdvance = defineModel<boolean>("autoAdvance", {required: true});

const emit = defineEmits<{change: []; reset: []}>();
const charactersPerLine = computed(() => Math.max(1, Math.round(measure.value / fontSize.value)));

function stepFont(delta: number): void {
  fontSize.value = Math.min(32, Math.max(14, fontSize.value + delta));
  emit("change");
}
</script>

<template>
  <div class="reader-settings-panel">
    <section v-if="props.showPageMode" class="reader-setting-section">
      <div class="reader-setting-heading">
        <span class="reader-setting-icon"><GameIcon name="book-open" :size="18" /></span>
        <div><strong>阅读方式</strong><small>选择连续滚动或逐页阅读</small></div>
      </div>
      <el-radio-group v-model="pageMode" class="reader-setting-segment" @change="emit('change')">
        <el-radio-button value="scroll">滚动</el-radio-button>
        <el-radio-button value="page">翻页</el-radio-button>
      </el-radio-group>
    </section>

    <section class="reader-setting-section">
      <div class="reader-setting-heading">
        <span class="reader-setting-icon"><GameIcon name="sun" :size="18" /></span>
        <div><strong>阅读主题</strong><small>主题与亮度只影响阅读页面</small></div>
      </div>
      <div class="reader-theme-options">
        <button type="button" class="theme-day" :class="{active: theme === 'day'}" @click="theme = 'day'; emit('change')">昼</button>
        <button type="button" class="theme-sepia" :class="{active: theme === 'sepia'}" @click="theme = 'sepia'; emit('change')">纸</button>
        <button type="button" class="theme-night" :class="{active: theme === 'night'}" @click="theme = 'night'; emit('change')">夜</button>
      </div>
      <div class="reader-setting-slider">
        <span>亮度</span>
        <el-slider v-model="brightness" :min="55" :max="110" :step="5" @change="emit('change')" />
        <b>{{ brightness }}%</b>
      </div>
    </section>

    <section class="reader-setting-section">
      <div class="reader-setting-heading">
        <span class="reader-setting-icon"><GameIcon name="type" :size="18" /></span>
        <div><strong>字体与字号</strong><small>正文默认使用适合长时间阅读的衬线字体</small></div>
      </div>
      <el-radio-group v-model="fontFamily" class="reader-setting-segment" @change="emit('change')">
        <el-radio-button value="serif">宋体</el-radio-button>
        <el-radio-button value="sans">黑体</el-radio-button>
        <el-radio-button value="system">系统</el-radio-button>
      </el-radio-group>
      <div class="reader-font-stepper">
        <button type="button" aria-label="减小字号" @click="stepFont(-1)">A−</button>
        <strong>{{ fontSize }} px</strong>
        <button type="button" aria-label="增大字号" @click="stepFont(1)">A+</button>
      </div>
    </section>

    <section class="reader-setting-section compact-grid">
      <div class="reader-setting-control">
        <label>行距</label>
        <el-slider v-model="lineHeight" :min="1.4" :max="2.6" :step="0.1" @change="emit('change')" />
        <b>{{ lineHeight.toFixed(1) }}</b>
      </div>
      <div class="reader-setting-control">
        <label>段距</label>
        <el-slider v-model="paragraphSpacing" :min="0.6" :max="2.2" :step="0.1" @change="emit('change')" />
        <b>{{ paragraphSpacing.toFixed(1) }}</b>
      </div>
      <div class="reader-setting-control">
        <label>正文宽度</label>
        <el-slider v-model="measure" :min="520" :max="920" :step="20" @change="emit('change')" />
        <b>约 {{ charactersPerLine }} 字/行</b>
      </div>
    </section>

    <section class="reader-setting-section reader-setting-toggles">
      <label><span><strong>两端对齐</strong><small>让中文段落左右边缘整齐</small></span><el-switch v-model="justify" @change="emit('change')" /></label>
      <label><span><strong>段首缩进</strong><small>每段开头缩进两个汉字</small></span><el-switch v-model="indent" @change="emit('change')" /></label>
      <label><span><strong>自动进入下一章</strong><small>滚动到章末后继续下一章</small></span><el-switch v-model="autoAdvance" @change="emit('change')" /></label>
    </section>

    <el-button class="reader-reset-button" @click="emit('reset')">恢复默认排版</el-button>
  </div>
</template>
