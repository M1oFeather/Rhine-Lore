<script setup lang="ts">
import GameIcon from "./GameIcon.vue";

export type ReaderTocItem = {
  id: string;
  title: string;
  meta: string;
};

export type ReaderSearchItem = {
  id: string;
  chapterId: string;
  title: string;
  snippet: string;
  matches: number;
};

export type ReaderBookmarkItem = {
  id: string;
  source: "novel" | "evolution" | "shelf";
  workId: string;
  chapterId: string;
  title: string;
  excerpt: string;
  progress: number;
  createdAt: string;
};

const props = defineProps<{
  title: string;
  toc: ReaderTocItem[];
  currentChapterId: string;
  query: string;
  results: ReaderSearchItem[];
  searching: boolean;
  bookmarks: ReaderBookmarkItem[];
}>();

const activeTab = defineModel<"toc" | "search" | "bookmarks">("activeTab", {required: true});

const emit = defineEmits<{
  "update:query": [value: string];
  search: [];
  selectChapter: [id: string];
  openResult: [item: ReaderSearchItem];
  openBookmark: [item: ReaderBookmarkItem];
  removeBookmark: [id: string];
}>();
</script>

<template>
  <div class="reader-navigator">
    <div class="reader-nav-book">
      <span class="reader-nav-book-icon"><GameIcon name="book-open" :size="22" /></span>
      <div>
        <small>正在阅读</small>
        <strong>{{ title }}</strong>
      </div>
    </div>

    <div class="reader-nav-tabs" role="tablist" aria-label="阅读导航">
      <button type="button" :class="{active: activeTab === 'toc'}" @click="activeTab = 'toc'">
        <GameIcon name="list" :size="17" />
        <span>目录</span>
        <b>{{ toc.length }}</b>
      </button>
      <button type="button" :class="{active: activeTab === 'search'}" @click="activeTab = 'search'">
        <GameIcon name="search" :size="17" />
        <span>搜索</span>
      </button>
      <button type="button" :class="{active: activeTab === 'bookmarks'}" @click="activeTab = 'bookmarks'">
        <GameIcon name="bookmark" :size="17" />
        <span>书签</span>
        <b>{{ bookmarks.length }}</b>
      </button>
    </div>

    <div v-if="activeTab === 'toc'" class="reader-nav-list">
      <button
        v-for="item in toc"
        :key="item.id"
        type="button"
        class="reader-nav-row"
        :class="{active: currentChapterId === item.id}"
        @click="emit('selectChapter', item.id)"
      >
        <span class="reader-nav-row-marker" />
        <span class="reader-nav-row-copy">
          <strong>{{ item.title }}</strong>
          <small>{{ item.meta }}</small>
        </span>
      </button>
      <div v-if="toc.length === 0" class="reader-nav-empty">还没有可阅读的章节</div>
    </div>

    <div v-else-if="activeTab === 'search'" class="reader-search-panel">
      <div class="reader-search-input">
        <el-input
          :model-value="props.query"
          clearable
          placeholder="搜索全书内容"
          @update:model-value="emit('update:query', String($event))"
          @keydown.enter="emit('search')"
        />
        <el-button type="primary" :loading="searching" @click="emit('search')">
          <GameIcon name="search" :size="16" />
          搜索
        </el-button>
      </div>
      <p v-if="query && !searching" class="reader-search-summary">
        找到 {{ results.reduce((total, item) => total + item.matches, 0) }} 处匹配
      </p>
      <div class="reader-nav-list search-results">
        <button
          v-for="item in results"
          :key="item.id"
          type="button"
          class="reader-search-result"
          @click="emit('openResult', item)"
        >
          <span>
            <strong>{{ item.title }}</strong>
            <b>{{ item.matches }} 处</b>
          </span>
          <small>{{ item.snippet }}</small>
        </button>
        <div v-if="query && !searching && results.length === 0" class="reader-nav-empty">
          没有找到“{{ query }}”
        </div>
        <div v-if="!query" class="reader-nav-empty">输入人物、地点或情节关键词</div>
      </div>
    </div>

    <div v-else class="reader-nav-list bookmark-list">
      <article v-for="item in bookmarks" :key="item.id" class="reader-bookmark-row">
        <button type="button" @click="emit('openBookmark', item)">
          <span>
            <strong>{{ item.title }}</strong>
            <b>{{ Math.round(item.progress) }}%</b>
          </span>
          <small>{{ item.excerpt || "此处没有文字预览" }}</small>
          <time>{{ item.createdAt }}</time>
        </button>
        <button type="button" class="reader-bookmark-remove" aria-label="删除书签" @click="emit('removeBookmark', item.id)">
          <GameIcon name="close" :size="16" />
        </button>
      </article>
      <div v-if="bookmarks.length === 0" class="reader-nav-empty">
        在阅读工具栏点击书签按钮，即可保存当前章节和进度
      </div>
    </div>
  </div>
</template>
