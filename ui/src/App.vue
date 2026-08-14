<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import { ElMessageBox } from "element-plus/es/components/message-box/index.mjs";

import {
  type ApiRecord,
  type AgentToolAction,
  type BookAnalysis,
  type BookAnalysisMode,
  type BookAnalysisPlan,
  type BookAnalysisStatus,
  type BookBranch,
  type BookBranchPath,
  type BookChapter,
  type BookChapterMeta,
  type BookDetail,
  type BookMeta,
  type Chapter,
  type CharacterCard,
  type CharacterRelationship,
  type CreativeMessage,
  type EvolutionCastMember,
  type EvolutionState,
  type EvolutionView,
  type LanInfo,
  type LlmChatMessage,
  type LoreItem,
  type KnowledgeExtractCandidate,
  type ManuscriptIssue,
  type ProjectBackupRow,
  type StoryMap,
  type StoryMapEdge,
  type StoryMapNode,
  type StoryProject,
  type VaultRuntimeStatus,
  type VaultWebStatus,
  type VersionRecord,
  type WorkspaceRecord,
  type WorldCard,
  advanceEvolution,
  advanceEvolutionChapter,
  addEvolutionCharacter,
  approveStaging,
  aiWriteBook,
  buildContextBundle,
  cancelBookAnalysis,
  connectVaultRuntime,
  convertBookToProject,
  createBookBranch,
  deleteBookBranch,
  createManualProposal,
  deleteBook,
  executeAgentTool,
  extractConversationKnowledge,
  exportBackupZip,
  fakeCreativeAnswer,
  generateEvolutionProseApi,
  generateKnowledgeDocument,
  getEvolutionState,
  getBookAnalysisStatus,
  getLanInfo,
  getLlmServerConfig,
  getBook,
  getBookBranchPath,
  getBookChapter,
  getServerBase,
  getServerProject,
  getVaultRuntimeStatus,
  getVaultWebStatus,
  guideEvolution,
  health,
  installVaultWeb,
  importBook,
  importBackupZip,
  listBooks,
  listBookBranches,
  llmServerChat,
  llmServerChatStream,
  llmServerPing,
  listNodes,
  listProposals,
  listStaging,
  listWorkspaces,
  listProjectBackups,
  listServerProjects,
  listVersions,
  commitVersion,
  restoreVersion,
  registerWorkspace,
  rejectProposal,
  regenerateEvolutionChapter,
  resetEvolutionRun,
  restoreProjectBackup,
  saveBookChapter,
  saveLlmServerConfig,
  saveServerProject,
  setServerBase,
  setWorkspaceId,
  pingServerBase,
  previewBookAnalysis,
  stageProposal,
  startEvolutionRun,
  startBookAnalysis,
  startVaultRuntime,
  stopVaultRuntime,
  updateProposalNode,
  workspaceId,
} from "./api";
import GameIcon from "./components/GameIcon.vue";
import BranchTree from "./components/BranchTree.vue";
import EmptyState from "./components/EmptyState.vue";
import HomeIllustration from "./components/HomeIllustration.vue";
import ReaderNavigator, {
  type ReaderBookmarkItem,
  type ReaderSearchItem,
  type ReaderTocItem,
} from "./components/ReaderNavigator.vue";
import ReaderSettingsPanel from "./components/ReaderSettingsPanel.vue";
import type { GameIconName } from "./icons/gameIconPack";
import {
  createStoryProjectFromTemplate,
  getStoryTemplate,
  storyTemplates,
  type StoryTemplateId,
} from "./storyTemplates";
import {
  type DecodedTextFile,
  type TextEncodingChoice,
  decodeTextBytes,
  detectAndDecodeText,
  textEncodingLabel,
  textEncodingOptions,
} from "./textEncoding";
import rhineLoreMark from "./assets/rhine-lore-mark.svg";

type Activity = "studio" | "story" | "world" | "characters" | "chat" | "novel" | "context" | "evolution" | "read" | "shelf" | "map" | "settings";
type WorkMode = "write" | "advanced";
type BackendStatus = "checking" | "online" | "offline";
type CreateDestination = "novel" | "chat";
type ReaderSource = "novel" | "evolution" | "shelf";
type ReaderPageParagraph = {
  text: string;
  continuation: boolean;
};
type ReaderPage =
  | {kind: "title"}
  | {kind: "content"; paragraphs: ReaderPageParagraph[]};
type ReaderPosition = {
  chapterId: string;
  progress: number;
  pageIndex: number;
};
type BranchSource = "shelf" | "project";
type BranchKind = BookBranch["kind"];
type BranchDraftContext = {
  source: BranchSource;
  chapterId: string;
  chapterTitle: string;
  offset: number;
  progress: number;
  anchor: string;
  selectedText: string;
  parentBranchId: string;
  origin: "selection" | "paragraph" | "position" | "cursor" | "branch";
};
type EvolutionChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};
type KnowledgeCandidateDraft = KnowledgeExtractCandidate & {
  selected: boolean;
  tagsText: string;
};
type KnowledgeReviewStage = "draft" | "ready" | "library";
type KnowledgeConflictMode = "coexist" | "merge" | "replace";
type KnowledgeReviewItem = {
  key: string;
  stage: KnowledgeReviewStage;
  proposalId?: string;
  temporaryId?: string;
  entryId?: string;
  nodeId?: string;
  revision?: number;
  baseRevision?: number;
  title: string;
  nodeType: string;
  content: string;
  authority: string;
  tags: string[];
  createdAt: string;
};
type KnowledgeSourceInfo = {
  kind: string;
  project: string;
  projectId: string;
  chapter: string;
  chapterId: string;
  messageIds: string[];
  excerpts: string[];
  metadata: string;
};
type KnowledgeSimilarity = {
  item: KnowledgeReviewItem;
  score: number;
  reason: string;
};
type KnowledgeSourceTarget = {
  project: StoryProject | null;
  chapter: Chapter | null;
  messageId: string;
};
type KnowledgeReviewForm = {
  title: string;
  nodeType: string;
  body: string;
  authority: string;
  tagsText: string;
};
type RevisionResult = {
  revisions: {
    chapter_id: string;
    chapter_title?: string;
    revised_text: string;
  }[];
  evaluation: ManuscriptIssue[];
};

const projectKey = "rhine-lore-projects";
const activeProjectKey = "rhine-lore-active-project";
const activeChapterKey = "rhine-lore-active-chapter";
const projectDraftIndexKey = "rhine-lore-pending-project-drafts";
const projectDraftPrefix = "rhine-lore-project-draft:";
const primaryActivityIds: Activity[] = ["studio", "chat", "novel", "context", "evolution", "map"];
const storySetupActivities: Activity[] = ["story", "world", "characters"];
const genreOptions = ["奇幻", "科幻", "悬疑", "都市", "历史", "爱情", "轻小说", "未分类"];
const characterRoles = ["主角", "重要配角", "配角", "反派", "盟友", "导师", "恋人"];
const characterStatusOptions = ["正常", "受伤", "失踪", "被囚禁", "死亡", "未知"];
const worldTypes = ["地点", "势力", "规则", "历史", "物品", "传说", "其他"];
const guidancePresets = ["制造一场冲突", "推进感情线", "回收一个伏笔", "引入新角色", "让局势紧张起来", "给一段平静日常"];
const worldTagPresets: Record<string, string[]> = {
  地点: ["港口", "校园", "森林", "废墟", "水域", "城郊"],
  势力: ["家族", "商会", "教会", "王国", "公会", "组织"],
  规则: ["禁令", "魔法", "登记", "契约", "禁忌"],
  历史: ["战争", "灾变", "旧日", "传说"],
  物品: ["信物", "武器", "古籍", "钥匙"],
  传说: ["龙族", "神明", "诅咒", "预言"],
  其他: ["秘密", "日常", "线索", "伏笔"],
};
const characterTraitPresets = ["谨慎", "毒舌", "重情义", "社恐", "开朗", "固执", "温柔", "腹黑", "胆大", "多疑", "理性", "浪漫"];
const evolutionStartPresets = [
  {label: "平静", chaos: 10, branch: 15},
  {label: "标准", chaos: 45, branch: 35},
  {label: "混乱", chaos: 85, branch: 60},
];
const evolutionChatStarters = ["总结现在的局势", "下一步制造一场冲突", "推进感情线", "回收一个伏笔", "建议一个新角色"];
const chapterTurnsOptions = [2, 3, 4, 6, 8];
const writingStylePresets = ["平实细腻", "轻快活泼", "冷峻悬疑", "华丽诗意", "幽默吐槽"];
const WRITING_QUALITY_GUIDE =
  "写作质量要求：1) 用具体的感官细节（视觉、听觉、触觉、气味）代替空泛形容；" +
  "2) 心理描写要有层次，避免直白贴标签；" +
  "3) 对话自然，符合人物身份与说话风格；" +
  "4) 长短句交替，控制叙事节奏；" +
  "5) 段落留白，避免流水账；" +
  "6) 避免 AI 腔（慎用“仿佛、不禁、然而、不禁让人”等套话）；" +
  "7) 与已知设定、人物声音、时间线严格一致，不发明未发生的情节。";

const activities: {id: Activity; label: string; icon: GameIconName; description: string}[] = [
  {id: "chat", label: "AI 对话", icon: "message", description: "续写、修订、导入的创作助手"},
  {id: "studio", label: "工作台", icon: "home", description: "选择故事和开始写作"},
  {id: "story", label: "故事档案", icon: "file-text", description: "名称、类型和概要"},
  {id: "world", label: "世界观", icon: "globe", description: "规则、地点和历史"},
  {id: "characters", label: "角色", icon: "users", description: "人物、动机和关系"},
  {id: "novel", label: "正文", icon: "pen", description: "阅读和编辑章节"},
  {id: "context", label: "资料库", icon: "database", description: "查找设定和参考资料"},
  {id: "evolution", label: "演化", icon: "sparkles", description: "沙盘观演与有限视角小说"},
  {id: "read", label: "小说阅读", icon: "book-open", description: "像追更一样读演化正文"},
  {id: "shelf", label: "书架", icon: "library", description: "导入并阅读 TXT 长篇小说"},
  {id: "map", label: "地图", icon: "map", description: "故事空间与地点连接"},
  {id: "settings", label: "设置", icon: "settings", description: "连接、高级和维护"},
];

type SidebarMode = "workbench" | "reader";
const sidebarMode = ref<SidebarMode>((localStorage.getItem("rhine-lore-sidebar-mode") as SidebarMode) || "workbench");
const workbenchActivities = activities.filter((item) => !["read", "shelf"].includes(item.id));
const readerActivities = activities.filter((item) =>
  ["novel", "read", "shelf", "context", "settings"].includes(item.id),
);
const visibleActivityGroups = computed(() => {
  const groups: {label: string; ids: Activity[]}[] = sidebarMode.value === "reader"
    ? [
        {label: "阅读", ids: ["novel", "read", "shelf"]},
        {label: "资料", ids: ["context"]},
        {label: "系统", ids: ["settings"]},
      ]
    : [
        {label: "创作", ids: ["chat", "studio", "novel"]},
        {label: "故事资料", ids: ["story", "world", "characters", "map"]},
        {label: "智能工具", ids: ["context", "evolution"]},
        {label: "系统", ids: ["settings"]},
      ];

  return groups.map((group) => ({
    label: group.label,
    items: group.ids.flatMap((id) => {
      const item = activities.find((activityItem) => activityItem.id === id);
      return item ? [item] : [];
    }),
  }));
});

const activity = ref<Activity>("studio");
const sidebarCollapsed = ref(localStorage.getItem("rhine-lore-sidebar-collapsed") === "1");
const mobileNavOpen = ref(false);
type NativeBackWindow = Window & {rhineLoreHandleBack?: () => boolean};
const contentMainRef = ref<HTMLElement | null>(null);
const mobileMenuBtnRef = ref<HTMLButtonElement | null>(null);
const mobileCloseBtnRef = ref<HTMLButtonElement | null>(null);
const showAllProjects = ref(false);
const storyStyleOpen = ref(false);
const readingProgress = ref(0);
const readerNavigatorVisible = ref(false);
const readerNavigatorTab = ref<"toc" | "search" | "bookmarks">("toc");
const readerSearchQuery = ref("");
const readerSearchResults = ref<ReaderSearchItem[]>([]);
const readerSearching = ref(false);
const readerSettingsVisible = ref(false);
const novelVersionsVisible = ref(false);
const shelfVersionsVisible = ref(false);
const novelVersionMessage = ref("");
const shelfVersionMessage = ref("");
const novelVersions = ref<VersionRecord[]>([]);
const shelfVersions = ref<VersionRecord[]>([]);
const versionBusy = ref("");
const pendingRestoreVersion = ref<{
  kind: "project" | "book";
  entity_id: string;
  snapshot_id: string;
  message: string;
} | null>(null);
const notice = ref("就绪");
const busyAction = ref("");
const runState = ref<Record<string, unknown> | null>(null);
const workMode = ref<WorkMode>("write");
const backendStatus = ref<BackendStatus>("checking");
const vaultStatus = ref<VaultRuntimeStatus | null>(null);
const vaultWebStatus = ref<VaultWebStatus | null>(null);
const vaultPath = ref(localStorage.getItem("rhine-lore-vault-path") || "");
const vaultHost = ref(localStorage.getItem("rhine-lore-vault-host") || "127.0.0.1");
const vaultPort = ref(Number(localStorage.getItem("rhine-lore-vault-port") || "8795"));
if (localStorage.getItem("rhine-lore-vault-port") === "8765" && !localStorage.getItem("rhine-lore-external-vault-url")) {
  localStorage.setItem("rhine-lore-vault-port", "8795");
  vaultPort.value = 8795;
}
const vaultDatabasePath = ref(localStorage.getItem("rhine-lore-vault-database-path") || "");
const vaultPythonPath = ref(localStorage.getItem("rhine-lore-vault-python-path") || "");
const externalVaultUrl = ref(localStorage.getItem("rhine-lore-external-vault-url") || "");
const activeProjectId = ref(localStorage.getItem(activeProjectKey) || "");
const activeChapterId = ref(localStorage.getItem(activeChapterKey) || "");
const projectImportInput = ref<HTMLInputElement | null>(null);
const createDialogVisible = ref(false);
const newProjectTemplate = ref<StoryTemplateId>("blank");
const newProjectName = ref("");
const newProjectGenre = ref("");
const newProjectIdea = ref("");
const selectedStoryTemplate = computed(() => getStoryTemplate(newProjectTemplate.value));
const projects = ref<StoryProject[]>([]);
const workspaces = ref<WorkspaceRecord[]>([]);
const selectedWorkspaceId = ref(workspaceId);
const newWorkspaceId = ref("story-workspace");
const newWorkspaceDisplayName = ref("Story Workspace");
const contextQuery = ref("story rules and character constraints");
const manualKnowledgeTitle = ref("");
const manualKnowledgeContent = ref("");
const manualKnowledgeTags = ref("lore, draft");
const profileId = ref("semantic-knowledge-base");
const resultLimit = ref(8);
const nodes = ref<ApiRecord[]>([]);
const selectedKnowledgeIds = ref<string[]>([]);
const proposals = ref<ApiRecord[]>([]);
const stagingEntries = ref<ApiRecord[]>([]);
const knowledgePageTab = ref<"review" | "library" | "tools">("review");
const knowledgeQueueTab = ref<"draft" | "ready">("draft");
const selectedKnowledgeDraftKeys = ref<string[]>([]);
const selectedKnowledgeReadyIds = ref<string[]>([]);
const knowledgeReviewVisible = ref(false);
const activeKnowledgeReviewKey = ref("");
const knowledgeReviewForm = ref<KnowledgeReviewForm>({
  title: "",
  nodeType: "Note",
  body: "",
  authority: "experimental",
  tagsText: "",
});
const knowledgeConflictMode = ref<KnowledgeConflictMode>("coexist");
const knowledgeConflictTargetKey = ref("");
const knowledgeConflictModes = ref<Record<string, KnowledgeConflictMode>>({});
const knowledgeConflictTargets = ref<Record<string, string>>({});
const knowledgeCoexistNodeIds = ref<Record<string, string>>({});
const highlightedKnowledgeMessageId = ref("");
const chatInput = ref("");
const chatThinking = ref(false);
const streamingChatText = ref("");
const chatThreadRef = ref<HTMLElement | null>(null);
const chatSidebarOpen = ref(window.innerWidth > 720);
const chatSideSections = ref({chapter: true, refs: true, issues: true});
const chatMoreOpen = ref(false);
const knowledgeExtractVisible = ref(false);
const knowledgeExtractStep = ref<"select" | "review">("select");
const knowledgeSelectedMessageIds = ref<string[]>([]);
const knowledgeCandidates = ref<KnowledgeCandidateDraft[]>([]);
const knowledgeExtractOffline = ref(false);
const knowledgeExtractNote = ref("");
const pendingAgentAction = ref<AgentToolAction | null>(null);
const chatAttachment = ref<{name: string; kind: "txt" | "project" | "knowledge"; text: string} | null>(null);
const chatAttachInput = ref<HTMLInputElement | null>(null);
const chatMode = ref<"chat" | "adjust">("chat");
const adjustInput = ref("");
const revisionBusy = ref(false);
const revisionPreview = ref<RevisionResult | null>(null);
const readerMode = ref<"read" | "edit">("edit");
function storedNumber(key: string, fallback: number, min: number, max: number): number {
  const value = Number(localStorage.getItem(key) || fallback);
  return Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : fallback;
}

function joinWrappedReaderLines(lines: string[]): string {
  return lines.reduce((content, line) => {
    if (!content) return line;
    const previous = content.at(-1) ?? "";
    const next = line.at(0) ?? "";
    const needsSpace = /[A-Za-z0-9,.;:!?%)\]]/.test(previous) && /[A-Za-z0-9([{"']/.test(next);
    return `${content}${needsSpace ? " " : ""}${line}`;
  }, "");
}

function splitReaderParagraphs(content: string): string[] {
  const normalized = content.replace(/^\uFEFF/, "").replace(/\r\n?/g, "\n").trim();
  if (!normalized) return [];

  const paragraphs: string[] = [];
  const blocks = normalized.split(/\n[\t \u3000]*\n+/);
  const sentenceEnding = /[。！？!?…][”’」』）】〕〉》]?$/;
  const heading = /^第[\d零〇一二三四五六七八九十百千万两]+[章节卷回部篇集](?:\s|$)/;

  const appendLines = (sourceLines: string[]) => {
    const lines = sourceLines.map((line) => line.trim()).filter(Boolean);
    if (lines.length <= 1) {
      if (lines[0]) paragraphs.push(lines[0]);
      return;
    }

    const lengths = lines.map((line) => Array.from(line).length).sort((a, b) => a - b);
    const median = lengths[Math.floor(lengths.length / 2)] ?? 0;
    const sentenceRatio = lines.filter((line) => sentenceEnding.test(line)).length / lines.length;
    const nearWrapRatio = lines.length > 1
      ? lines.slice(0, -1).filter((line) => Array.from(line).length >= Math.max(32, median * 0.82)).length / (lines.length - 1)
      : 0;
    const looksSoftWrapped = median >= 32 && sentenceRatio < 0.6 && nearWrapRatio >= 0.66;

    if (looksSoftWrapped) {
      paragraphs.push(joinWrappedReaderLines(lines));
    } else {
      paragraphs.push(...lines);
    }
  };

  for (const block of blocks) {
    const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
    let pending: string[] = [];
    for (const line of lines) {
      if (line.length <= 40 && heading.test(line)) {
        appendLines(pending);
        pending = [];
        paragraphs.push(line);
      } else {
        pending.push(line);
      }
    }
    appendLines(pending);
  }
  return paragraphs;
}

function isReaderVolumeTitle(title: string): boolean {
  return /^(?:第\s*[\d零〇一二三四五六七八九十百千万两]+\s*[卷部篇集]|卷[\d零〇一二三四五六七八九十百千万两首]|[上中下终序]卷)/i.test(title.trim());
}

const readerFontSize = ref(storedNumber("rhine-lore-reader-font-size", 18, 14, 32));
const readerLineHeight = ref(storedNumber("rhine-lore-reader-line-height", 1.9, 1.4, 2.6));
const readerTheme = ref<"day" | "sepia" | "night">(
  (localStorage.getItem("rhine-lore-reader-theme") as "day" | "sepia" | "night") || "day",
);
const readerParagraphSpacing = ref(storedNumber("rhine-lore-reader-paragraph-spacing", 1.1, 0.6, 2.2));
const readerJustify = ref(localStorage.getItem("rhine-lore-reader-justify") !== "0");
const readerIndent = ref(localStorage.getItem("rhine-lore-reader-indent") !== "0");
const readerAutoAdvance = ref(localStorage.getItem("rhine-lore-reader-auto-advance") !== "0");
const readerFontFamily = ref<"serif" | "sans" | "system">(
  (localStorage.getItem("rhine-lore-reader-font-family") as "serif" | "sans" | "system") || "serif",
);
const readerBrightness = ref(storedNumber("rhine-lore-reader-brightness", 100, 55, 110));
const readerMeasure = ref(storedNumber("rhine-lore-reader-measure", 700, 520, 920));
const readerPageMode = ref<"scroll" | "page">(
  (localStorage.getItem("rhine-lore-reader-mode") as "scroll" | "page") || "scroll",
);
const readerPages = ref<ReaderPage[]>([]);
const readerPageIndex = ref(0);
const readerPageAreaRef = ref<HTMLElement | null>(null);
const readerOverlayPageAreaRef = ref<HTMLElement | null>(null);
const readerOverlayOpen = ref(false);
const readerChromeVisible = ref(true);
const readerFullscreenActive = ref(false);
const userScrolledReading = ref(false);
const lastReaderAutoAdvance = ref(0);
const shelfBooks = ref<BookMeta[]>([]);
const shelfBookId = ref("");
const shelfBook = ref<BookDetail | null>(null);
const shelfChapter = ref<BookChapter | null>(null);
const shelfChapterIndex = ref(-1);
const readerBookmarks = ref<ReaderBookmarkItem[]>(loadReaderBookmarks());
let readerPositionTimer: number | undefined;
let readerBoundScrollElement: HTMLElement | null = null;
let readerResizeTimer: number | undefined;
let shelfAnalysisPollTimer: number | undefined;
const shelfGuidance = ref("");
const shelfAiMode = ref<"continue" | "rewrite" | "expand">("continue");
const shelfAiResult = ref("");
const shelfAiBusy = ref(false);
const shelfAnalysis = ref<BookAnalysis | null>(null);
const shelfAnalyzeBusy = ref(false);
const shelfAnalysisStatus = ref<BookAnalysisStatus | null>(null);
const shelfAnalysisMode = ref<BookAnalysisMode>(
  (localStorage.getItem("rhine-lore-analysis-mode") as BookAnalysisMode) || "smart",
);
const shelfAnalysisPlan = ref<BookAnalysisPlan | null>(null);
const shelfAnalysisAdvanced = ref(false);
const shelfAnalysisForce = ref(false);
const shelfAnalysisTab = ref("overview");
const pendingShelfProjectBranchId = ref<string | null>(null);
const shelfBranches = ref<BookBranch[]>([]);
const branchTreeVisible = ref(false);
const selectedShelfBranchId = ref("");
const selectedBranchPath = ref<BookBranchPath | null>(null);
const branchPathBusy = ref(false);
const branchPathVisible = ref(false);
const branchDialogVisible = ref(false);
const branchContext = ref<BranchDraftContext | null>(null);
const branchGuidance = ref("");
const branchKind = ref<BranchKind>("free");
const branchResult = ref("");
const branchRecord = ref<BookBranch | null>(null);
const branchBusy = ref(false);
const branchProjectBusy = ref(false);
const capturedBranchSelection = ref<BranchDraftContext | null>(null);
const shelfSaving = ref(false);
const shelfImportInput = ref<HTMLInputElement | null>(null);
const shelfImportVisible = ref(false);
const shelfImportBusy = ref(false);
const shelfImportAdvanced = ref(false);
const shelfImportName = ref("");
const shelfImportFileName = ref("");
const shelfImportFileSize = ref("");
const shelfImportEncoding = ref<TextEncodingChoice>("auto");
const shelfImportBytes = ref<Uint8Array | null>(null);
const shelfImportDetected = ref<DecodedTextFile | null>(null);
const shelfImportDecoded = ref<DecodedTextFile | null>(null);
const shelfImportError = ref("");
const settingsTab = ref("basic");
type ThemeMode = "light" | "dark" | "system";
const themeMode = ref<ThemeMode>((localStorage.getItem("rhine-lore-theme") as ThemeMode) || "system");
const systemDark = ref(false);
const serverBaseInput = ref(getServerBase());
const serverBaseCurrent = ref(getServerBase());
const serverBaseBusy = ref(false);
const serverBaseMessage = ref("");
const backupImportInput = ref<HTMLInputElement | null>(null);
const backupBusy = ref(false);
const backupMessage = ref("");
const saveNotice = ref("");
const lastSavedAt = ref("");
let saveNoticeTimer: number | undefined;
const evolutionView = ref<EvolutionView | null>(null);
const evolutionTab = ref<"sandbox" | "novel" | "chat">("sandbox");
const evolutionViewpoint = ref("");
const evolutionChaos = ref(45);
const evolutionBranchFrequency = ref(35);
const evolutionAutoResolve = ref(false);
const evolutionAutoPlay = ref(false);
const evolutionSpeed = ref(4);
const evolutionSeedInput = ref("");
const evolutionGuidance = ref("");
const evolutionStateTab = ref("arc");
const evolutionChapterIndex = ref(0);
const chapterGuidanceInput = ref("");
const chapterBusy = ref(false);
const evolutionChat = ref<EvolutionChatMessage[]>([]);
const evolutionChatInput = ref("");
const evolutionChatBusy = ref(false);
const evolutionChatStreaming = ref("");
const evolutionCharacterDialogVisible = ref(false);
const evolutionNewCharacter = ref({name: "", role: "配角", drive: "", secret: ""});
const ignoredCharacterPromptProjects = ref<string[]>([]);
const evolutionTimelineLimit = ref(30);
const worldEditVisible = ref(false);
const worldDraft = ref<WorldCard>({
  id: "",
  name: "",
  type: "地点",
  summary: "",
  details: "",
  significance: "",
  tags: "",
});
const worldEditIndex = ref(-1);
const characterEditVisible = ref(false);
const characterDraft = ref<CharacterCard | null>(null);
const characterEditIndex = ref(-1);
const mapSelectedNodeId = ref("");
const mapSelectedEdgeId = ref("");
const mapConnectMode = ref(false);
const mapPendingNodeId = ref("");
const mapZoom = ref(1);
const mapDragging = ref<{id: string; dx: number; dy: number} | null>(null);
const llmBaseUrl = ref("https://api.deepseek.com/v1");
const llmApiKey = ref("");
const llmModel = ref("deepseek-chat");
const llmPreset = ref("deepseek");
const llmConfigured = ref(false);
const llmMaskedKey = ref("");
const aiProse = ref("");
const aiProseBusy = ref(false);
const aiAutoProse = ref(localStorage.getItem("rhine-lore-ai-auto") !== "0");
const aiGenerating = ref(false);
const aiStatus = ref<"checking" | "ok" | "error" | "unset">("unset");
const aiStatusDetail = ref("");
const aiPanelOpen = ref(false);
let evolutionTimer: number | undefined;
let evolutionTurnRunning = false;
const projectBackupTimers = new Map<string, number>();
const projectDraftTimers = new Map<string, number>();
const pendingProjectBackups = new Map<string, StoryProject>();
const diskBackups = ref<ProjectBackupRow[]>([]);
const restoreDialogVisible = ref(false);
const restoreBusy = ref("");
const lanInfo = ref<LanInfo | null>(null);

const promptStarters = [
  "续写当前章节",
  "设计下一场冲突",
  "检查角色动机",
  "整理本章设定",
  "结合资料续写",
];
const knowledgeTypeOptions: {value: KnowledgeExtractCandidate["node_type"]; label: string}[] = [
  {value: "Character", label: "角色"},
  {value: "Location", label: "地点"},
  {value: "Rule", label: "规则"},
  {value: "Event", label: "事件"},
  {value: "Fact", label: "事实"},
  {value: "Foreshadowing", label: "伏笔"},
  {value: "Note", label: "资料"},
];

function loadReaderBookmarks(): ReaderBookmarkItem[] {
  try {
    const parsed = JSON.parse(localStorage.getItem("rhine-lore-reader-bookmarks") || "[]") as ReaderBookmarkItem[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

if (!projects.value.some((project) => project.id === activeProjectId.value) && projects.value.length > 0) {
  activeProjectId.value = projects.value[0].id;
}
const initialProject = projects.value.find((project) => project.id === activeProjectId.value);
if (initialProject && !initialProject.chapters.some((chapter) => chapter.id === activeChapterId.value)) {
  activeChapterId.value = initialProject.chapters[0]?.id ?? "";
}

const activeTabMeta = computed(() => {
  return activities.find((item) => item.id === activity.value) ?? activities[0];
});

const activeProject = computed(() => {
  return (
    projects.value.find((project) => project.id === activeProjectId.value) ??
    projects.value[0] ??
    createDefaultProject()
  );
});

const activeChapter = computed(() => {
  const project = activeProject.value;
  if (!project) {
    return null;
  }
  return project.chapters.find((chapter) => chapter.id === activeChapterId.value) ?? project.chapters[0] ?? null;
});

const stats = computed(() => [
  {label: "设定", value: activeProject.value?.world.length ?? 0, tone: "blue"},
  {label: "角色", value: activeProject.value?.characters.length ?? 0, tone: "green"},
  {label: "章节", value: activeProject.value?.chapters.length ?? 0, tone: "amber"},
  {label: "资料", value: nodes.value.length, tone: "gray"},
]);

const knowledgeDraftItems = computed<KnowledgeReviewItem[]>(() =>
  proposals.value.flatMap((proposal) => normalizeKnowledgeProposal(proposal)),
);
const knowledgeReadyItems = computed<KnowledgeReviewItem[]>(() =>
  stagingEntries.value
    .filter((entry) => !entry.status || String(entry.status) === "pending")
    .map((entry) => normalizeKnowledgeStaging(entry)),
);
const knowledgeLibraryItems = computed<KnowledgeReviewItem[]>(() =>
  nodes.value.map((node) => normalizeKnowledgeNode(node)),
);
const activeKnowledgeReviewItem = computed<KnowledgeReviewItem | null>(() => {
  const items = [...knowledgeDraftItems.value, ...knowledgeReadyItems.value];
  return items.find((item) => item.key === activeKnowledgeReviewKey.value) ?? null;
});
const activeKnowledgeSource = computed<KnowledgeSourceInfo>(() =>
  parseKnowledgeSource(activeKnowledgeReviewItem.value?.content ?? ""),
);
const activeKnowledgeSimilarities = computed<KnowledgeSimilarity[]>(() => {
  const active = activeKnowledgeReviewItem.value;
  return active ? knowledgeSimilarities(active) : [];
});
const activeKnowledgeConflictTarget = computed<KnowledgeReviewItem | null>(() =>
  knowledgeLibraryItems.value.find((item) => item.key === knowledgeConflictTargetKey.value) ?? null,
);
const activeKnowledgeRevisionTarget = computed<KnowledgeReviewItem | null>(() => {
  const nodeId = activeKnowledgeReviewItem.value?.nodeId;
  return nodeId
    ? knowledgeLibraryItems.value.find((item) => item.nodeId === nodeId) ?? null
    : null;
});
const activeKnowledgeSourceTarget = computed<KnowledgeSourceTarget>(() =>
  resolveKnowledgeSourceTarget(activeKnowledgeSource.value),
);

const knowledgePipelineStats = computed(() => [
  {label: "待整理", value: knowledgeDraftItems.value.length, tone: "amber"},
  {label: "待入库", value: knowledgeReadyItems.value.length, tone: "blue"},
  {label: "已入库", value: nodes.value.length, tone: "green"},
]);

const knowledgePipelineHint = computed(() => {
  if (knowledgeDraftItems.value.length > 0) {
    return `${knowledgeDraftItems.value.length} 条资料草稿等待整理`;
  }
  if (knowledgeReadyItems.value.length > 0) {
    return `${knowledgeReadyItems.value.length} 条待确认资料可以入库`;
  }
  if (nodes.value.length > 0) {
    return `已有 ${nodes.value.length} 条资料可用于对话参考`;
  }
  return "还没有资料，先从章节或对话保存一条草稿";
});

const chatReferenceNodes = computed(() => nodes.value.slice(0, 10));

const selectedKnowledgeNodes = computed(() => {
  const ids = new Set(selectedKnowledgeIds.value);
  return nodes.value.filter((node) => ids.has(recordId(node)));
});

const knowledgeExtractMessages = computed(() => activeProject.value.chat.slice(-40));
const knowledgeSelectedMessages = computed(() => {
  const selected = new Set(knowledgeSelectedMessageIds.value);
  return knowledgeExtractMessages.value.filter((message) => selected.has(message.id));
});
const knowledgeSelectedCandidateCount = computed(
  () => knowledgeCandidates.value.filter((candidate) => candidate.selected).length,
);


const agentImpactPreview = computed<{label: string; lines: string[]} | null>(() => {
  const action = pendingAgentAction.value;
  if (!action) {
    return null;
  }
  const args = action.args;
  const projectName = activeProject.value?.name || "当前项目";
  switch (action.tool) {
    case "create_project":
      return {
        label: "新建项目",
        lines: [
          `名称：${String(args.name || "未命名")}`,
          `类型：${String(args.genre || "未分类")}`,
          `概要：${String(args.summary || "（空）")}`,
          "影响：项目列表新增 1 个故事，不修改现有数据",
        ],
      };
    case "add_character":
      return {
        label: "新增角色卡",
        lines: [
          `位置：项目《${projectName}》 → 角色列表`,
          `将新增 1 个角色：${String(args.name || "未命名")}`,
          "现有角色不会被修改",
        ],
      };
    case "update_character": {
      const targetName = String(args.name || args.id || "");
      const card = activeProject.value.characters.find(
        (item) => item.name === targetName || item.id === args.id,
      );
      const fields: [keyof CharacterCard, string][] = [
        ["role", "角色"],
        ["drive", "欲望"],
        ["fear", "恐惧"],
        ["stance", "立场"],
        ["identity", "身份"],
        ["traits", "特质"],
        ["background", "背景"],
        ["secret", "秘密"],
        ["status", "状态"],
      ];
      const changed: string[] = [];
      for (const [key, label] of fields) {
        if (args[key] !== undefined && String(card?.[key] ?? "") !== String(args[key])) {
          changed.push(
            `${label}：${String(card?.[key] ?? "（空）")} → ${String(args[key])}`,
          );
        }
      }
      if (!card) {
        changed.push(`将按名称/ID 匹配角色「${targetName || "?"}」，未在当前项目找到对应角色`);
      }
      return {
        label: `调整角色「${card?.name || targetName || "?"}」`,
        lines: changed.length > 0 ? changed : ["未检测到字段变化，请确认是否仍要执行"],
      };
    }
    case "add_world_card":
      return {
        label: "新增设定",
        lines: [
          `位置：项目《${projectName}》 → 世界观`,
          `新增：${String(args.name || "未命名")}（${String(args.type || "地点")}）`,
          "现有设定不会被修改",
        ],
      };
    case "append_chapter":
      return {
        label: "追加章节",
        lines: [
          `位置：项目《${projectName}》 → 章节列表（末尾）`,
          `新增章节：《${String(args.title || "未命名")}》 · 约 ${String(args.content || "").length} 字`,
          "现有章节不会被修改",
        ],
      };
    case "import_txt":
      return {
        label: "导入 TXT",
        lines: [
          "位置：书架",
          `新增书籍：《${String(args.name || "未命名")}》 · 约 ${String(args.text || "").length} 字`,
          "现有书籍不会被修改",
        ],
      };
    case "append_book_chapter": {
      const book = shelfBooks.value.find((item) => item.book_id === args.book_id);
      return {
        label: "给书追加章节",
        lines: [
          `位置：书架 → 《${book?.name || String(args.book_id || "未知书")}》`,
          `新增章节：《${String(args.title || "未命名")}》 · 约 ${String(args.content || "").length} 字`,
          "现有章节不会被修改",
        ],
      };
    }
    case "save_knowledge":
      return {
        label: "保存资料草稿",
        lines: [
          "位置：资料库 → 草稿",
          `标题：${String(args.title || "未命名")}`,
          `内容预览：${preview(String(args.content || ""), 80)}`,
        ],
      };
    case "delete_character":
      return {
        label: "删除角色",
        lines: [
          `位置：项目《${projectName}》 → 角色列表`,
          `将永久删除角色「${String(args.name || args.id || "?")}」`,
          "⚠️ 删除后不可恢复",
        ],
      };
    case "update_world_card": {
      const target = String(args.name || args.id || "?");
      const card = activeProject.value.world.find(
        (item) => item.name === target || item.id === args.id,
      );
      const changed: string[] = [];
      const worldFields: [keyof WorldCard, string][] = [
        ["type", "类型"],
        ["summary", "概要"],
        ["details", "详情"],
        ["significance", "重要性"],
        ["tags", "标签"],
      ];
      for (const [key, label] of worldFields) {
        if (args[key] !== undefined && String(card?.[key] ?? "") !== String(args[key])) {
          changed.push(`${label}：${String(card?.[key] ?? "（空）")} → ${String(args[key])}`);
        }
      }
      return {
        label: `调整设定「${card?.name || target}」`,
        lines: changed.length > 0 ? changed : ["未检测到字段变化，请确认是否仍要执行"],
      };
    }
    case "delete_world_card":
      return {
        label: "删除设定",
        lines: [
          `位置：项目《${projectName}》 → 世界观`,
          `将永久删除设定「${String(args.name || args.id || "?")}」`,
          "⚠️ 删除后不可恢复",
        ],
      };
    case "update_chapter": {
      const target = String(args.chapter_id || args.title || "?");
      return {
        label: `修改章节「${target}」`,
        lines: [
          `位置：项目《${projectName}》 → 章节列表`,
          args.content !== undefined
            ? `正文将被替换（新正文约 ${String(args.content).length} 字）`
            : "将修改章节标题",
          "⚠️ 原正文会被覆盖",
        ],
      };
    }
    case "delete_chapter":
      return {
        label: "删除章节",
        lines: [
          `位置：项目《${projectName}》 → 章节列表`,
          `将永久删除章节「${String(args.chapter_id || args.title || "?")}」`,
          "⚠️ 删除后不可恢复",
        ],
      };
    case "update_project": {
      const project = activeProject.value;
      const changed: string[] = [];
      const projectFields: [string, string][] = [
        ["name", "名称"],
        ["genre", "类型"],
        ["summary", "概要"],
        ["global_guidance", "全局引导"],
        ["chapter_turns", "单章回合数"],
      ];
      for (const [key, label] of projectFields) {
        if (args[key] !== undefined && String(project?.[key as keyof StoryProject] ?? "") !== String(args[key])) {
          changed.push(
            `${label}：${String(project?.[key as keyof StoryProject] ?? "（空）")} → ${String(args[key])}`,
          );
        }
      }
      return {
        label: `修改项目「${project?.name || projectName}」`,
        lines: changed.length > 0 ? changed : ["未检测到字段变化，请确认是否仍要执行"],
      };
    }
    case "merge_chapters": {
      const book = shelfBooks.value.find((item) => item.book_id === args.book_id);
      return {
        label: "合并章节",
        lines: [
          `位置：书架 → 《${book?.name || String(args.book_id || "未知书")}》`,
          `将第 ${String(args.start_order ?? "?")}–${String(args.end_order ?? "?")} 章合并为 1 章`,
          "⚠️ 合并后的原章节会被移除",
        ],
      };
    }
    case "evolution_start":
      return {
        label: "新建演化",
        lines: [
          "位置：演化存档",
          `将新建《${String(args.project_name || args.project_id || "未命名")}》的演化（从第 1 回合开始）`,
          "不会修改现有正文",
        ],
      };
    case "evolution_advance":
      return {
        label: "推进演化",
        lines: [
          `位置：演化存档（${String(args.project_id || "当前项目")}）`,
          "将推进 1 个回合；如遇分支会暂停等待选择",
          "已发生的回合记录会追加",
        ],
      };
    case "evolution_guidance":
      return {
        label: "设置引导",
        lines: [
          `位置：演化存档（${String(args.project_id || "当前项目")}）`,
          `将设置全局引导：「${String(args.guidance || "（空）")}」`,
          "后续回合生效",
        ],
      };
    case "evolution_reset":
      return {
        label: "重置演化",
        lines: [
          `位置：演化存档（${String(args.project_id || "当前项目")}）`,
          "将永久删除整个演化存档",
          "⚠️ 删除后不可恢复",
        ],
      };
    case "update_llm_config":
      return {
        label: "修改 AI 配置",
        lines: [
          "位置：AI 通道配置",
          [
            args.base_url !== undefined ? `API 地址：${String(args.base_url)}` : "",
            args.model !== undefined ? `模型：${String(args.model)}` : "",
            args.preset !== undefined ? `预设：${String(args.preset)}` : "",
          ]
            .filter(Boolean)
            .join("，") || "更新配置项",
          "不会写入或清除 API Key",
        ],
      };
    case "list_projects":
    case "export_project":
    case "export_book":
    case "get_llm_config":
    case "get_server_status":
      return {
        label: toolActionLabel(action.tool),
        lines: ["只读操作，不会修改任何数据"],
      };
    default:
      return {
        label: toolActionLabel(action.tool),
        lines: ["执行后将写入本地数据"],
      };
  }
});

const agentImpactDanger = computed(() => {
  const tool = pendingAgentAction.value?.tool ?? "";
  return tool.includes("delete") || tool === "evolution_reset" || tool === "merge_chapters" || tool === "update_chapter";
});

const createPathSteps = [
  {
    index: 1,
    label: "创建故事",
    hint: "名称与概要",
    action: () => {
      activity.value = "story";
    },
  },
  {index: 2, label: "写正文", hint: "第一章", action: startWriting},
  {
    index: 3,
    label: "AI 对话",
    hint: "续写 / 导入",
    action: () => void openActivity("chat"),
  },
  {
    index: 4,
    label: "演化小说",
    hint: "让故事自己演",
    action: () => void openActivity("evolution"),
  },
  {
    index: 5,
    label: "TXT 书架",
    hint: "导入长篇小说",
    action: () => void openActivity("shelf"),
  },
];

function toastSuccess(message: string): void {
  ElMessage({message, type: "success", duration: 2200});
}

function toastError(message: string): void {
  ElMessage({message, type: "error", duration: 3200});
}

function toastInfo(message: string): void {
  ElMessage({message, type: "info", duration: 2200});
}

const chatContextLabel = computed(() => {
  const chapterText = activeChapter.value ? `《${activeChapter.value.title}》` : "未选择章节";
  const referenceText = selectedKnowledgeNodes.value.length > 0 ? `${selectedKnowledgeNodes.value.length} 条资料` : "未选择资料";
  return `${chapterText} · ${referenceText}`;
});

const backendStatusLabel = computed(() => {
  if (backendStatus.value === "online") {
    return "资料库可用";
  }
  if (backendStatus.value === "offline") {
    return "资料库离线";
  }
  return "正在检查";
});

const vaultRuntimeLabel = computed(() => {
  const manager = vaultStatus.value?.manager;
  if (manager?.running) {
    return `由 Rhine-Lore 启动 · PID ${manager.pid}`;
  }
  if (vaultStatus.value?.connected) {
    return manager?.mode === "default-core" ? "已连接默认资料库" : "已连接到外部 Rhine-Vault";
  }
  return "尚未连接资料库后端";
});

const vaultModeLabel = computed(() => {
  return vaultStatus.value?.manager.mode === "external" ? "外部 Vault" : "默认 Core";
});

const vaultWebLabel = computed(() => {
  if (vaultWebStatus.value?.installed) {
    return "Vault Web 已准备好";
  }
  if (vaultWebStatus.value?.installable) {
    return "Vault Web 可安装";
  }
  return "Vault Web 未发现";
});

const vaultWebUrl = computed(() => {
  return vaultWebStatus.value?.url || vaultStatus.value?.manager.base_url || "http://127.0.0.1:8795/";
});

const backendStatusTone = computed(() => {
  if (backendStatus.value === "online") {
    return "online";
  }
  if (backendStatus.value === "offline") {
    return "offline";
  }
  return "checking";
});

const activeChapterParagraphs = computed(() => {
  const content = activeChapter.value?.content ?? "";
  return splitReaderParagraphs(content);
});

const activeChapterIndex = computed(() => {
  const chapterId = activeChapter.value?.id;
  if (!chapterId) {
    return -1;
  }
  return activeProject.value.chapters.findIndex((chapter) => chapter.id === chapterId);
});

const chapterCharacterCount = computed(() => activeChapter.value?.content.trim().length ?? 0);

const projectCharacterCount = computed(() => {
  return activeProject.value.chapters.reduce((total, chapter) => total + chapter.content.trim().length, 0);
});

const latestChapter = computed(() => {
  const chapters = activeProject.value.chapters;
  return chapters[chapters.length - 1] ?? null;
});

const hasStoryIdentity = computed(() => {
  const name = activeProject.value.name.trim();
  return Boolean(name && !["我的故事", "新的故事", "Untitled Lore", "New Lore Project"].includes(name));
});

const hasStartedCreating = computed(() => {
  return projectCharacterCount.value > 0 || activeProject.value.chat.length > 0;
});

const projectSetupSteps = computed(() => [
  {label: "给故事起个名字", complete: hasStoryIdentity.value},
  {label: "准备第一章", complete: activeProject.value.chapters.length > 0},
  {label: "写下第一段或聊聊想法", complete: hasStartedCreating.value},
]);

const needsProjectGuidance = computed(() => !projectSetupSteps.value.every((step) => step.complete));

const nextStepLabel = computed(() => {
  if (!hasStoryIdentity.value) {
    return "补充故事信息";
  }
  if (activeProject.value.chapters.length === 0) {
    return "创建第一章";
  }
  return "开始创作";
});

const chapterNavigationLabel = computed(() => {
  const total = activeProject.value.chapters.length;
  if (activeChapterIndex.value < 0 || total === 0) {
    return "暂无章节";
  }
  return `${activeChapterIndex.value + 1} / ${total}`;
});

watch(shelfAnalysisMode, (mode) => {
  localStorage.setItem("rhine-lore-analysis-mode", mode);
  if (shelfBookId.value) void loadShelfAnalysisPlan(shelfBookId.value);
});

onMounted(async () => {
  (window as NativeBackWindow).rhineLoreHandleBack = handleNativeBack;
  systemDark.value = window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme();
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", handleSystemThemeChange);
  document.addEventListener("click", closeChatMore);
  window.addEventListener("scroll", handleReadingScroll, {passive: true});
  readerScrollContainer()?.addEventListener("scroll", handleReadingScroll, {passive: true});
  window.addEventListener("resize", handleReaderResize);
  window.addEventListener("keydown", handleReaderOverlayKeydown);
  window.addEventListener("pagehide", handleProjectPageHide);
  document.addEventListener("fullscreenchange", handleReaderFullscreenChange);
  await initProjects();
  await perform("初始化", async () => {
    await Promise.allSettled([updateBackendStatus(), refreshWorkspaces(), refreshNodes(), refreshReview()]);
    return {ready: true};
  }, {collapseOutput: true});
  void runAiCheck();
  void loadDiskBackups();
  void loadLanInfo();
  void loadLlmServerConfig();
});

function closeChatMore(): void {
  chatMoreOpen.value = false;
}

function handleNativeBack(): boolean {
  const floatingControl = document.querySelector<HTMLElement>(".el-popper[aria-hidden='false']");
  if (floatingControl && floatingControl.getBoundingClientRect().height > 0) {
    const target = document.activeElement instanceof HTMLElement ? document.activeElement : document.body;
    target.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape", code: "Escape", bubbles: true}));
    return true;
  }
  if (mobileNavOpen.value) {
    mobileNavOpen.value = false;
    return true;
  }
  if (chatMoreOpen.value) {
    chatMoreOpen.value = false;
    return true;
  }
  if (window.innerWidth <= 720 && chatSidebarOpen.value) {
    chatSidebarOpen.value = false;
    return true;
  }
  if (readerSettingsVisible.value) {
    readerSettingsVisible.value = false;
    return true;
  }
  if (readerNavigatorVisible.value) {
    readerNavigatorVisible.value = false;
    return true;
  }
  if (novelVersionsVisible.value || shelfVersionsVisible.value) {
    novelVersionsVisible.value = false;
    shelfVersionsVisible.value = false;
    return true;
  }
  if (createDialogVisible.value || restoreDialogVisible.value) {
    createDialogVisible.value = false;
    restoreDialogVisible.value = false;
    return true;
  }
  if (knowledgeReviewVisible.value || knowledgeExtractVisible.value) {
    knowledgeReviewVisible.value = false;
    knowledgeExtractVisible.value = false;
    return true;
  }
  if (worldEditVisible.value || characterEditVisible.value || evolutionCharacterDialogVisible.value) {
    worldEditVisible.value = false;
    characterEditVisible.value = false;
    evolutionCharacterDialogVisible.value = false;
    return true;
  }
  if (storyStyleOpen.value || aiPanelOpen.value) {
    storyStyleOpen.value = false;
    aiPanelOpen.value = false;
    return true;
  }
  if (readerOverlayOpen.value) {
    exitReaderMode();
    return true;
  }
  if (activity.value !== "studio") {
    sidebarMode.value = "workbench";
    localStorage.setItem("rhine-lore-sidebar-mode", "workbench");
    void openActivity("studio");
    return true;
  }
  return false;
}

function applyTheme(): void {
  const dark = themeMode.value === "dark" || (themeMode.value === "system" && systemDark.value);
  document.documentElement.classList.toggle("dark", dark);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  localStorage.setItem("rhine-lore-theme", themeMode.value);
}

function setThemeMode(mode: ThemeMode): void {
  themeMode.value = mode;
  applyTheme();
}

function handleSystemThemeChange(event: MediaQueryListEvent): void {
  systemDark.value = event.matches;
  applyTheme();
}

function createDefaultProject(): StoryProject {
  return createStoryProjectFromTemplate("gothic-fantasy", uid);
}

function loadLegacyProjects(): StoryProject[] {
  const raw = localStorage.getItem(projectKey);
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as Partial<StoryProject>[];
      return parsed.map(normalizeProject);
    } catch {
      localStorage.removeItem(projectKey);
    }
  }
  return [];
}

type PendingProjectDraft = {
  saved_at: number;
  project: StoryProject;
};

function projectDraftKey(projectId: string): string {
  return `${projectDraftPrefix}${projectId}`;
}

function projectDraftIds(): string[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(projectDraftIndexKey) || "[]") as unknown;
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === "string") : [];
  } catch {
    return [];
  }
}

function rememberProjectDraftId(projectId: string): void {
  const ids = new Set(projectDraftIds());
  ids.add(projectId);
  localStorage.setItem(projectDraftIndexKey, JSON.stringify([...ids]));
}

function persistProjectDraft(project: StoryProject): void {
  try {
    const draft: PendingProjectDraft = {
      saved_at: Date.now(),
      project: JSON.parse(JSON.stringify(project)) as StoryProject,
    };
    localStorage.setItem(projectDraftKey(project.id), JSON.stringify(draft));
    rememberProjectDraftId(project.id);
  } catch {
    // The server-side save remains authoritative when browser storage is unavailable or full.
  }
}

function clearProjectDraft(projectId: string): void {
  try {
    localStorage.removeItem(projectDraftKey(projectId));
    const remaining = projectDraftIds().filter((id) => id !== projectId);
    if (remaining.length > 0) {
      localStorage.setItem(projectDraftIndexKey, JSON.stringify(remaining));
    } else {
      localStorage.removeItem(projectDraftIndexKey);
    }
  } catch {
    // A stale recovery draft is harmless and will be compared with the server copy next time.
  }
}

function loadPendingProjectDrafts(): PendingProjectDraft[] {
  const drafts: PendingProjectDraft[] = [];
  for (const projectId of projectDraftIds()) {
    try {
      const raw = localStorage.getItem(projectDraftKey(projectId));
      if (!raw) continue;
      const parsed = JSON.parse(raw) as Partial<PendingProjectDraft>;
      if (!parsed.project?.id) {
        clearProjectDraft(projectId);
        continue;
      }
      drafts.push({
        saved_at: Number(parsed.saved_at) || 0,
        project: normalizeProject(parsed.project),
      });
    } catch {
      clearProjectDraft(projectId);
    }
  }
  return drafts;
}

async function initProjects(): Promise<void> {
  let serverAvailable = false;
  const serverUpdatedAt = new Map<string, number>();
  try {
    const metaResult = await listServerProjects();
    serverAvailable = true;
    for (const meta of metaResult.projects) {
      const timestamp = Date.parse(meta.updated_at);
      serverUpdatedAt.set(meta.project_id, Number.isFinite(timestamp) ? timestamp : 0);
    }
    if (metaResult.projects.length > 0) {
      projects.value = await Promise.all(
        metaResult.projects.map((meta) =>
          getServerProject(meta.project_id).then((result) => normalizeProject(result.project)),
        ),
      );
    } else {
      const legacy = loadLegacyProjects();
      if (legacy.length > 0) {
        for (const project of legacy) {
          await saveServerProject(project);
        }
        projects.value = legacy;
        localStorage.removeItem(projectKey);
      } else {
        projects.value = [createDefaultProject()];
        await saveServerProject(projects.value[0]);
      }
      localStorage.removeItem(projectKey);
    }
  } catch {
    const legacy = loadLegacyProjects();
    projects.value = legacy.length > 0 ? legacy : [createDefaultProject()];
  }
  const recoveredDrafts: StoryProject[] = [];
  for (const draft of loadPendingProjectDrafts()) {
    const index = projects.value.findIndex((project) => project.id === draft.project.id);
    const serverTimestamp = serverUpdatedAt.get(draft.project.id) ?? 0;
    if (index < 0 || !serverAvailable || draft.saved_at >= serverTimestamp) {
      if (index >= 0) {
        projects.value[index] = draft.project;
      } else {
        projects.value.push(draft.project);
      }
      recoveredDrafts.push(draft.project);
    } else {
      clearProjectDraft(draft.project.id);
    }
  }
  if (
    !projects.value.some((project) => project.id === activeProjectId.value) &&
    projects.value.length > 0
  ) {
    activeProjectId.value = projects.value[0].id;
    localStorage.setItem(activeProjectKey, activeProjectId.value);
  }
  const initialProject = projects.value.find((project) => project.id === activeProjectId.value);
  if (
    initialProject &&
    initialProject.chapters.length > 0 &&
    !initialProject.chapters.some((chapter) => chapter.id === activeChapterId.value)
  ) {
    activeChapterId.value = initialProject.chapters[0].id;
    localStorage.setItem(activeChapterKey, activeChapterId.value);
  }
  if (serverAvailable) {
    for (const project of recoveredDrafts) {
      queueProjectBackup(project, 80);
    }
  }
}

function normalizeCharacter(item: Partial<CharacterCard> & Partial<LoreItem>): CharacterCard {
  const legacyTitle = item.title || "";
  const legacyContent = item.content || "";
  return {
    id: item.id || uid("character"),
    name: item.name || legacyTitle || "未命名角色",
    identity: item.identity || "",
    role: item.role || "配角",
    age: item.age || "",
    stance: item.stance || "",
    drive: item.drive || "",
    fear: item.fear || "",
    traits: item.traits || "",
    abilities: item.abilities || "",
    weakness: item.weakness || "",
    secret: item.secret || "",
    speech: item.speech || "",
    appearance: item.appearance || "",
    background: item.background || "",
    relationships: Array.isArray(item.relationships)
      ? item.relationships.map((relation: CharacterRelationship) => ({
          name: String(relation?.name ?? ""),
          relation: String(relation?.relation ?? ""),
        }))
      : [],
    status: item.status || "正常",
    notes: item.notes || legacyContent || "",
  };
}

function normalizeIssue(issue: Partial<ManuscriptIssue>): ManuscriptIssue {
  const kinds: ManuscriptIssue["kind"][] = ["冲突", "误区", "不一致", "提醒"];
  const statuses: ManuscriptIssue["status"][] = ["待处理", "已处理", "忽略"];
  return {
    id: issue.id || uid("issue"),
    kind: kinds.includes(String(issue.kind) as ManuscriptIssue["kind"]) ? (String(issue.kind) as ManuscriptIssue["kind"]) : "提醒",
    item: issue.item || "未命名问题",
    reason: issue.reason || "",
    suggestion: issue.suggestion || "",
    status: statuses.includes(String(issue.status) as ManuscriptIssue["status"])
      ? (String(issue.status) as ManuscriptIssue["status"])
      : "待处理",
    created_at: issue.created_at || new Date().toISOString(),
  };
}

function normalizeWorld(item: Partial<WorldCard> & Partial<LoreItem>): WorldCard {
  const legacyTitle = item.title || "";
  const legacyContent = item.content || "";
  return {
    id: item.id || uid("world"),
    name: item.name || legacyTitle || "新设定",
    type: item.type || "地点",
    summary: item.summary || "",
    details: item.details || legacyContent || "",
    significance: item.significance || "",
    tags: item.tags || "",
  };
}

function normalizeMap(map: Partial<StoryMap> | null | undefined): StoryMap {
  return {
    nodes: (map?.nodes ?? []).map((node) => ({
      id: node.id || uid("map-node"),
      name: node.name || "新地点",
      x: Number(node.x) || 0,
      y: Number(node.y) || 0,
      description: node.description || "",
    })),
    edges: (map?.edges ?? [])
      .filter((edge) => edge.from && edge.to)
      .map((edge) => ({
        id: edge.id || uid("map-edge"),
        from: edge.from,
        to: edge.to,
      })),
  };
}

function normalizeProject(project: Partial<StoryProject>): StoryProject {
  const chat = (project.chat ?? []).map((message) => {
    if (
      message.role === "assistant" &&
      typeof message.content === "string" &&
      message.content.startsWith("FakeLLM answer for:")
    ) {
      return {
        ...message,
        content: "这条旧的离线测试回复已整理。你可以继续发起新的创作请求，新的回复会以可编辑草稿呈现。",
      };
    }
    return message;
  });
  return {
    id: project.id || `project-${Date.now()}`,
    name: project.name || "未命名故事",
    genre: project.genre || "未分类",
    summary: project.summary || "",
    source_book_id: project.source_book_id || "",
    source_branch_id: project.source_branch_id || "",
    global_guidance: project.global_guidance || "",
    chapter_turns: Math.min(8, Math.max(1, Number(project.chapter_turns) || 4)),
    writing_style: project.writing_style || "",
    polish_writing: project.polish_writing !== false,
    style_example: project.style_example || "",
    style_notes: project.style_notes || "",
    style_avoid: project.style_avoid || "",
    world: (project.world ?? []).map(normalizeWorld),
    characters: (project.characters ?? []).map(normalizeCharacter),
    map: normalizeMap(project.map),
    chapters: project.chapters ?? [],
    chat,
    issues: (project.issues ?? []).map(normalizeIssue),
  };
}

function saveProjects(): void {
  localStorage.setItem(activeProjectKey, activeProjectId.value);
  localStorage.setItem(activeChapterKey, activeChapterId.value);
  lastSavedAt.value = new Date().toLocaleTimeString("zh-CN", {hour: "2-digit", minute: "2-digit"});
  const project = activeProject.value;
  if (project?.id) {
    queueProjectBackup(project);
  }
}

function queueProjectBackup(project: StoryProject, delay = 900): void {
  pendingProjectBackups.set(project.id, project);

  const existingDraftTimer = projectDraftTimers.get(project.id);
  if (existingDraftTimer) {
    window.clearTimeout(existingDraftTimer);
  }
  projectDraftTimers.set(
    project.id,
    window.setTimeout(() => {
      projectDraftTimers.delete(project.id);
      persistProjectDraft(project);
    }, Math.min(delay, 180)),
  );

  const existingBackupTimer = projectBackupTimers.get(project.id);
  if (existingBackupTimer) {
    window.clearTimeout(existingBackupTimer);
  }
  projectBackupTimers.set(
    project.id,
    window.setTimeout(() => {
      projectBackupTimers.delete(project.id);
      void backupProject(project);
    }, delay),
  );
}

async function backupProject(project: StoryProject): Promise<void> {
  const serializedProject = JSON.stringify(project);
  const snapshot = JSON.parse(serializedProject) as StoryProject;
  persistProjectDraft(snapshot);
  try {
    await saveServerProject(snapshot);
    const current = pendingProjectBackups.get(project.id);
    if (!current || JSON.stringify(current) === serializedProject) {
      pendingProjectBackups.delete(project.id);
      clearProjectDraft(project.id);
    }
  } catch (error) {
    runState.value = {error: `自动保存失败：${error instanceof Error ? error.message : String(error)}`};
    toastError("自动保存失败，请检查本地服务");
  }
}

function flushPendingProjectDrafts(): void {
  for (const project of pendingProjectBackups.values()) {
    persistProjectDraft(project);
  }
}

function handleProjectPageHide(): void {
  flushPendingProjectDrafts();
}

async function loadDiskBackups(): Promise<void> {
  try {
    const result = await listProjectBackups();
    diskBackups.value = result.backups ?? [];
  } catch {
    diskBackups.value = [];
  }
}

async function loadLanInfo(): Promise<void> {
  try {
    lanInfo.value = await getLanInfo();
  } catch {
    lanInfo.value = null;
  }
}

function openRestoreDialog(): void {
  restoreDialogVisible.value = true;
  void loadDiskBackups();
}

async function confirmRestore(row: ProjectBackupRow): Promise<void> {
  restoreBusy.value = row.project_id;
  const result = await perform("恢复项目", () => restoreProjectBackup(row.project_id));
  restoreBusy.value = "";
  if (!result?.project) {
    return;
  }
  const restored = normalizeProject(result.project);
  const index = projects.value.findIndex((item) => item.id === restored.id);
  if (index >= 0) {
    projects.value[index] = restored;
  } else {
    projects.value.push(restored);
  }
  activeProjectId.value = restored.id;
  activeChapterId.value = restored.chapters[0]?.id ?? "";
  restoreDialogVisible.value = false;
  saveProjects();
  markSaved("已从磁盘恢复项目");
}

function markSaved(message: string): void {
  saveNotice.value = message;
  lastSavedAt.value = new Date().toLocaleTimeString("zh-CN", {hour: "2-digit", minute: "2-digit"});
  if (saveNoticeTimer) {
    window.clearTimeout(saveNoticeTimer);
  }
  saveNoticeTimer = window.setTimeout(() => {
    saveNotice.value = "";
  }, 4200);
}

function uid(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

async function perform<T>(
  label: string,
  task: () => Promise<T>,
  options: {collapseOutput?: boolean} = {},
): Promise<T | null> {
  busyAction.value = label;
  notice.value = `${label}...`;
  try {
    const result = await task();
    if (result !== undefined && !options.collapseOutput) {
      runState.value = result as Record<string, unknown>;
    }
    notice.value = `${label}完成`;
    return result;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    runState.value = {error: message, action: label};
    notice.value = `${label}失败`;
    return null;
  } finally {
    busyAction.value = "";
  }
}

async function openActivity(next: Activity): Promise<void> {
  activity.value = next;
  workMode.value = next === "settings" ? "advanced" : "write";
  if (next === "evolution") {
    await loadEvolutionView();
  }
  if (next === "read") {
    await loadEvolutionView();
    const position = loadReaderPosition("evolution", activeProject.value.id);
    const savedIndex = Number(position?.chapterId ?? "-1");
    evolutionChapterIndex.value = savedIndex >= 0 && savedIndex < evolutionNovelChapters.value.length
      ? savedIndex
      : Math.max(0, evolutionNovelChapters.value.length - 1);
    await restoreReaderProgress(position);
  }
  if (next === "shelf") {
    await loadShelfBooks();
  }
  if (next === "context") {
    await Promise.allSettled([refreshNodes(), refreshReview()]);
  }
  if (next === "settings") {
    await Promise.allSettled([refreshWorkspaces(), refreshReview()]);
  }
  await nextTick();
  contentMainRef.value?.focus({preventScroll: true});
}

watch(activity, async () => {
  await nextTick();
  window.scrollTo(0, 0);
  document
    .querySelectorAll<HTMLElement>(".workspace-main .el-scrollbar__wrap, .activity-panel")
    .forEach((element) => {
      element.scrollTop = 0;
      element.scrollLeft = 0;
    });
});

function toggleSidebar(): void {
  sidebarCollapsed.value = !sidebarCollapsed.value;
  localStorage.setItem("rhine-lore-sidebar-collapsed", sidebarCollapsed.value ? "1" : "0");
}

function setSidebarMode(mode: SidebarMode): void {
  if (sidebarMode.value === mode) {
    return;
  }
  sidebarMode.value = mode;
  localStorage.setItem("rhine-lore-sidebar-mode", mode);
  const list = mode === "reader" ? readerActivities : workbenchActivities;
  if (!list.some((item) => item.id === activity.value)) {
    activity.value = list[0].id;
    void openActivity(list[0].id);
  }
}

async function openMobileNav(): Promise<void> {
  mobileNavOpen.value = true;
  await nextTick();
  mobileCloseBtnRef.value?.focus({preventScroll: true});
}

async function closeMobileNav(): Promise<void> {
  mobileNavOpen.value = false;
  await nextTick();
  mobileMenuBtnRef.value?.focus({preventScroll: true});
}

function persistReaderSettings(): void {
  localStorage.setItem("rhine-lore-reader-font-size", String(readerFontSize.value));
  localStorage.setItem("rhine-lore-reader-line-height", String(readerLineHeight.value));
  localStorage.setItem("rhine-lore-reader-theme", readerTheme.value);
  localStorage.setItem("rhine-lore-reader-paragraph-spacing", String(readerParagraphSpacing.value));
  localStorage.setItem("rhine-lore-reader-justify", readerJustify.value ? "1" : "0");
  localStorage.setItem("rhine-lore-reader-indent", readerIndent.value ? "1" : "0");
  localStorage.setItem("rhine-lore-reader-auto-advance", readerAutoAdvance.value ? "1" : "0");
  localStorage.setItem("rhine-lore-reader-font-family", readerFontFamily.value);
  localStorage.setItem("rhine-lore-reader-brightness", String(readerBrightness.value));
  localStorage.setItem("rhine-lore-reader-measure", String(readerMeasure.value));
  localStorage.setItem("rhine-lore-reader-mode", readerPageMode.value);
  if (readerPageMode.value === "page") {
    void repaginate();
  }
}

function readerThemeClass(): string {
  return `theme-${readerTheme.value}`;
}

function readerContentStyle(): Record<string, string> {
  const fonts = {
    serif: '"Noto Serif SC", "Source Han Serif SC", "Songti SC", SimSun, serif',
    sans: 'Inter, "Segoe UI", "Microsoft YaHei", system-ui, sans-serif',
    system: 'system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif',
  };
  return {
    fontSize: `${readerFontSize.value}px`,
    fontFamily: fonts[readerFontFamily.value],
    lineHeight: String(readerLineHeight.value),
    textAlign: readerJustify.value ? "justify" : "left",
    "--reader-para-margin": `${readerParagraphSpacing.value}em`,
    "--reader-measure": `${readerMeasure.value}px`,
    "--reader-indent": readerIndent.value ? "2em" : "0",
    "--reader-brightness": String(readerBrightness.value / 100),
  } as Record<string, string>;
}

function resetReaderSettings(): void {
  readerPageMode.value = "scroll";
  readerTheme.value = "day";
  readerFontFamily.value = "serif";
  readerFontSize.value = 18;
  readerLineHeight.value = 1.9;
  readerParagraphSpacing.value = 1.1;
  readerMeasure.value = 700;
  readerBrightness.value = 100;
  readerJustify.value = true;
  readerIndent.value = true;
  readerAutoAdvance.value = true;
  persistReaderSettings();
}

function readerScrollContainer(): HTMLElement | null {
  if (readerOverlayOpen.value) {
    return document.querySelector<HTMLElement>(".reader-overlay-scroll");
  }
  return document.querySelector<HTMLElement>(".workspace-main .el-scrollbar__wrap");
}

function resetReaderScroll(): void {
  userScrolledReading.value = false;
  const wrap = readerScrollContainer();
  if (wrap) {
    wrap.scrollTop = 0;
  } else {
    window.scrollTo({top: 0});
  }
  requestAnimationFrame(updateReadingProgress);
}

async function loadShelfBooks(): Promise<void> {
  try {
    const result = await listBooks();
    shelfBooks.value = result.books;
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  }
}

const shelfCoverPalettes: [string, string][] = [
  ["#1e3a8a", "#7c3aed"],
  ["#0f766e", "#2563eb"],
  ["#b45309", "#db2777"],
  ["#7a3fc0", "#0ea5e9"],
  ["#be123c", "#f59e0b"],
  ["#166534", "#0f766e"],
];

function hashText(text: string): number {
  let hash = 0;
  for (const ch of text) {
    hash = (hash * 31 + (ch.codePointAt(0) ?? 0)) >>> 0;
  }
  return hash;
}

function shelfCoverStyle(book: {name?: string}): Record<string, string> {
  const key = book.name || "书";
  const hash = hashText(key);
  const palette = shelfCoverPalettes[hash % shelfCoverPalettes.length];
  const patterns = [
    "repeating-linear-gradient(115deg, transparent 0 10px, rgba(255,255,255,0.55) 10px 12px)",
    "radial-gradient(circle at 24% 28%, rgba(255,255,255,0.5) 0 2px, transparent 2.5px)",
    "repeating-linear-gradient(0deg, transparent 0 14px, rgba(255,255,255,0.4) 14px 15px)",
  ];
  return {
    background: `linear-gradient(135deg, ${palette[0]}, ${palette[1]})`,
    "--cover-pattern": patterns[hash % patterns.length],
  } as Record<string, string>;
}

const shelfImportPreview = computed(() => {
  const text = shelfImportDecoded.value?.text.trim() ?? "";
  return text.length > 2800 ? `${text.slice(0, 2800)}\n…` : text;
});

const shelfImportConfidenceLabel = computed(() => {
  if (shelfImportEncoding.value !== "auto") return "手动选择";
  return {
    high: "高可信",
    medium: "建议确认",
    low: "需要确认",
  }[shelfImportDecoded.value?.confidence ?? "low"];
});

const shelfImportNeedsAttention = computed(
  () =>
    shelfImportDecoded.value?.confidence === "low" ||
    Boolean(shelfImportDecoded.value?.replacementCount),
);

function resetShelfImportDialog(): void {
  shelfImportBusy.value = false;
  shelfImportAdvanced.value = false;
  shelfImportName.value = "";
  shelfImportFileName.value = "";
  shelfImportFileSize.value = "";
  shelfImportEncoding.value = "auto";
  shelfImportBytes.value = null;
  shelfImportDetected.value = null;
  shelfImportDecoded.value = null;
  shelfImportError.value = "";
}

function updateShelfImportDecoding(): void {
  const bytes = shelfImportBytes.value;
  const detected = shelfImportDetected.value;
  if (!bytes || !detected) return;
  shelfImportError.value = "";
  try {
    shelfImportDecoded.value = shelfImportEncoding.value === "auto"
      ? detected
      : decodeTextBytes(bytes, shelfImportEncoding.value);
    if (!shelfImportDecoded.value.text.trim()) {
      shelfImportError.value = "当前编码下没有可导入的文字";
    }
  } catch (error) {
    shelfImportError.value = `无法使用这个编码读取文件：${error instanceof Error ? error.message : String(error)}`;
  }
}

async function handleShelfTxtImport(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    return;
  }
  input.value = "";
  try {
    const bytes = new Uint8Array(await file.arrayBuffer());
    const detected = detectAndDecodeText(bytes);
    if (!detected.text.trim()) {
      throw new Error("文件内容为空");
    }
    shelfImportName.value = file.name.replace(/\.(txt|text)$/i, "") || "未命名小说";
    shelfImportFileName.value = file.name;
    shelfImportFileSize.value = file.size >= 1024 * 1024
      ? `${(file.size / 1024 / 1024).toFixed(1)} MB`
      : `${Math.max(1, Math.round(file.size / 1024))} KB`;
    shelfImportEncoding.value = "auto";
    shelfImportBytes.value = bytes;
    shelfImportDetected.value = detected;
    shelfImportDecoded.value = detected;
    shelfImportAdvanced.value = detected.confidence === "low" || detected.replacementCount > 0;
    shelfImportError.value = "";
    shelfImportVisible.value = true;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    runState.value = {error: message, action: "读取 TXT"};
    toastError(message);
  }
}

async function confirmShelfTxtImport(): Promise<void> {
  const decoded = shelfImportDecoded.value;
  if (!decoded?.text.trim()) {
    shelfImportError.value = "没有可导入的文字";
    return;
  }
  if (!shelfImportName.value.trim()) {
    shelfImportError.value = "请填写书名";
    return;
  }
  shelfImportBusy.value = true;
  try {
    const book = await perform("导入 TXT", () => importBook({
      name: shelfImportName.value.trim(),
      genre: "TXT 导入",
      text: decoded.text,
      source_encoding: decoded.encoding,
    }));
    if (!book) return;
    shelfImportVisible.value = false;
    shelfBooks.value = (await listBooks()).books;
    await openShelfBook(book.book_id);
    toastSuccess(`TXT 导入完成 · ${textEncodingLabel(decoded.encoding)}`);
  } finally {
    shelfImportBusy.value = false;
  }
}

const shelfAnalysisRunning = computed(() =>
  ["queued", "running"].includes(shelfAnalysisStatus.value?.state || ""),
);

const shelfAnalysisActionLabel = computed(() => {
  if (shelfAnalysisRunning.value) return "分析进行中";
  if (shelfAnalysisStatus.value?.can_resume) return "继续分析";
  if (shelfAnalysis.value?.stale) return "更新档案";
  if (shelfAnalysis.value) return "重新分析";
  return "建立全书档案";
});

const selectedShelfBranch = computed(() =>
  shelfBranches.value.find((branch) => branch.branch_id === selectedShelfBranchId.value) || null,
);

const shelfBranchEndingCount = computed(() =>
  shelfBranches.value.filter((branch) => branch.is_leaf).length,
);

const branchKindLabels: Record<BranchKind, string> = {
  choice: "关键选择",
  relationship: "关系变化",
  clue: "新线索",
  free: "自由续写",
};

function analysisSourceLabel(chapters: number[] | undefined): string {
  if (!chapters?.length) return "";
  if (chapters.length === 1) return `第 ${chapters[0]} 项`;
  return `第 ${chapters[0]} - ${chapters.at(-1)} 项`;
}

function clearShelfAnalysisPoll(): void {
  if (shelfAnalysisPollTimer) {
    window.clearTimeout(shelfAnalysisPollTimer);
    shelfAnalysisPollTimer = undefined;
  }
}

function closeShelfBook(): void {
  clearShelfAnalysisPoll();
  shelfBook.value = null;
  shelfBookId.value = "";
  shelfChapter.value = null;
  shelfChapterIndex.value = -1;
  shelfAnalysisStatus.value = null;
  shelfAnalysisPlan.value = null;
  pendingShelfProjectBranchId.value = null;
}

function scheduleShelfAnalysisPoll(bookId: string): void {
  clearShelfAnalysisPoll();
  if (!shelfAnalysisRunning.value || shelfBookId.value !== bookId) return;
  shelfAnalysisPollTimer = window.setTimeout(() => {
    void refreshShelfAnalysisStatus(bookId);
  }, 1200);
}

async function loadShelfAnalysisPlan(bookId = shelfBookId.value): Promise<void> {
  if (!bookId) return;
  try {
    const result = await previewBookAnalysis(bookId, shelfAnalysisMode.value);
    if (shelfBookId.value === bookId) shelfAnalysisPlan.value = result.plan;
  } catch {
    if (shelfBookId.value === bookId) shelfAnalysisPlan.value = null;
  }
}

async function refreshShelfAnalysisStatus(bookId = shelfBookId.value): Promise<void> {
  if (!bookId) return;
  try {
    const previousState = shelfAnalysisStatus.value?.state;
    const result = await getBookAnalysisStatus(bookId);
    if (shelfBookId.value !== bookId) return;
    shelfAnalysisStatus.value = result.status;
    if (result.status.plan) shelfAnalysisPlan.value = result.status.plan;
    if (result.status.state === "completed" && previousState !== "completed") {
      const refreshed = await getBook(bookId);
      if (shelfBookId.value !== bookId) return;
      shelfBook.value = refreshed.book;
      shelfAnalysis.value = refreshed.book.analysis ?? null;
      markSaved(result.status.message);
      const branchId = pendingShelfProjectBranchId.value;
      if (branchId !== null) {
        pendingShelfProjectBranchId.value = null;
        void materializeShelfProject(branchId);
      }
    } else if (result.status.state === "failed" && previousState !== "failed") {
      toastError(result.status.error || "全书分析暂停，可稍后继续");
    }
    scheduleShelfAnalysisPoll(bookId);
  } catch {
    clearShelfAnalysisPoll();
  }
}

async function openShelfBook(bookId: string): Promise<void> {
  clearShelfAnalysisPoll();
  const result = await perform("打开书", () => getBook(bookId));
  if (!result) {
    return;
  }
  shelfBook.value = result.book;
  shelfBookId.value = result.book.book_id;
  shelfChapter.value = null;
  shelfChapterIndex.value = -1;
  shelfAiResult.value = "";
  shelfAnalysis.value = result.book.analysis ?? null;
  shelfAnalysisStatus.value = null;
  shelfAnalysisPlan.value = null;
  pendingShelfProjectBranchId.value = null;
  const position = loadReaderPosition("shelf", bookId);
  const saved = position?.chapterId || localStorage.getItem(`rhine-shelf-pos-${bookId}`);
  const targetId =
    saved && result.book.chapters.some((item) => item.id === saved)
      ? saved
      : (result.book.chapters[0]?.id ?? "");
  if (targetId) {
    await loadShelfChapter(targetId);
  }
  await restoreReaderProgress(position);
  void refreshShelfAnalysisStatus(bookId);
  void loadShelfAnalysisPlan(bookId);
}

async function loadShelfChapter(chapterId: string): Promise<void> {
  if (!shelfBookId.value) {
    return;
  }
  const result = await perform("加载章节", () => getBookChapter(shelfBookId.value, chapterId), {
    collapseOutput: true,
  });
  if (!result) {
    return;
  }
  shelfChapter.value = result.chapter;
  shelfChapterIndex.value =
    shelfBook.value?.chapters.findIndex((item) => item.id === chapterId) ?? -1;
  localStorage.setItem(`rhine-shelf-pos-${shelfBookId.value}`, chapterId);
  capturedBranchSelection.value = null;
  await loadShelfBranches(chapterId);
  requestAnimationFrame(resetReaderScroll);
}

async function loadShelfBranches(chapterId = shelfChapter.value?.id || ""): Promise<void> {
  if (!shelfBookId.value) {
    shelfBranches.value = [];
    return;
  }
  try {
    shelfBranches.value = (await listBookBranches(shelfBookId.value, chapterId)).branches;
    if (
      selectedShelfBranchId.value &&
      !shelfBranches.value.some((branch) => branch.branch_id === selectedShelfBranchId.value)
    ) {
      selectedShelfBranchId.value = "";
      selectedBranchPath.value = null;
    }
  } catch {
    shelfBranches.value = [];
  }
}

function openShelfAdjacentChapter(direction: -1 | 1): void {
  const chapters = shelfBook.value?.chapters ?? [];
  const next = shelfChapterIndex.value + direction;
  if (next < 0 || next >= chapters.length) {
    return;
  }
  void loadShelfChapter(chapters[next].id);
}

async function saveShelfChapter(): Promise<void> {
  const bookId = shelfBookId.value;
  const chapter = shelfChapter.value;
  if (!bookId || !chapter || shelfSaving.value) {
    return;
  }
  shelfSaving.value = true;
  try {
    const result = await saveBookChapter(bookId, chapter.id, {
      title: chapter.title,
      content: chapter.content,
    });
    shelfChapter.value = result.chapter;
    const meta = shelfBook.value?.chapters.find((item) => item.id === chapter.id);
    if (meta) {
      meta.char_count = result.chapter.char_count;
      meta.title = result.chapter.title;
    }
    markSaved("章节已保存");
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  } finally {
    shelfSaving.value = false;
  }
}

async function runShelfAiWrite(): Promise<void> {
  const bookId = shelfBookId.value;
  const chapter = shelfChapter.value;
  if (!bookId || !chapter || shelfAiBusy.value) {
    return;
  }
  shelfAiBusy.value = true;
  shelfAiResult.value = "";
  try {
    const result = await aiWriteBook({
      book_id: bookId,
      chapter_id: chapter.id,
      mode: shelfAiMode.value,
      guidance: shelfGuidance.value.trim(),
    });
    shelfAiResult.value = result.text;
    markSaved(result.offline ? "未配置 AI 通道，返回离线模板" : "AI 生成完成，可预览后应用");
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  } finally {
    shelfAiBusy.value = false;
  }
}

async function runShelfAnalysis(): Promise<void> {
  const bookId = shelfBookId.value;
  if (!bookId || shelfAnalyzeBusy.value || shelfAnalysisRunning.value) {
    return;
  }
  shelfAnalyzeBusy.value = true;
  try {
    localStorage.setItem("rhine-lore-analysis-mode", shelfAnalysisMode.value);
    const result = await startBookAnalysis(bookId, {
      mode: shelfAnalysisMode.value,
      force: shelfAnalysisForce.value,
    });
    if (shelfBookId.value !== bookId) return;
    shelfAnalysisStatus.value = result.status;
    if (result.status.plan) shelfAnalysisPlan.value = result.status.plan;
    shelfAnalysisForce.value = false;
    markSaved(result.status.offline ? "正在建立本地基础索引" : "全书分析已在后台开始");
    scheduleShelfAnalysisPoll(bookId);
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  } finally {
    shelfAnalyzeBusy.value = false;
  }
}

async function pauseShelfAnalysis(): Promise<void> {
  const bookId = shelfBookId.value;
  if (!bookId || !shelfAnalysisRunning.value) return;
  try {
    const result = await cancelBookAnalysis(bookId);
    if (shelfBookId.value === bookId) shelfAnalysisStatus.value = result.status;
    scheduleShelfAnalysisPoll(bookId);
  } catch (error) {
    toastError(error instanceof Error ? error.message : "暂停失败");
  }
}

function applyShelfAiResult(): void {
  const chapter = shelfChapter.value;
  if (!chapter || !shelfAiResult.value.trim()) {
    return;
  }
  if (shelfAiMode.value === "continue") {
    chapter.content = `${chapter.content.trim()}\n\n${shelfAiResult.value.trim()}`;
  } else {
    chapter.content = shelfAiResult.value.trim();
  }
  shelfAiResult.value = "";
  markSaved("AI 正文已应用到本章，请保存");
}

function normalizeSelectionText(value: string): {text: string; offsets: number[]} {
  let text = "";
  const offsets: number[] = [];
  let inWhitespace = false;
  for (let index = 0; index < value.length; index += 1) {
    const character = value[index];
    if (/\s/.test(character)) {
      if (!inWhitespace && text) {
        text += " ";
        offsets.push(index + 1);
      }
      inWhitespace = true;
      continue;
    }
    text += character;
    offsets.push(index + 1);
    inWhitespace = false;
  }
  return {text: text.trim(), offsets};
}

function selectedTextEndOffset(content: string, selectedText: string, approximate: number): number | null {
  const normalizedContent = normalizeSelectionText(content);
  const needle = selectedText.replace(/\s+/g, " ").trim();
  if (!needle) return null;
  const candidates: number[] = [];
  let cursor = 0;
  while (cursor < normalizedContent.text.length) {
    const found = normalizedContent.text.indexOf(needle, cursor);
    if (found < 0) break;
    const normalizedEnd = found + needle.length - 1;
    candidates.push(normalizedContent.offsets[normalizedEnd] ?? approximate);
    cursor = found + 1;
  }
  if (candidates.length === 0) return null;
  return candidates.reduce((best, candidate) =>
    Math.abs(candidate - approximate) < Math.abs(best - approximate) ? candidate : best,
  );
}

function branchSourceContent(source: BranchSource): string {
  if (source === "shelf") return shelfChapter.value?.content || "";
  return activeChapter.value?.content || "";
}

function buildBranchContext(
  source: BranchSource,
  offset: number,
  origin: BranchDraftContext["origin"],
  selectedText = "",
): BranchDraftContext | null {
  const chapter = source === "shelf" ? shelfChapter.value : activeChapter.value;
  if (!chapter) return null;
  const content = String(chapter.content || "");
  const safeOffset = Math.min(content.length, Math.max(0, Math.round(offset)));
  return {
    source,
    chapterId: chapter.id,
    chapterTitle: chapter.title,
    offset: safeOffset,
    progress: Math.round((safeOffset / Math.max(1, content.length)) * 100),
    anchor: content.slice(Math.max(0, safeOffset - 180), safeOffset),
    selectedText: selectedText.trim(),
    parentBranchId: "",
    origin,
  };
}

function captureBranchSelection(event: MouseEvent | TouchEvent): void {
  const source: BranchSource | null = readerSource.value === "shelf"
    ? "shelf"
    : readerSource.value === "novel"
      ? "project"
      : null;
  if (!source) return;
  const selection = window.getSelection();
  const root = event.currentTarget as HTMLElement | null;
  if (!selection || selection.isCollapsed || !root || !selection.rangeCount) return;
  const range = selection.getRangeAt(0);
  if (!root.contains(range.commonAncestorContainer)) return;
  const selected = selection.toString().trim();
  if (!selected) return;
  const content = branchSourceContent(source);
  const approximate = Math.round(content.length * readingProgress.value / 100);
  const offset = selectedTextEndOffset(content, selected, approximate);
  if (offset === null) return;
  capturedBranchSelection.value = buildBranchContext(source, offset, "selection", selected);
}

function openBranchDialog(context: BranchDraftContext | null): void {
  if (!context) return;
  branchContext.value = context;
  branchGuidance.value = "";
  branchKind.value = "free";
  branchResult.value = "";
  branchRecord.value = null;
  branchDialogVisible.value = true;
}

function currentReaderBranchContext(): BranchDraftContext | null {
  const source: BranchSource | null = readerSource.value === "shelf"
    ? "shelf"
    : readerSource.value === "novel"
      ? "project"
      : null;
  if (!source) return null;
  const captured = capturedBranchSelection.value;
  const chapterId = source === "shelf" ? shelfChapter.value?.id : activeChapter.value?.id;
  if (captured && captured.source === source && captured.chapterId === chapterId) {
    return captured;
  }

  const content = branchSourceContent(source);
  let approximate = Math.round(content.length * readingProgress.value / 100);
  let anchor = "";
  if (readerPageMode.value === "page" && !currentReaderPageIsTitle()) {
    const paragraph = currentReaderPage().at(-1);
    if (paragraph?.text) {
      anchor = paragraph.text.slice(-180);
      approximate = selectedTextEndOffset(content, anchor, approximate) ?? approximate;
    }
  } else if (content) {
    const nearby = content.slice(approximate, Math.min(content.length, approximate + 260));
    const sentenceEnd = nearby.search(/[。！？!?…](?:[”’」』）】])?/);
    approximate = sentenceEnd >= 0 ? approximate + sentenceEnd + 1 : approximate;
    anchor = content.slice(Math.max(0, approximate - 180), approximate);
  }
  const context = buildBranchContext(source, approximate, "position");
  if (context && anchor) context.anchor = anchor;
  return context;
}

function openReaderBranch(): void {
  openBranchDialog(currentReaderBranchContext());
}

function openShelfParagraphBranch(paragraph: string, paragraphIndex: number): void {
  const chapter = shelfChapter.value;
  if (!chapter) return;
  const paragraphs = shelfChapterParagraphs(chapter);
  let cursor = 0;
  let offset = chapter.content.length;
  for (let index = 0; index <= paragraphIndex; index += 1) {
    const value = paragraphs[index] || "";
    const found = chapter.content.indexOf(value, cursor);
    if (found >= 0) {
      offset = found + value.length;
      cursor = offset;
    }
  }
  openBranchDialog(buildBranchContext("shelf", offset, "paragraph", paragraph));
}

function openProjectBranchFromCursor(): void {
  const chapter = activeChapter.value;
  if (!chapter) return;
  const textarea = document.querySelector<HTMLTextAreaElement>(".novel-editor textarea");
  const offset = textarea?.selectionEnd ?? chapter.content.length;
  const selected = textarea && textarea.selectionStart !== textarea.selectionEnd
    ? chapter.content.slice(textarea.selectionStart, textarea.selectionEnd)
    : "";
  openBranchDialog(buildBranchContext("project", offset, "cursor", selected));
}

function branchPositionLabel(): string {
  const context = branchContext.value;
  if (!context) return "";
  const origin = {
    selection: "选中文字后",
    paragraph: "本段末尾",
    position: "当前阅读位置",
    cursor: context.selectedText ? "选中文字后" : "编辑光标处",
    branch: `第 ${selectedShelfBranch.value ? selectedShelfBranch.value.depth + 2 : 2} 层分叉`,
  }[context.origin];
  return `${context.chapterTitle} · ${origin} · ${context.progress}%`;
}

function applyBranchPreset(kind: BranchKind, guidance: string): void {
  branchKind.value = kind;
  branchGuidance.value = guidance;
}

async function generateBranchDraft(): Promise<void> {
  const context = branchContext.value;
  if (!context || branchBusy.value) return;
  branchBusy.value = true;
  branchResult.value = "";
  branchRecord.value = null;
  try {
    if (context.source === "shelf") {
      if (!shelfBookId.value) return;
      const result = await createBookBranch({
        book_id: shelfBookId.value,
        chapter_id: context.chapterId,
        offset: context.offset,
        anchor: context.anchor,
        guidance: branchGuidance.value.trim(),
        parent_branch_id: context.parentBranchId,
        kind: branchKind.value,
      });
      branchRecord.value = result.branch;
      branchResult.value = result.branch.text;
      await loadShelfBranches(context.chapterId);
      selectedShelfBranchId.value = result.branch.branch_id;
      if (branchTreeVisible.value) await selectShelfBranch(result.branch);
      markSaved(result.offline ? "分支点已保存，配置 AI 后即可生成正文" : "新分支已生成并保存");
      return;
    }

    if (!llmConfigured.value) {
      toastError("请先在设置中连接 AI，再生成分支正文");
      return;
    }
    const project = activeProject.value;
    const chapterIndex = project.chapters.findIndex((item) => item.id === context.chapterId);
    const chapter = project.chapters[chapterIndex];
    if (!chapter) return;
    const previous = project.chapters
      .slice(Math.max(0, chapterIndex - 3), chapterIndex)
      .map((item) => `《${item.title}》末尾：${item.content.slice(-700)}`)
      .join("\n\n");
    const characters = project.characters
      .slice(0, 24)
      .map((item) => `${item.name}（${item.role}）：${item.background || item.notes || item.drive}`)
      .join("\n");
    const world = project.world
      .slice(0, 18)
      .map((item) => `${item.name}（${item.type}）：${item.summary || item.details}`)
      .join("\n");
    const result = await llmServerChat([
      {
        role: "system",
        content:
          "你是中文长篇小说作者。请从指定锚点写一条新的平行分支，只输出新正文，不复述锚点前的文字，不写解释。" +
          WRITING_QUALITY_GUIDE,
      },
      {
        role: "user",
        content: [
          `项目：《${project.name}》`,
          `概要：${project.summary || "无"}`,
          characters ? `角色：\n${characters}` : "",
          world ? `世界设定：\n${world}` : "",
          previous ? `此前章节：\n${previous}` : "",
          `当前章节：《${chapter.title}》`,
          `锚点前正文：\n${chapter.content.slice(0, context.offset).slice(-4200)}`,
          `分支引导：${branchGuidance.value.trim() || "按故事自然走向继续"}`,
        ].filter(Boolean).join("\n\n"),
      },
    ]);
    branchResult.value = String(result.answer || "").trim();
    if (!branchResult.value) throw new Error("AI 没有返回分支正文");
    markSaved("工作台分支草稿已生成");
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
    toastError(error instanceof Error ? error.message : "分支生成失败");
  } finally {
    branchBusy.value = false;
  }
}

async function materializeShelfProject(branchId = ""): Promise<void> {
  if (!shelfBookId.value || branchProjectBusy.value) return;
  branchProjectBusy.value = true;
  try {
    const needsFullAnalysis =
      !shelfAnalysis.value ||
      shelfAnalysis.value.stale ||
      (shelfAnalysis.value.offline && llmConfigured.value);
    if (needsFullAnalysis && llmConfigured.value) {
      pendingShelfProjectBranchId.value = branchId;
      await runShelfAnalysis();
      toastSuccess("正在先建立全书档案，完成后会自动进入工作台");
      return;
    }
    const result = await convertBookToProject(shelfBookId.value, branchId);
    const project = normalizeProject(result.project);
    const existing = projects.value.findIndex((item) => item.id === project.id);
    if (existing >= 0) projects.value[existing] = project;
    else projects.value.push(project);
    activeProjectId.value = project.id;
    activeChapterId.value = branchId
      ? project.chapters.at(-1)?.id || project.chapters[0]?.id || ""
      : project.chapters[0]?.id || "";
    saveProjects();
    branchDialogVisible.value = false;
    branchTreeVisible.value = false;
    branchPathVisible.value = false;
    readerOverlayOpen.value = false;
    sidebarMode.value = "workbench";
    localStorage.setItem("rhine-lore-sidebar-mode", sidebarMode.value);
    activity.value = "studio";
    toastSuccess(
      `已进入工作台：${result.imported.chapters} 章、${result.imported.characters} 个角色、${result.imported.world} 项设定`,
    );
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
    toastError(error instanceof Error ? error.message : "导入工作台失败");
  } finally {
    branchProjectBusy.value = false;
  }
}

function materializeProjectBranch(): void {
  const context = branchContext.value;
  const source = activeProject.value;
  if (!context || context.source !== "project" || !branchResult.value.trim()) return;
  const sourceIndex = source.chapters.findIndex((item) => item.id === context.chapterId);
  if (sourceIndex < 0) return;
  const copy = normalizeProject(JSON.parse(JSON.stringify(source)) as Partial<StoryProject>);
  copy.id = uid("project");
  copy.name = `${source.name} · 分支`;
  copy.source_branch_id = uid("branch");
  copy.chapters = copy.chapters.slice(0, sourceIndex + 1).map((chapter, index) => ({
    ...chapter,
    id: uid("chapter"),
    content: index === sourceIndex
      ? [chapter.content.slice(0, context.offset).trimEnd(), branchResult.value.trim()].filter(Boolean).join("\n\n")
      : chapter.content,
    title: index === sourceIndex ? `${chapter.title} · 分支` : chapter.title,
  }));
  copy.chat = [];
  projects.value.push(copy);
  activeProjectId.value = copy.id;
  activeChapterId.value = copy.chapters.at(-1)?.id || "";
  saveProjects();
  branchDialogVisible.value = false;
  readerOverlayOpen.value = false;
  sidebarMode.value = "workbench";
  activity.value = "novel";
  readerMode.value = "edit";
  toastSuccess("已创建独立分支项目，原项目保持不变");
}

async function selectShelfBranch(branch: BookBranch): Promise<void> {
  if (!shelfBookId.value) return;
  selectedShelfBranchId.value = branch.branch_id;
  branchPathBusy.value = true;
  try {
    const result = await getBookBranchPath(shelfBookId.value, branch.branch_id);
    if (selectedShelfBranchId.value === branch.branch_id) selectedBranchPath.value = result.path;
  } catch (error) {
    selectedBranchPath.value = null;
    toastError(error instanceof Error ? error.message : "分支路径加载失败");
  } finally {
    branchPathBusy.value = false;
  }
}

async function openShelfBranchTree(): Promise<void> {
  branchTreeVisible.value = true;
  await loadShelfBranches();
  const selected = selectedShelfBranch.value || shelfBranches.value[0];
  if (selected) await selectShelfBranch(selected);
}

function createBranchFromTree(): void {
  branchTreeVisible.value = false;
  openReaderBranch();
}

async function openSelectedBranchPath(): Promise<void> {
  const branch = selectedShelfBranch.value;
  if (!branch) return;
  if (selectedBranchPath.value?.branch.branch_id !== branch.branch_id) {
    await selectShelfBranch(branch);
  }
  if (selectedBranchPath.value) branchPathVisible.value = true;
}

function continueShelfBranch(branch = selectedShelfBranch.value): void {
  if (!branch) return;
  branchPathVisible.value = false;
  branchContext.value = {
    source: "shelf",
    chapterId: branch.chapter_id,
    chapterTitle: branch.chapter_title,
    offset: branch.text.length,
    progress: 100,
    anchor: branch.text.slice(-180),
    selectedText: "",
    parentBranchId: branch.branch_id,
    origin: "branch",
  };
  branchGuidance.value = "";
  branchKind.value = "free";
  branchResult.value = "";
  branchRecord.value = null;
  branchDialogVisible.value = true;
}

async function removeSelectedShelfBranch(): Promise<void> {
  const branch = selectedShelfBranch.value;
  if (!branch || !shelfBookId.value) return;
  const descendants = shelfBranches.value.filter((item) => {
    if (item.branch_id === branch.branch_id) return false;
    let current: BookBranch | undefined = item;
    while (current?.parent_branch_id) {
      if (current.parent_branch_id === branch.branch_id) return true;
      current = shelfBranches.value.find((candidate) => candidate.branch_id === current?.parent_branch_id);
    }
    return false;
  }).length;
  try {
    await ElMessageBox.confirm(
      descendants
        ? `这会同时删除它下面的 ${descendants} 条后续故事线。原作正文不会改变。`
        : "删除这个故事节点？原作正文不会改变。",
      "删除分支",
      {confirmButtonText: "删除", cancelButtonText: "取消", type: "warning"},
    );
    const parentId = branch.parent_branch_id;
    const result = await deleteBookBranch(shelfBookId.value, branch.branch_id);
    await loadShelfBranches();
    const next = shelfBranches.value.find((item) => item.branch_id === parentId) || shelfBranches.value[0];
    if (next) await selectShelfBranch(next);
    else {
      selectedShelfBranchId.value = "";
      selectedBranchPath.value = null;
    }
    toastSuccess(`已删除 ${result.deleted.count} 个故事节点`);
  } catch (error) {
    if (error === "cancel" || error === "close") return;
    toastError(error instanceof Error ? error.message : "删除分支失败");
  }
}

function openSavedShelfBranch(branch: BookBranch): void {
  selectedShelfBranchId.value = branch.branch_id;
  branchContext.value = {
    source: "shelf",
    chapterId: branch.chapter_id,
    chapterTitle: branch.chapter_title,
    offset: branch.offset,
    progress: Math.round(branch.progress),
    anchor: branch.anchor,
    selectedText: "",
    parentBranchId: branch.parent_branch_id || "",
    origin: "position",
  };
  branchGuidance.value = branch.guidance;
  branchKind.value = branch.kind || "free";
  branchResult.value = branch.text;
  branchRecord.value = branch;
  branchDialogVisible.value = true;
}

async function removeShelfBook(bookId: string): Promise<void> {
  await perform("删除书", () => deleteBook(bookId));
  localStorage.removeItem(`rhine-shelf-pos-${bookId}`);
  if (shelfBookId.value === bookId) {
    clearShelfAnalysisPoll();
    shelfBook.value = null;
    shelfBookId.value = "";
    shelfChapter.value = null;
    shelfAnalysisStatus.value = null;
    shelfAnalysisPlan.value = null;
  }
  await loadShelfBooks();
}

function shelfChapterParagraphs(chapter: BookChapter): string[] {
  return splitReaderParagraphs(chapter.content ?? "");
}

function shelfProgressLabel(): string {
  const total = shelfBook.value?.chapters.length ?? 0;
  return total > 0 ? `第 ${Math.max(0, shelfChapterIndex.value + 1)} / ${total} 章` : "无章节";
}

async function refreshNovelVersions(): Promise<void> {
  const projectId = activeProject.value?.id;
  if (!projectId) {
    return;
  }
  try {
    novelVersions.value = (await listVersions("project", projectId)).versions;
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  }
}

function openNovelVersions(): void {
  novelVersionsVisible.value = true;
  void refreshNovelVersions();
}

async function commitNovelVersion(): Promise<void> {
  const project = activeProject.value;
  if (!project || versionBusy.value) {
    return;
  }
  versionBusy.value = "提交版本";
  try {
    await commitVersion(
      "project",
      project.id,
      novelVersionMessage.value.trim() || "手动提交",
      project,
    );
    novelVersionMessage.value = "";
    markSaved("版本已提交");
    toastSuccess("版本已提交");
    await refreshNovelVersions();
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  } finally {
    versionBusy.value = "";
  }
}

function requestNovelRestore(record: VersionRecord): void {
  if (
    !pendingRestoreVersion.value ||
    pendingRestoreVersion.value.snapshot_id !== record.snapshot_id
  ) {
    pendingRestoreVersion.value = {
      kind: "project",
      entity_id: record.entity_id,
      snapshot_id: record.snapshot_id,
      message: record.message,
    };
    return;
  }
  void restoreNovelVersion(record);
}

async function restoreNovelVersion(record: VersionRecord): Promise<void> {
  const projectId = activeProject.value?.id;
  if (!projectId || versionBusy.value) {
    return;
  }
  versionBusy.value = "恢复版本";
  pendingRestoreVersion.value = null;
  try {
    const result = await restoreVersion("project", projectId, record.snapshot_id);
    const payload = result.payload as unknown as StoryProject;
    if (payload?.id) {
      upsertProject(payload);
      markSaved(`已恢复到「${record.message}」`);
      toastSuccess(`已恢复到「${record.message}」`);
    }
    await refreshNovelVersions();
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  } finally {
    versionBusy.value = "";
  }
}

async function refreshShelfVersions(): Promise<void> {
  if (!shelfBookId.value) {
    return;
  }
  try {
    shelfVersions.value = (await listVersions("book", shelfBookId.value)).versions;
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  }
}

function openShelfVersions(): void {
  shelfVersionsVisible.value = true;
  void refreshShelfVersions();
}

async function commitShelfVersion(): Promise<void> {
  if (!shelfBookId.value || versionBusy.value) {
    return;
  }
  versionBusy.value = "提交版本";
  try {
    await commitVersion(
      "book",
      shelfBookId.value,
      shelfVersionMessage.value.trim() || "手动提交",
    );
    shelfVersionMessage.value = "";
    markSaved("版本已提交");
    toastSuccess("版本已提交");
    await refreshShelfVersions();
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  } finally {
    versionBusy.value = "";
  }
}

function requestShelfRestore(record: VersionRecord): void {
  if (
    !pendingRestoreVersion.value ||
    pendingRestoreVersion.value.snapshot_id !== record.snapshot_id
  ) {
    pendingRestoreVersion.value = {
      kind: "book",
      entity_id: record.entity_id,
      snapshot_id: record.snapshot_id,
      message: record.message,
    };
    return;
  }
  void restoreShelfVersion(record);
}

async function restoreShelfVersion(record: VersionRecord): Promise<void> {
  if (!shelfBookId.value || versionBusy.value) {
    return;
  }
  versionBusy.value = "恢复版本";
  pendingRestoreVersion.value = null;
  try {
    const result = await restoreVersion("book", shelfBookId.value, record.snapshot_id);
    const payload = result.payload as unknown as {book: BookDetail; chapters: BookChapter[]};
    if (payload?.book) {
      shelfBook.value = payload.book;
      const first = payload.book.chapters[0];
      if (first) {
        await loadShelfChapter(first.id);
      }
      await loadShelfBooks();
      markSaved(`已恢复到「${record.message}」`);
      toastSuccess(`已恢复到「${record.message}」`);
    }
    await refreshShelfVersions();
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  } finally {
    versionBusy.value = "";
  }
}

async function openKnowledgeIntake(): Promise<void> {
  await openActivity("context");
}

function createProject(): void {
  newProjectTemplate.value = "blank";
  newProjectName.value = "";
  newProjectGenre.value = "";
  newProjectIdea.value = "";
  createDialogVisible.value = true;
}

function confirmCreateProject(destination: CreateDestination): void {
  const project = createStoryProjectFromTemplate(newProjectTemplate.value, uid, {
    name: newProjectName.value,
    genre: newProjectGenre.value,
    summary: newProjectIdea.value,
  });
  projects.value.push(project);
  activeProjectId.value = project.id;
  activeChapterId.value = project.chapters[0]?.id ?? "";
  createDialogVisible.value = false;
  saveProjects();
  const createdMessage = newProjectTemplate.value === "gothic-fantasy" ? "奇幻演示已创建" : "故事已创建";
  markSaved(createdMessage);
  toastSuccess(createdMessage);
  if (destination === "novel") {
    readerMode.value = "edit";
  }
  activity.value = destination;
}

function selectProject(projectId: string, next: Activity = "studio"): void {
  activeProjectId.value = projectId;
  activity.value = next;
  activeChapterId.value = activeProject.value.chapters[0]?.id ?? "";
  saveProjects();
}

function handleProjectChange(): void {
  activeChapterId.value = activeProject.value.chapters[0]?.id ?? "";
  saveProjects();
}

function selectChapter(chapterId: string): void {
  activeChapterId.value = chapterId;
  localStorage.setItem(activeChapterKey, chapterId);
  resetReaderScroll();
}

function duplicateProject(): void {
  const source = activeProject.value;
  const copy = normalizeProject(JSON.parse(JSON.stringify(source)) as Partial<StoryProject>);
  copy.id = uid("project");
  copy.name = `${source.name || "未命名故事"} 副本`;
  copy.chapters = copy.chapters.map((chapter) => ({...chapter, id: uid("chapter")}));
  copy.world = copy.world.map((item) => ({...item, id: uid("world")}));
  copy.characters = copy.characters.map((item) => ({...item, id: uid("characters")}));
  copy.chat = copy.chat.map((message) => ({...message, id: uid("message")}));
  const nodeIdMap = new Map<string, string>();
  copy.map.nodes = copy.map.nodes.map((node) => {
    const nextId = uid("map-node");
    nodeIdMap.set(node.id, nextId);
    return {...node, id: nextId};
  });
  copy.map.edges = copy.map.edges.map((edge) => ({
    ...edge,
    id: uid("map-edge"),
    from: nodeIdMap.get(edge.from) ?? edge.from,
    to: nodeIdMap.get(edge.to) ?? edge.to,
  }));
  copy.issues = copy.issues.map((issue) => ({...issue, id: uid("issue")}));
  projects.value.push(copy);
  activeProjectId.value = copy.id;
  activeChapterId.value = copy.chapters[0]?.id ?? "";
  saveProjects();
  markSaved("故事已复制");
}

function exportActiveProject(): void {
  const payload = JSON.stringify(activeProject.value, null, 2);
  const blob = new Blob([payload], {type: "application/json;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const safeName = (activeProject.value.name || "rhine-lore-project").replace(/[\\/:*?"<>|]+/g, "-");
  link.href = url;
  link.download = `${safeName}.json`;
  link.click();
  URL.revokeObjectURL(url);
  markSaved("故事已导出");
}

function requestProjectImport(): void {
  projectImportInput.value?.click();
}

async function importProjectFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    return;
  }
  try {
    const raw = await file.text();
    const imported = normalizeProject(JSON.parse(raw) as Partial<StoryProject>);
    if (projects.value.some((project) => project.id === imported.id)) {
      imported.id = uid("project");
      imported.name = `${imported.name || "未命名故事"} 导入`;
    }
    projects.value.push(imported);
    activeProjectId.value = imported.id;
    activeChapterId.value = imported.chapters[0]?.id ?? "";
    saveProjects();
    markSaved("故事已导入");
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  } finally {
    input.value = "";
  }
}

function switchWorkMode(mode: WorkMode): void {
  workMode.value = mode;
  activity.value = mode === "advanced" ? "settings" : "studio";
}

function isPrimaryActivity(next: Activity): boolean {
  return primaryActivityIds.includes(next);
}

function isStudioChildActivity(next: Activity): boolean {
  return next === "studio" && storySetupActivities.includes(activity.value);
}

function startWriting(): void {
  if (activeProject.value.chapters.length === 0) {
    addChapter();
  } else if (latestChapter.value) {
    activeChapterId.value = latestChapter.value.id;
  }
  readerMode.value = "edit";
  activity.value = "novel";
}

function continueSetup(): void {
  if (!hasStoryIdentity.value) {
    activity.value = "story";
    return;
  }
  if (activeProject.value.chapters.length === 0) {
    startWriting();
    return;
  }
  activity.value = "chat";
}

function addLoreItem(): void {
  openWorldEditor(-1);
}

function removeWorldItem(item: WorldCard): void {
  const project = activeProject.value;
  const index = project.world.findIndex((entry) => entry.id === item.id);
  if (index >= 0) {
    project.world.splice(index, 1);
    saveProjects();
  }
}

function addCharacter(): void {
  openCharacterEditor(-1);
}

function hasTag(text: string, tag: string): boolean {
  return text
    .split(/[，,、;；\n]+/)
    .map((item) => item.trim())
    .includes(tag);
}

function appendTagToText(current: string, tag: string): string {
  const tags = current
    .split(/[，,、;；\n]+/)
    .map((item) => item.trim())
    .filter(Boolean);
  if (!tags.includes(tag)) {
    tags.push(tag);
  }
  return tags.join("、");
}

function applyGuidancePreset(text: string): void {
  evolutionGuidance.value = text;
  void saveEvolutionGuidance();
}

function setGlobalGuidance(text: string): void {
  activeProject.value.global_guidance = text;
  saveProjects();
  markSaved("全局引导已设置");
}

function setWritingStyle(style: string): void {
  activeProject.value.writing_style = style;
  saveProjects();
  markSaved(`文风已设为「${style}」`);
}

function buildStyleCard(): string {
  const project = activeProject.value;
  const lines: string[] = [];
  if (project.writing_style) {
    lines.push(`文风：${project.writing_style}`);
  }
  const example = project.style_example.trim();
  if (example) {
    lines.push(`风格参考（以下文字的语感、句式、节奏就是本故事的基准）：\n${example.slice(0, 800)}`);
  }
  if (project.style_notes.trim()) {
    lines.push(`风格要点：${project.style_notes.trim()}`);
  }
  if (project.style_avoid.trim()) {
    lines.push(`避免：${project.style_avoid.trim()}`);
  }
  return lines.join("\n\n");
}

function setStyleExampleFromChapter(): void {
  const chapter = activeChapter.value;
  if (!chapter || !chapter.content.trim()) {
    runState.value = {error: "当前章节还没有正文"};
    return;
  }
  activeProject.value.style_example = chapter.content.trim().slice(0, 800);
  saveProjects();
  markSaved("已把当前章节设为风格基准");
}

function fillWorldTags(item: WorldCard, tag: string): void {
  item.tags = appendTagToText(item.tags, tag);
  saveProjects();
}

function fillCharacterTraits(card: CharacterCard, tag: string): void {
  card.traits = appendTagToText(card.traits, tag);
  saveProjects();
}

function applyEvolutionStartPreset(preset: {label: string; chaos: number; branch: number}): void {
  evolutionChaos.value = preset.chaos;
  evolutionBranchFrequency.value = preset.branch;
}

function removeCharacter(card: CharacterCard): void {
  const project = activeProject.value;
  const index = project.characters.findIndex((item) => item.id === card.id);
  if (index >= 0) {
    project.characters.splice(index, 1);
    saveProjects();
  }
}

function splitTags(tags: string): string[] {
  return String(tags || "")
    .split(/[，,、;；\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function openWorldEditor(index: number): void {
  const item = index >= 0 ? activeProject.value.world[index] : null;
  worldEditIndex.value = index;
  worldDraft.value = item
    ? {...item}
    : {id: uid("world"), name: "", type: "地点", summary: "", details: "", significance: "", tags: ""};
  worldEditVisible.value = true;
}

function saveWorldEditor(): void {
  const draft = worldDraft.value;
  if (!draft.name.trim()) {
    toastError("名称不能为空");
    return;
  }
  if (worldEditIndex.value >= 0) {
    Object.assign(activeProject.value.world[worldEditIndex.value], draft);
  } else {
    activeProject.value.world.push({...draft});
  }
  saveProjects();
  worldEditVisible.value = false;
  toastSuccess(worldEditIndex.value >= 0 ? "设定已更新" : "设定已添加");
}

function createEmptyCharacterDraft(): CharacterCard {
  return {
    id: uid("character"),
    name: "",
    identity: "",
    role: "配角",
    age: "",
    stance: "",
    drive: "",
    fear: "",
    traits: "",
    abilities: "",
    weakness: "",
    secret: "",
    speech: "",
    appearance: "",
    background: "",
    relationships: [],
    status: "正常",
    notes: "",
  };
}

function openCharacterEditor(index: number): void {
  const card = index >= 0 ? activeProject.value.characters[index] : null;
  characterEditIndex.value = index;
  characterDraft.value = card ? JSON.parse(JSON.stringify(card)) : createEmptyCharacterDraft();
  characterEditVisible.value = true;
}

function saveCharacterEditor(): void {
  const draft = characterDraft.value;
  if (!draft || !draft.name.trim()) {
    toastError("姓名不能为空");
    return;
  }
  if (characterEditIndex.value >= 0) {
    Object.assign(activeProject.value.characters[characterEditIndex.value], draft);
  } else {
    activeProject.value.characters.push({...draft});
  }
  saveProjects();
  characterEditVisible.value = false;
  toastSuccess(characterEditIndex.value >= 0 ? "角色已更新" : "角色已添加");
}

function addRelationship(card: CharacterCard): void {
  card.relationships.push({name: "", relation: ""});
  saveProjects();
}

function removeRelationship(card: CharacterCard, index: number): void {
  card.relationships.splice(index, 1);
  saveProjects();
}

const mapViewBox = computed(() => {
  const width = 1000 / mapZoom.value;
  const height = 700 / mapZoom.value;
  return `0 0 ${width} ${height}`;
});

const mapSelectedNode = computed(() => {
  return activeProject.value.map.nodes.find((node) => node.id === mapSelectedNodeId.value) ?? null;
});

function mapEventPoint(event: PointerEvent): {x: number; y: number} {
  const svg = (event.currentTarget as Element).closest("svg") as SVGSVGElement | null;
  const rect = svg?.getBoundingClientRect();
  if (!svg || !rect || rect.width === 0) {
    return {x: 0, y: 0};
  }
  const parts = mapViewBox.value.split(" ").map(Number);
  return {
    x: ((event.clientX - rect.left) / rect.width) * parts[2] + parts[0],
    y: ((event.clientY - rect.top) / rect.height) * parts[3] + parts[1],
  };
}

function addMapNode(): void {
  const map = activeProject.value.map;
  const count = map.nodes.length;
  map.nodes.push({
    id: uid("map-node"),
    name: `地点${count + 1}`,
    x: 120 + (count % 4) * 220,
    y: 120 + Math.floor(count / 4) * 190,
    description: "",
  });
  saveProjects();
}

function selectMapNode(node: StoryMapNode): void {
  mapSelectedEdgeId.value = "";
  if (mapConnectMode.value) {
    if (mapPendingNodeId.value && mapPendingNodeId.value !== node.id) {
      const exists = activeProject.value.map.edges.some(
        (edge) =>
          (edge.from === mapPendingNodeId.value && edge.to === node.id) ||
          (edge.from === node.id && edge.to === mapPendingNodeId.value),
      );
      if (!exists) {
        activeProject.value.map.edges.push({
          id: uid("map-edge"),
          from: mapPendingNodeId.value,
          to: node.id,
        });
        saveProjects();
      }
      mapPendingNodeId.value = "";
    } else {
      mapPendingNodeId.value = node.id;
    }
  }
  mapSelectedNodeId.value = node.id;
}

function selectMapEdge(edge: StoryMapEdge): void {
  mapSelectedNodeId.value = "";
  mapSelectedEdgeId.value = edge.id;
}

function removeMapSelection(): void {
  const map = activeProject.value.map;
  const edgeId = mapSelectedEdgeId.value;
  if (edgeId) {
    map.edges = map.edges.filter((edge) => edge.id !== edgeId);
    mapSelectedEdgeId.value = "";
    mapPendingNodeId.value = "";
    saveProjects();
    return;
  }
  const nodeId = mapSelectedNodeId.value;
  if (!nodeId) {
    return;
  }
  map.nodes = map.nodes.filter((node) => node.id !== nodeId);
  map.edges = map.edges.filter((edge) => edge.from !== nodeId && edge.to !== nodeId);
  mapSelectedNodeId.value = "";
  mapSelectedEdgeId.value = "";
  mapPendingNodeId.value = "";
  saveProjects();
}

function onMapNodePointerDown(node: StoryMapNode, event: PointerEvent): void {
  const svg = (event.currentTarget as Element).closest("svg");
  svg?.setPointerCapture?.(event.pointerId);
  const point = mapEventPoint(event);
  mapDragging.value = {id: node.id, dx: node.x - point.x, dy: node.y - point.y};
}

function onMapSvgPointerDown(event: PointerEvent): void {
  if ((event.target as Element).tagName !== "svg") {
    return;
  }
  if (mapConnectMode.value) {
    return;
  }
  mapSelectedNodeId.value = "";
  mapSelectedEdgeId.value = "";
  mapPendingNodeId.value = "";
}

function onMapPointerMove(event: PointerEvent): void {
  const dragging = mapDragging.value;
  if (!dragging) {
    return;
  }
  const point = mapEventPoint(event);
  const node = activeProject.value.map.nodes.find((item) => item.id === dragging.id);
  if (node) {
    node.x = Math.max(24, Math.min(976, Math.round(point.x + dragging.dx)));
    node.y = Math.max(24, Math.min(676, Math.round(point.y + dragging.dy)));
    saveProjects();
  }
}

function onMapPointerUp(): void {
  mapDragging.value = null;
}

function mapNodeX(nodeId: string): number {
  return activeProject.value.map.nodes.find((node) => node.id === nodeId)?.x ?? 0;
}

function mapNodeY(nodeId: string): number {
  return activeProject.value.map.nodes.find((node) => node.id === nodeId)?.y ?? 0;
}

function mapZoomIn(): void {
  mapZoom.value = Math.min(2, Number((mapZoom.value * 1.2).toFixed(2)));
}

function mapZoomOut(): void {
  mapZoom.value = Math.max(0.5, Number((mapZoom.value / 1.2).toFixed(2)));
}

function placeWorldOnMap(item: WorldCard): void {
  const map = activeProject.value.map;
  const existing = map.nodes.find((node) => node.name === item.name);
  if (existing) {
    mapSelectedNodeId.value = existing.id;
    activity.value = "map";
    markSaved("该地点已在地图上");
    return;
  }
  const count = map.nodes.length;
  map.nodes.push({
    id: uid("map-node"),
    name: item.name,
    x: 120 + (count % 4) * 220,
    y: 120 + Math.floor(count / 4) * 190,
    description: item.summary || item.details.slice(0, 80),
  });
  saveProjects();
  markSaved("已放置到地图");
  activity.value = "map";
}

function addChapter(): void {
  const project = activeProject.value;
  const chapter: Chapter = {
    id: uid("chapter"),
    title: `第${project.chapters.length + 1}章`,
    content: "",
  };
  project.chapters.push(chapter);
  activeChapterId.value = chapter.id;
  saveProjects();
}

function appendChat(role: CreativeMessage["role"], content: string): CreativeMessage {
  const message: CreativeMessage = {
    id: uid("message"),
    role,
    content,
    created_at: new Date().toISOString(),
  };
  activeProject.value.chat.push(message);
  saveProjects();
  return message;
}

function buildCreativePrompt(userText: string): string {
  const chapter = activeChapter.value;
  const world = activeProject.value.world
    .slice(0, 5)
    .map((item) =>
      [
        `${item.name}（${item.type}）`,
        item.summary,
        item.details,
        item.significance ? `意义：${item.significance}` : "",
      ]
        .filter(Boolean)
        .join("；"),
    )
    .join("\n");
  const characters = activeProject.value.characters
    .slice(0, 5)
    .map((card) =>
      [
        `${card.name}（${card.role}${card.identity ? ` · ${card.identity}` : ""}）`,
        card.drive ? `欲望：${card.drive}` : "",
        card.fear ? `恐惧：${card.fear}` : "",
        card.traits ? `性格：${card.traits}` : "",
        card.relationships.length > 0
          ? `关系：${card.relationships.map((relation) => `${relation.name || "?"}（${relation.relation || "?"}）`).join("；")}`
          : "",
      ]
        .filter(Boolean)
        .join("；"),
    )
    .join("\n");
  const selectedReferences = selectedKnowledgeNodes.value
    .slice(0, 6)
    .map((item) => `${recordTitle(item)}: ${String(item.content ?? item.summary ?? "").slice(0, 700)}`)
    .join("\n");
  return [
    `项目：${activeProject.value.name}`,
    `类型：${activeProject.value.genre}`,
    `概要：${activeProject.value.summary}`,
    world ? `世界观：\n${world}` : "",
    characters ? `角色：\n${characters}` : "",
    selectedReferences ? `选中的资料库参考：\n${selectedReferences}` : "",
    chapter ? `当前章节：${chapter.title}\n${chapter.content.slice(0, 1200)}` : "",
    `创作请求：${userText}`,
  ].filter(Boolean).join("\n\n");
}

function extractAssistantText(payload: ApiRecord, fallback: string): string {
  const candidates = [
    payload.answer,
    payload.content,
    payload.text,
    payload.message,
    payload.response,
  ];
  const found = candidates.find((value) => typeof value === "string" && value.trim());
  if (found) {
    const text = String(found);
    if (text.startsWith("FakeLLM answer for:")) {
      return fallback;
    }
    return text;
  }
  return fallback;
}

function localCreativeDraft(userText: string): string {
  const chapter = activeChapter.value;
  const chapterTitle = chapter?.title ?? "新章节";
  return [
    `《${chapterTitle}》续写草稿`,
    "",
    "雨声停得太突然，走廊里只剩下通风管道低低的回响。",
    "",
    "“你也听见了？”她没有回头，指尖却已经按在记录本的锁扣上。",
    "",
    "门外的人停在半明半暗的灯下，声音比脚步更轻：“我听见的不是脚步，是有人在念你的名字。”",
    "",
    "她终于转身。那人手里没有武器，只有一张被雨水泡皱的旧照片。照片背面写着一行字：不要相信今晚醒来的人。",
    "",
    `本轮请求：${userText}`,
  ].join("\n");
}

async function sendCreativeMessage(): Promise<void> {
  const text = chatInput.value.trim();
  if (!text) {
    return;
  }
  appendChat("user", text);
  chatInput.value = "";
  const prompt = buildCreativePrompt(text);
  const fallback = localCreativeDraft(text);
  const styleCard = buildStyleCard();
  const attachments = chatAttachment.value ? [chatAttachment.value] : [];
  let result: any = null;
  chatThinking.value = true;
  streamingChatText.value = "";
  try {
    result = await perform("对话创作", async () => {
      if (llmConfigured.value) {
        let fullText = "";
        let revealed = 0;
        let revealTimer: ReturnType<typeof setInterval> | undefined;
        revealTimer = setInterval(() => {
          if (revealed >= fullText.length) {
            return;
          }
          const step = Math.max(3, Math.ceil(fullText.length / 150));
          revealed = Math.min(fullText.length, revealed + step);
          streamingChatText.value = fullText.slice(0, revealed);
          void scrollChatToBottom();
        }, 16);
        try {
          const streamed = await llmServerChatStream(
            [
              {
                role: "system",
                content:
                  "你是 Rhine-Lore 的创作助手：基于用户给出的世界观、角色与章节续写或讨论剧情，不要编造未提供的设定。" +
                  (styleCard ? `\n风格基准（必须严格遵守）：\n${styleCard}` : "") +
                  WRITING_QUALITY_GUIDE,
              },
              {role: "user", content: prompt},
            ],
            attachments,
            (event) => {
              if (event.type === "delta") {
                fullText += event.text;
              }
            },
          );
          if (revealTimer) {
            clearInterval(revealTimer);
          }
          revealed = fullText.length;
          streamingChatText.value = fullText;
          return {answer: streamed.answer, actions: streamed.actions};
        } finally {
          if (revealTimer) {
            clearInterval(revealTimer);
          }
        }
      }
      return fakeCreativeAnswer({
        query: prompt,
        profile_id: profileId.value,
        result_limit: resultLimit.value,
        tags: ["lore"],
      });
    });
  } finally {
    chatThinking.value = false;
    streamingChatText.value = "";
  }
  let reply = result ? extractAssistantText(result, fallback) : fallback;
  if (reply && reply !== fallback && activeProject.value.polish_writing && llmConfigured.value) {
    notice.value = "正在润色…";
    try {
      const polished = await llmServerChat([
        {
          role: "system",
          content:
            "你是中文小说润色编辑。保持事件、设定、人物与时间线完全不变，只提升文学质感、节奏与细节，删除 AI 腔套话。" +
            (styleCard ? `风格基准（润色后必须保持）：${styleCard}` : "") +
            WRITING_QUALITY_GUIDE,
        },
        {role: "user", content: `请润色以下正文，直接输出润色后的完整正文，不要解释：\n\n${reply}`},
      ]);
      const polishedText = polished ? String(polished.answer ?? "").trim() : "";
      if (polishedText) {
        reply = polishedText;
      }
    } catch {
      // 润色失败时保留原稿
    }
  }
  appendChat("assistant", reply);
  if (result?.actions && result.actions.length > 0) {
    const last = activeProject.value.chat[activeProject.value.chat.length - 1];
    if (last) {
      last.actions = result.actions;
    }
    const pending = result.actions.find((action: AgentToolAction) => action.pending);
    if (pending) {
      pendingAgentAction.value = pending;
    } else {
      await applyAgentActions(result.actions);
    }
  }
  chatAttachment.value = null;
  saveProjects();
}

async function confirmAgentAction(): Promise<void> {
  const action = pendingAgentAction.value;
  if (!action) {
    return;
  }
  pendingAgentAction.value = null;
  const args: Record<string, unknown> = {...action.args};
  if (
    ["append_chapter", "add_character", "add_world_card"].includes(action.tool) &&
    !args.project_id
  ) {
    args.project_id = activeProject.value.id;
  }
  try {
    const executed = await perform(`执行「${toolActionLabel(action.tool)}」`, () =>
      executeAgentTool(action.tool, args),
    );
    if (executed) {
      await applyAgentActions([
        {tool: action.tool, args, result: executed.result as ApiRecord},
      ]);
      appendChat("assistant", `已执行「${toolActionLabel(action.tool)}」。`);
      saveProjects();
      toastSuccess(`已执行「${toolActionLabel(action.tool)}」`);
      markSaved(
        `AI 操作已执行并同步到本地${executed.snapshot ? "（执行前已自动备份）" : ""}`,
      );
    }
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
    toastError(error instanceof Error ? error.message : String(error));
  }
}

function discardAgentAction(): void {
  pendingAgentAction.value = null;
}

function adjustAgentAction(): void {
  const action = pendingAgentAction.value;
  pendingAgentAction.value = null;
  if (!action) {
    return;
  }
  chatInput.value = `请调整刚才的「${toolActionLabel(action.tool)}」建议，说明哪里不合适：`;
}

function handleChatAttach(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    return;
  }
  const reader = new FileReader();
  reader.onload = async () => {
    const text = String(reader.result ?? "");
    if (text.length > 500000) {
      runState.value = {error: "附件过大（超过 500KB），请拆分后重试"};
      return;
    }
    const kind = /\.json$/i.test(file.name)
      ? ("project" as const)
      : /\.txt$/i.test(file.name)
        ? ("txt" as const)
        : ("knowledge" as const);
    chatAttachment.value = {name: file.name, kind, text};
    markSaved(`已附加 ${file.name}，发送后 AI 可以读取并执行导入等操作`);
  };
  reader.readAsText(file, "utf-8");
  input.value = "";
}

function removeChatAttachment(): void {
  chatAttachment.value = null;
}

function handleChatKeydown(event: KeyboardEvent): void {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    void sendCreativeMessage();
  }
}

async function copyChatText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
    markSaved("已复制到剪贴板");
  } catch {
    runState.value = {error: "复制失败，请手动选择复制"};
  }
}

function chatTime(iso: string): string {
  if (!iso) {
    return "";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleTimeString("zh-CN", {hour: "2-digit", minute: "2-digit"});
}

async function scrollChatToBottom(): Promise<void> {
  await nextTick();
  const el = chatThreadRef.value;
  if (el) {
    el.scrollTop = el.scrollHeight;
  }
}

watch(
  () => activeProject.value.chat.length,
  () => void scrollChatToBottom(),
);
watch(chatThinking, () => void scrollChatToBottom());

watch(
  [
    activity,
    readerMode,
    () => activeChapter.value?.id,
    readerFontSize,
    readerLineHeight,
    readerParagraphSpacing,
    readerFontFamily,
    readerJustify,
    readerIndent,
    readerMeasure,
    readerPageMode,
  ],
  () => {
    if (readerPageMode.value !== "page") {
      return;
    }
    readerPageIndex.value = 0;
    void repaginate();
  },
);

watch(readerOverlayOpen, async (open) => {
  await nextTick();
  bindReaderScrollListener(open ? readerScrollContainer() : null);
});

function bindReaderScrollListener(element: HTMLElement | null): void {
  if (readerBoundScrollElement === element) return;
  readerBoundScrollElement?.removeEventListener("scroll", handleReadingScroll);
  readerBoundScrollElement = element;
  readerBoundScrollElement?.addEventListener("scroll", handleReadingScroll, {passive: true});
}

function upsertProject(project: StoryProject): void {
  const normalized = normalizeProject(project);
  const index = projects.value.findIndex((item) => item.id === normalized.id);
  if (index >= 0) {
    projects.value[index] = normalized;
  } else {
    projects.value.push(normalized);
  }
  if (!activeProjectId.value) {
    activeProjectId.value = normalized.id;
  }
  saveProjects();
}

async function applyAgentActions(actions: AgentToolAction[]): Promise<void> {
  let changed = false;
  for (const action of actions) {
    const result = action.result;
    if (result && typeof result.project === "object" && result.project) {
      upsertProject(result.project as StoryProject);
      changed = true;
    }
    if (
      action.tool === "import_txt" ||
      action.tool === "append_book_chapter" ||
      action.tool === "list_books"
    ) {
      await loadShelfBooks();
      changed = true;
    }
    if (action.tool === "save_knowledge") {
      await refreshReview();
      changed = true;
    }
  }
  if (changed) {
    markSaved("AI 已执行操作并同步到本地");
  }
}

const pendingIssueCount = computed(() => {
  return activeProject.value.issues.filter((issue) => issue.status === "待处理").length;
});

function revisionOriginalText(revision: {chapter_id: string; chapter_title?: string}): string {
  const project = activeProject.value;
  return (
    project.chapters.find((chapter) => chapter.id === revision.chapter_id)?.content ??
    project.chapters.find((chapter) => chapter.title === revision.chapter_title)?.content ??
    ""
  );
}

function buildRevisionMessages(instruction: string, threadsText: string): LlmChatMessage[] {
  const project = activeProject.value;
  const chaptersText = project.chapters
    .map((chapter) => `【章节：${chapter.title}】\n${chapter.content.slice(0, 2500)}`)
    .join("\n\n");
  const charactersText = project.characters
    .map(
      (card) =>
        `${card.name}（${card.role}）：身份=${card.identity || "未设定"}；欲望=${card.drive || "未设定"}；恐惧=${card.fear || "未设定"}；关系=${card.relationships.map((relation) => `${relation.name}(${relation.relation})`).join("、") || "暂无"}；秘密=${card.secret || "无"}；状态=${card.status}`,
    )
    .join("\n");
  const worldText = project.world
    .map((item) => `${item.name}（${item.type}）：${item.summary || item.details.slice(0, 120)}`)
    .join("\n");
  const system =
    "你是小说的修订编辑与设定管理员。根据用户指令修改已有正文，并对照角色卡、世界观、伏笔清单和所有章节评估整体影响。" +
    "必须只输出一个 JSON 对象，不要输出任何其他文字。格式：" +
    '{"revisions":[{"chapter_id":"...","chapter_title":"...","revised_text":"修订后的完整章节正文"}],"evaluation":[{"kind":"冲突|误区|不一致|提醒","item":"问题一句话","reason":"依据（哪条设定或哪一章）","suggestion":"处理建议"}]}。' +
    "如果没有需要修改的章节，revisions 为空数组；局部修改时 revised_text 必须是包含修改后的完整章节正文。" +
    (buildStyleCard() ? `\n风格基准（修订后必须保持）：\n${buildStyleCard()}` : "") +
    WRITING_QUALITY_GUIDE;
  const user = [
    `调整指令：${instruction}`,
    `项目：《${project.name}》 类型：${project.genre} 概要：${project.summary || "未设定"}`,
    `全局引导：${project.global_guidance || "无"}`,
    `当前激活章节：${activeChapter.value?.title ?? "无"}`,
    `全部章节：\n${chaptersText || "暂无"}`,
    `角色卡：\n${charactersText || "暂无"}`,
    `世界观：\n${worldText || "暂无"}`,
    threadsText ? `活跃线索与伏笔：\n${threadsText}` : "活跃线索与伏笔：暂无",
  ].join("\n\n");
  return [
    {role: "system", content: system},
    {role: "user", content: user},
  ];
}

function parseRevisionResult(text: string): RevisionResult | null {
  let cleaned = String(text || "").trim();
  const fence = cleaned.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fence) {
    cleaned = fence[1].trim();
  }
  const start = cleaned.indexOf("{");
  const end = cleaned.lastIndexOf("}");
  if (start < 0 || end <= start) {
    return null;
  }
  try {
    const data = JSON.parse(cleaned.slice(start, end + 1));
    const kinds: ManuscriptIssue["kind"][] = ["冲突", "误区", "不一致", "提醒"];
    const revisions = Array.isArray(data.revisions)
      ? data.revisions
          .filter((revision: any) => typeof revision?.revised_text === "string" && revision.revised_text.trim())
          .map((revision: any) => ({
            chapter_id: String(revision.chapter_id || ""),
            chapter_title: String(revision.chapter_title || ""),
            revised_text: String(revision.revised_text).trim(),
          }))
      : [];
    const evaluation = Array.isArray(data.evaluation)
      ? data.evaluation
          .slice(0, 20)
          .map((entry: any) => ({
            id: uid("issue"),
            kind: kinds.includes(String(entry?.kind) as ManuscriptIssue["kind"])
              ? (String(entry?.kind) as ManuscriptIssue["kind"])
              : "提醒",
            item: String(entry?.item || entry?.title || "未命名问题"),
            reason: String(entry?.reason || ""),
            suggestion: String(entry?.suggestion || ""),
            status: "待处理" as const,
            created_at: new Date().toISOString(),
          }))
      : [];
    return {revisions, evaluation};
  } catch {
    return null;
  }
}

async function generateRevision(): Promise<void> {
  const instruction = adjustInput.value.trim();
  if (!instruction || revisionBusy.value) {
    return;
  }
  if (!llmConfigured.value) {
    runState.value = {error: "调整正文需要 AI 通道，请先在首页或右上角配置 API Key"};
    return;
  }
  revisionBusy.value = true;
  revisionPreview.value = null;
  let threadsText = "";
  try {
    const view = await getEvolutionState(activeProject.value.id, evolutionViewpoint.value || "");
    threadsText = view.state.threads
      .filter((thread) => thread.status === "active")
      .slice(0, 8)
      .map((thread) => `【${thread.kind}】${thread.title}${thread.secret ? `：${thread.secret}` : ""}`)
      .join("\n");
  } catch {
    // 没有演化存档不影响正文修订
  }
  const result = await perform("生成修订与评估", () =>
    llmServerChat(buildRevisionMessages(instruction, threadsText)),
  );
  revisionBusy.value = false;
  if (!result) {
    return;
  }
  const parsed = parseRevisionResult(String(result.answer ?? ""));
  if (!parsed) {
    runState.value = {error: "AI 返回无法解析，请简化指令后重试"};
    return;
  }
  revisionPreview.value = parsed;
  markSaved(`修订生成完毕：${parsed.revisions.length} 处改动，${parsed.evaluation.length} 项评估`);
}

function applyRevision(): void {
  const preview = revisionPreview.value;
  if (!preview) {
    return;
  }
  let applied = 0;
  for (const revision of preview.revisions) {
    const target =
      activeProject.value.chapters.find((chapter) => chapter.id === revision.chapter_id) ??
      (revision.chapter_title
        ? activeProject.value.chapters.find((chapter) => chapter.title === revision.chapter_title)
        : undefined);
    if (!target) {
      continue;
    }
    target.content = revision.revised_text;
    if (revision.chapter_title) {
      target.title = revision.chapter_title;
    }
    applied += 1;
  }
  if (applied === 0) {
    runState.value = {error: "没有匹配到章节，未应用任何修订"};
    return;
  }
  if (preview.evaluation.length > 0) {
    activeProject.value.issues.push(...preview.evaluation);
  }
  saveProjects();
  markSaved(`已应用 ${applied} 处修订，新增 ${preview.evaluation.length} 项待处理`);
  revisionPreview.value = null;
}

function discardRevision(): void {
  revisionPreview.value = null;
  adjustInput.value = "";
}

function setIssueStatus(issue: ManuscriptIssue, status: ManuscriptIssue["status"]): void {
  issue.status = status;
  saveProjects();
}

function removeIssue(issue: ManuscriptIssue): void {
  const index = activeProject.value.issues.findIndex((item) => item.id === issue.id);
  if (index >= 0) {
    activeProject.value.issues.splice(index, 1);
    saveProjects();
  }
}

function insertMessageIntoChapter(message: CreativeMessage): void {
  let chapter = activeChapter.value;
  if (!chapter) {
    addChapter();
    chapter = activeChapter.value;
  }
  if (!chapter) {
    return;
  }
  chapter.content = [chapter.content.trim(), message.content.trim()].filter(Boolean).join("\n\n");
  saveProjects();
  markSaved("已插入正文");
  readerMode.value = "edit";
  activity.value = "novel";
}

function clearProjectChat(): void {
  activeProject.value.chat = [];
  saveProjects();
}

function usePromptStarter(text: string): void {
  chatInput.value = text;
}

function toolActionLabel(tool: string): string {
  const labels: Record<string, string> = {
    import_txt: "导入 TXT",
    create_project: "新建项目",
    append_chapter: "追加章节",
    add_character: "添加角色",
    update_character: "调整角色",
    delete_character: "删除角色",
    add_world_card: "添加设定",
    update_world_card: "调整设定",
    delete_world_card: "删除设定",
    update_chapter: "修改章节",
    delete_chapter: "删除章节",
    update_project: "修改项目",
    list_projects: "查看项目",
    export_project: "导出项目",
    export_book: "导出书",
    merge_chapters: "合并章节",
    evolution_start: "新建演化",
    evolution_advance: "推进演化",
    evolution_guidance: "设置引导",
    evolution_reset: "重置演化",
    get_llm_config: "查看 AI 配置",
    get_server_status: "查看服务状态",
    update_llm_config: "修改 AI 配置",
    save_knowledge: "保存资料",
    append_book_chapter: "追加书章",
    list_books: "查看书架",
    load_project: "读取项目",
  };
  return labels[tool] || tool;
}

function recordId(record: ApiRecord): string {
  return String(record.node_id ?? record.id ?? record.title ?? record.proposal_id ?? record.entry_id ?? "");
}

function recordTitle(record: ApiRecord): string {
  return String(record.title ?? record.node_id ?? record.id ?? "未命名资料");
}

function recordPreview(record: ApiRecord, length = 96): string {
  const raw = String(record.content ?? record.summary ?? record.text ?? record.markdown ?? "");
  return preview(splitKnowledgeEnvelope(raw, recordTitle(record)).body, length);
}

function normalizeTags(value: unknown): string[] {
  return Array.isArray(value)
    ? value.map((tag) => String(tag).trim()).filter(Boolean)
    : [];
}

function normalizeKnowledgeProposal(proposal: ApiRecord): KnowledgeReviewItem[] {
  const status = String(proposal.status ?? "draft").toLowerCase();
  if (!["draft", "pending_review"].includes(status)) {
    return [];
  }
  const proposalId = String(proposal.proposal_id ?? "");
  const proposedNodes = Array.isArray(proposal.proposed_nodes) && proposal.proposed_nodes.length > 0
    ? proposal.proposed_nodes as ApiRecord[]
    : [proposal];
  return proposedNodes.map((node, index) => {
    const temporaryId = String(node.temporary_id ?? `node-${index}`);
    return {
      key: `draft:${proposalId}:${temporaryId}`,
      stage: "draft",
      proposalId,
      temporaryId,
      nodeId: String(node.node_id ?? "") || undefined,
      title: String(node.title ?? proposal.title ?? "未命名草稿"),
      nodeType: String(node.node_type ?? proposal.node_type ?? "Note"),
      content: String(node.content ?? proposal.content ?? ""),
      authority: String(node.authority ?? proposal.authority ?? "experimental"),
      tags: normalizeTags(node.tags ?? proposal.tags),
      createdAt: String(node.created_at ?? proposal.created_at ?? ""),
    };
  });
}

function normalizeKnowledgeStaging(entry: ApiRecord): KnowledgeReviewItem {
  const entryId = String(entry.entry_id ?? entry.id ?? "");
  const proposedNode = entry.proposed_node && typeof entry.proposed_node === "object"
    ? entry.proposed_node as ApiRecord
    : entry;
  const baseRevision = entry.base_revision === null || entry.base_revision === undefined
    ? Number.NaN
    : Number(entry.base_revision);
  return {
    key: `ready:${entryId}`,
    stage: "ready",
    proposalId: String(entry.proposal_id ?? ""),
    temporaryId: String(entry.source_temporary_id ?? ""),
    entryId,
    nodeId: String(proposedNode.node_id ?? entry.node_id ?? "") || undefined,
    baseRevision: Number.isFinite(baseRevision) ? baseRevision : undefined,
    title: String(proposedNode.title ?? entry.title ?? "未命名资料"),
    nodeType: String(proposedNode.node_type ?? entry.node_type ?? "Note"),
    content: String(proposedNode.content ?? entry.content ?? ""),
    authority: String(proposedNode.authority ?? entry.authority ?? "experimental"),
    tags: normalizeTags(proposedNode.tags ?? entry.tags),
    createdAt: String(entry.created_at ?? ""),
  };
}

function normalizeKnowledgeNode(node: ApiRecord): KnowledgeReviewItem {
  const nodeId = recordId(node);
  return {
    key: `library:${nodeId}`,
    stage: "library",
    nodeId,
    revision: Number(node.revision) || 1,
    title: recordTitle(node),
    nodeType: String(node.node_type ?? "Note"),
    content: String(node.content ?? ""),
    authority: String(node.authority ?? ""),
    tags: normalizeTags(node.tags),
    createdAt: String(node.updated_at ?? node.created_at ?? ""),
  };
}

function splitKnowledgeEnvelope(content: string, title = ""): {body: string; metadata: string} {
  const match = content.match(/\r?\n---\r?\n(?=来源[:：])/);
  const main = match?.index === undefined ? content : content.slice(0, match.index);
  const metadata = match?.index === undefined ? "" : content.slice(match.index + match[0].length).trim();
  const heading = title.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const withoutHeading = heading
    ? main.replace(new RegExp(`^\\s*#\\s+${heading}\\s*(?:\\r?\\n)+`, "i"), "")
    : main;
  return {body: withoutHeading.trim(), metadata};
}

function parseKnowledgeSource(content: string): KnowledgeSourceInfo {
  const {metadata} = splitKnowledgeEnvelope(content);
  const info: KnowledgeSourceInfo = {
    kind: "",
    project: "",
    projectId: "",
    chapter: "",
    chapterId: "",
    messageIds: [],
    excerpts: [],
    metadata,
  };
  if (!metadata) {
    return info;
  }
  let readingExcerpts = false;
  for (const rawLine of metadata.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (/^来源摘录[:：]?/.test(line)) {
      readingExcerpts = true;
      continue;
    }
    if (readingExcerpts && line.startsWith("- ")) {
      info.excerpts.push(line.slice(2).trim());
      continue;
    }
    readingExcerpts = false;
    const value = (label: string) => line.replace(new RegExp(`^${label}[:：]\\s*`), "").trim();
    if (/^来源[:：]/.test(line)) info.kind = value("来源");
    if (/^项目 ID[:：]/.test(line)) info.projectId = value("项目 ID");
    if (/^项目[:：]/.test(line)) info.project = value("项目");
    if (/^章节 ID[:：]/.test(line)) info.chapterId = value("章节 ID");
    if (/^章节[:：]/.test(line)) info.chapter = value("章节");
    if (/^来源消息[:：]/.test(line)) {
      info.messageIds = value("来源消息").split(/[,，]\s*/).filter(Boolean);
    }
  }
  return info;
}

function resolveKnowledgeSourceTarget(source: KnowledgeSourceInfo): KnowledgeSourceTarget {
  let project = projects.value.find((item) => item.id === source.projectId) ?? null;
  if (!project && source.project) {
    project = projects.value.find((item) => item.name === source.project) ?? null;
  }
  if (!project && source.messageIds.length > 0) {
    project = projects.value.find((item) =>
      item.chat.some((message) => source.messageIds.includes(message.id)),
    ) ?? null;
  }
  const chapter = project
    ? project.chapters.find((item) => item.id === source.chapterId)
      ?? project.chapters.find((item) => item.title === source.chapter)
      ?? null
    : null;
  const messageId = project
    ? source.messageIds.find((id) => project?.chat.some((message) => message.id === id)) ?? ""
    : "";
  return {project, chapter, messageId};
}

async function jumpToKnowledgeSource(destination: "chat" | "chapter"): Promise<void> {
  const target = activeKnowledgeSourceTarget.value;
  if (!target.project) {
    ElMessage.warning("原项目已不在当前设备，可以继续查看保留的来源摘录");
    return;
  }
  if (destination === "chapter" && !target.chapter) {
    ElMessage.warning("原章节已不存在，可以继续查看保留的来源摘录");
    return;
  }
  if (destination === "chat" && !target.messageId) {
    ElMessage.warning("原对话已不在当前设备，可以继续查看保留的来源摘录");
    return;
  }
  activeProjectId.value = target.project.id;
  const nextChapterId = target.chapter?.id ?? target.project.chapters[0]?.id ?? "";
  activeChapterId.value = nextChapterId;
  localStorage.setItem(activeProjectKey, target.project.id);
  localStorage.setItem(activeChapterKey, nextChapterId);
  knowledgeReviewVisible.value = false;
  if (destination === "chapter") {
    readerMode.value = "edit";
    activity.value = "novel";
    resetReaderScroll();
    markSaved(`已打开《${target.chapter?.title || "原章节"}》`);
    return;
  }
  activity.value = "chat";
  await nextTick();
  await nextTick();
  const messageElement = Array.from(
    chatThreadRef.value?.querySelectorAll<HTMLElement>("[data-message-id]") ?? [],
  ).find((element) => element.dataset.messageId === target.messageId);
  if (!messageElement) {
    ElMessage.warning("已打开原项目，但没有找到对应消息");
    return;
  }
  highlightedKnowledgeMessageId.value = target.messageId;
  messageElement.scrollIntoView({behavior: "smooth", block: "center"});
  window.setTimeout(() => {
    if (highlightedKnowledgeMessageId.value === target.messageId) {
      highlightedKnowledgeMessageId.value = "";
    }
  }, 3600);
  markSaved("已定位到资料来源");
}

function knowledgeEditableBody(item: KnowledgeReviewItem): string {
  return splitKnowledgeEnvelope(item.content, item.title).body;
}

function composeKnowledgeContent(item: KnowledgeReviewItem, title: string, body: string): string {
  const {metadata} = splitKnowledgeEnvelope(item.content, item.title);
  if (!metadata) {
    return body.trim();
  }
  return [`# ${title.trim()}`, "", body.trim(), "", "---", metadata].join("\n");
}

function coexistNodeId(item: KnowledgeReviewItem): string {
  const existing = knowledgeCoexistNodeIds.value[item.key];
  if (existing) return existing;
  const suffix = uid("lore").toLocaleLowerCase().replace(/[^a-z0-9-]+/g, "-");
  const nodeId = `${workspaceId}.${suffix}`.slice(0, 126).replace(/[^a-z0-9]$/g, "0");
  knowledgeCoexistNodeIds.value = {...knowledgeCoexistNodeIds.value, [item.key]: nodeId};
  return nodeId;
}

function mergeKnowledgeBodies(target: KnowledgeReviewItem, draftTitle: string, draftBody: string): string {
  const currentBody = knowledgeEditableBody(target).trim();
  const addition = draftBody.trim();
  if (!currentBody) return addition;
  if (!addition || currentBody === addition || currentBody.includes(addition)) return currentBody;
  return [currentBody, `## 补充：${draftTitle.trim()}`, addition].join("\n\n");
}

function selectKnowledgeConflictTarget(item: KnowledgeReviewItem): void {
  if (item.stage !== "library") return;
  knowledgeConflictTargetKey.value = item.key;
  const activeKey = activeKnowledgeReviewItem.value?.key;
  if (activeKey) {
    knowledgeConflictTargets.value = {...knowledgeConflictTargets.value, [activeKey]: item.key};
  }
}

function selectKnowledgeConflictMode(mode: KnowledgeConflictMode): void {
  if (mode !== "coexist" && !activeKnowledgeConflictTarget.value) {
    ElMessage.info("先从相似资料中选择一条已入库资料");
    return;
  }
  knowledgeConflictMode.value = mode;
  const activeKey = activeKnowledgeReviewItem.value?.key;
  if (activeKey) {
    knowledgeConflictModes.value = {...knowledgeConflictModes.value, [activeKey]: mode};
  }
}

function knowledgeReviewPatch(item: KnowledgeReviewItem): {
  node_id: string;
  title: string;
  node_type: string;
  content: string;
  authority: string;
  tags: string[];
} {
  const form = knowledgeReviewForm.value;
  const target = activeKnowledgeConflictTarget.value;
  const mode = target ? knowledgeConflictMode.value : "coexist";
  let title = form.title.trim();
  let nodeType = form.nodeType;
  let body = form.body.trim();
  let nodeId = coexistNodeId(item);
  if (mode === "merge" && target?.nodeId) {
    title = target.title;
    nodeType = target.nodeType;
    body = mergeKnowledgeBodies(target, form.title, body);
    nodeId = target.nodeId;
  } else if (mode === "replace" && target?.nodeId) {
    nodeId = target.nodeId;
  }
  let content = composeKnowledgeContent(item, title, body);
  if (mode !== "coexist" && target) {
    const action = mode === "merge" ? "合并" : "覆盖";
    content = `${content}\n处理记录：${action}自 ${target.nodeId} rev ${target.revision ?? 1}`;
  }
  return {
    node_id: nodeId,
    title,
    node_type: nodeType,
    content,
    authority: form.authority === "project" ? "approved" : form.authority || "experimental",
    tags: parseKnowledgeReviewTags(),
  };
}

function similarityTokens(value: string): Set<string> {
  const clean = value.toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu, " ").trim();
  const tokens = new Set(clean.split(/\s+/).filter((token) => token.length > 1));
  const compact = clean.replace(/\s+/g, "");
  for (let index = 0; index < compact.length - 1; index += 1) {
    tokens.add(compact.slice(index, index + 2));
  }
  return tokens;
}

function setSimilarity(left: Set<string>, right: Set<string>): number {
  if (left.size === 0 || right.size === 0) {
    return 0;
  }
  let shared = 0;
  for (const token of left) {
    if (right.has(token)) shared += 1;
  }
  return shared / (left.size + right.size - shared);
}

function knowledgeSimilarities(target: KnowledgeReviewItem): KnowledgeSimilarity[] {
  const candidates = [
    ...knowledgeDraftItems.value,
    ...knowledgeReadyItems.value,
    ...knowledgeLibraryItems.value,
  ];
  const targetBody = knowledgeEditableBody(target);
  const targetTokens = similarityTokens(`${target.title} ${targetBody}`);
  const targetTitle = similarityTokens(target.title);
  const targetTags = new Set(target.tags.map((tag) => tag.toLocaleLowerCase()));
  return candidates
    .filter((candidate) => candidate.key !== target.key)
    .map((candidate) => {
      const contentScore = setSimilarity(
        targetTokens,
        similarityTokens(`${candidate.title} ${knowledgeEditableBody(candidate)}`),
      );
      const titleScore = setSimilarity(targetTitle, similarityTokens(candidate.title));
      const tagScore = setSimilarity(targetTags, new Set(candidate.tags.map((tag) => tag.toLocaleLowerCase())));
      const score = Math.min(1, contentScore * 0.68 + titleScore * 0.24 + tagScore * 0.08);
      const location = candidate.stage === "library" ? "已入库资料" : candidate.stage === "ready" ? "待入库资料" : "另一条草稿";
      return {item: candidate, score, reason: location};
    })
    .filter((match) => match.score >= 0.16)
    .sort((left, right) => right.score - left.score)
    .slice(0, 4);
}

function knowledgeDuplicateCount(item: KnowledgeReviewItem): number {
  return knowledgeSimilarities(item).filter((match) => match.score >= 0.34).length;
}

function knowledgeTypeLabel(value: string): string {
  return knowledgeTypeOptions.find((option) => option.value === value)?.label ?? "资料";
}

function formatKnowledgeDate(value: string): string {
  if (!value) return "刚刚";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"});
}

function isKnowledgeSelected(record: ApiRecord): boolean {
  return selectedKnowledgeIds.value.includes(recordId(record));
}

function toggleKnowledgeReference(record: ApiRecord): void {
  const id = recordId(record);
  if (!id) {
    return;
  }
  if (selectedKnowledgeIds.value.includes(id)) {
    selectedKnowledgeIds.value = selectedKnowledgeIds.value.filter((item) => item !== id);
    return;
  }
  selectedKnowledgeIds.value = [...selectedKnowledgeIds.value, id].slice(-6);
}

function addKnowledgeToChat(record: ApiRecord): void {
  const id = recordId(record);
  if (id && !selectedKnowledgeIds.value.includes(id)) {
    selectedKnowledgeIds.value = [...selectedKnowledgeIds.value, id].slice(-6);
  }
  activity.value = "chat";
  markSaved("资料已加入对话参考");
}

function removeKnowledgeReference(record: ApiRecord): void {
  const id = recordId(record);
  selectedKnowledgeIds.value = selectedKnowledgeIds.value.filter((item) => item !== id);
}

async function refreshChatReferences(): Promise<void> {
  await refreshNodes();
  markSaved("资料列表已刷新");
}

function selectRecentKnowledgeMessages(): void {
  knowledgeSelectedMessageIds.value = knowledgeExtractMessages.value.slice(-8).map((message) => message.id);
}

function selectAllKnowledgeMessages(): void {
  knowledgeSelectedMessageIds.value = knowledgeExtractMessages.value.slice(-24).map((message) => message.id);
}

function toggleKnowledgeExtractMessage(messageId: string): void {
  if (knowledgeSelectedMessageIds.value.includes(messageId)) {
    knowledgeSelectedMessageIds.value = knowledgeSelectedMessageIds.value.filter((id) => id !== messageId);
    return;
  }
  if (knowledgeSelectedMessageIds.value.length >= 24) {
    ElMessage.warning("一次最多提炼 24 条消息");
    return;
  }
  knowledgeSelectedMessageIds.value = [...knowledgeSelectedMessageIds.value, messageId];
}

function openKnowledgeExtractor(messageIds?: string[]): void {
  if (activeProject.value.chat.length === 0) {
    runState.value = {error: "还没有可提炼的对话"};
    ElMessage.warning("先进行一段创作对话，再提炼资料");
    return;
  }
  knowledgeExtractStep.value = "select";
  knowledgeCandidates.value = [];
  knowledgeExtractOffline.value = false;
  knowledgeExtractNote.value = "";
  const available = new Set(knowledgeExtractMessages.value.map((message) => message.id));
  const requested = (messageIds ?? []).filter((id) => available.has(id));
  knowledgeSelectedMessageIds.value = requested.length > 0
    ? requested
    : knowledgeExtractMessages.value.slice(-8).map((message) => message.id);
  knowledgeExtractVisible.value = true;
}

function saveMessageAsKnowledge(message: CreativeMessage): void {
  openKnowledgeExtractor([message.id]);
}

function saveChatAsKnowledge(): void {
  openKnowledgeExtractor();
}

async function runKnowledgeExtraction(): Promise<void> {
  if (knowledgeSelectedMessages.value.length === 0) {
    ElMessage.warning("至少选择一条对话");
    return;
  }
  const result = await perform("提炼对话资料", () =>
    extractConversationKnowledge({
      project: {
        id: activeProject.value.id,
        name: activeProject.value.name,
        genre: activeProject.value.genre,
      },
      chapter: activeChapter.value
        ? {id: activeChapter.value.id, title: activeChapter.value.title}
        : null,
      messages: knowledgeSelectedMessages.value.map((message) => ({
        id: message.id,
        role: message.role,
        content: message.content,
        created_at: message.created_at,
      })),
    }),
    {collapseOutput: true},
  );
  if (!result) {
    return;
  }
  knowledgeCandidates.value = result.candidates.map((candidate) => ({
    ...candidate,
    selected: true,
    tagsText: candidate.tags.join(", "),
  }));
  knowledgeExtractOffline.value = result.offline;
  knowledgeExtractNote.value = result.note;
  knowledgeExtractStep.value = "review";
}

function knowledgeCandidateSource(candidate: KnowledgeCandidateDraft): CreativeMessage[] {
  const ids = new Set(candidate.source_message_ids);
  const matched = knowledgeSelectedMessages.value.filter((message) => ids.has(message.id));
  return matched.length > 0 ? matched : knowledgeSelectedMessages.value;
}

function knowledgeCandidateContent(candidate: KnowledgeCandidateDraft): string {
  const sourceLines = knowledgeCandidateSource(candidate)
    .slice(0, 4)
    .map((message) => {
      const role = message.role === "user" ? "我" : "Rhine-Lore";
      return `- ${role}：${preview(message.content, 180)}`;
    });
  return [
    `# ${candidate.title.trim()}`,
    "",
    candidate.content.trim(),
    "",
    "---",
    "来源：Rhine-Lore 对话提炼",
    `项目：${activeProject.value.name}`,
    `项目 ID：${activeProject.value.id}`,
    activeChapter.value ? `章节：${activeChapter.value.title}` : "章节：未选择",
    activeChapter.value ? `章节 ID：${activeChapter.value.id}` : "章节 ID：",
    `来源消息：${candidate.source_message_ids.join(", ")}`,
    "来源摘录：",
    ...sourceLines,
  ].join("\n");
}

async function saveKnowledgeCandidates(): Promise<void> {
  const selected = knowledgeCandidates.value.filter((candidate) => candidate.selected);
  const invalid = selected.find((candidate) => !candidate.title.trim() || !candidate.content.trim());
  if (selected.length === 0) {
    ElMessage.warning("至少选择一条资料候选");
    return;
  }
  if (invalid) {
    ElMessage.warning("所选资料的标题和内容不能为空");
    return;
  }
  const result = await perform("保存资料草稿", async () => {
    const savedIds: string[] = [];
    const failures: {candidateId: string; message: string}[] = [];
    for (const candidate of selected) {
      try {
        const tags = candidate.tagsText
          .split(/[,，、\s]+/)
          .map((tag) => tag.trim())
          .filter(Boolean);
        await createManualProposal({
          title: candidate.title.trim(),
          node_type: candidate.node_type,
          content: knowledgeCandidateContent(candidate),
          authority: candidate.authority || "experimental",
          tags: Array.from(new Set(["lore", "chat-extract", activeProject.value.id, ...tags])),
        });
        savedIds.push(candidate.candidate_id);
      } catch (error) {
        failures.push({
          candidateId: candidate.candidate_id,
          message: error instanceof Error ? error.message : String(error),
        });
      }
    }
    if (savedIds.length === 0) {
      throw new Error(failures[0]?.message || "资料草稿保存失败");
    }
    return {savedIds, failures};
  }, {collapseOutput: true});
  if (!result) {
    return;
  }
  await refreshReview();
  if (result.failures.length > 0) {
    const failedIds = new Set(result.failures.map((failure) => failure.candidateId));
    knowledgeCandidates.value = knowledgeCandidates.value.filter((candidate) => failedIds.has(candidate.candidate_id));
    knowledgeCandidates.value.forEach((candidate) => {
      candidate.selected = true;
    });
    markSaved(`${result.savedIds.length} 条已保存，${result.failures.length} 条需要重试`);
    ElMessage.warning(`${result.savedIds.length} 条已进入草稿，${result.failures.length} 条保存失败并已保留`);
    return;
  }
  knowledgeExtractVisible.value = false;
  markSaved(`${result.savedIds.length} 条资料已进入草稿`);
  toastSuccess(`${result.savedIds.length} 条资料已保存，审核后即可入库`);
}

async function submitLoreItem(kind: "world" | "characters", item: WorldCard | CharacterCard): Promise<void> {
  const project = activeProject.value;
  const titlePrefix = kind === "world" ? "World" : "Character";
  let title = "";
  let content = "";
  if (kind === "world") {
    const lore = item as WorldCard;
    title = lore.name;
    content = [
      `# ${lore.name}`,
      "",
      `Project: ${project.name}`,
      "",
      `类型：${lore.type}`,
      `概述：${lore.summary || "未设定"}`,
      `意义：${lore.significance || "未设定"}`,
      `标签：${lore.tags || "未设定"}`,
      "",
      lore.details || "未设定",
    ].join("\n");
  } else {
    const card = item as CharacterCard;
    title = card.name;
    const relationships = card.relationships
      .map((relation) => `${relation.name || "?"}（${relation.relation || "?"}）`)
      .join("；");
    content = [
      `# ${card.name}`,
      "",
      `Project: ${project.name}`,
      "",
      `身份：${card.identity || "未设定"}`,
      `角色定位：${card.role}`,
      `年龄：${card.age || "未设定"}`,
      `立场：${card.stance || "未设定"}`,
      `欲望：${card.drive || "未设定"}`,
      `恐惧：${card.fear || "未设定"}`,
      `性格：${card.traits || "未设定"}`,
      `能力：${card.abilities || "未设定"}`,
      `弱点：${card.weakness || "未设定"}`,
      `秘密：${card.secret || "未设定"}`,
      `说话风格：${card.speech || "未设定"}`,
      `外貌：${card.appearance || "未设定"}`,
      `背景：${card.background || "未设定"}`,
      `状态：${card.status}`,
      relationships ? `关系：${relationships}` : "",
      card.notes ? `备注：\n${card.notes}` : "",
    ]
      .filter(Boolean)
      .join("\n");
  }
  const result = await perform("保存资料", () =>
    createManualProposal({
      title: `${titlePrefix}: ${title}`,
      node_type: "Note",
      content,
      authority: "experimental",
      tags: ["lore", kind === "world" ? "world" : "character", project.id],
    }),
  );
  if (result) {
    markSaved("已保存为资料草稿")
    await refreshReview();
  }
}

async function submitChapterExtract(): Promise<void> {
  const chapter = activeChapter.value;
  if (!chapter || !chapter.content.trim()) {
    runState.value = {error: "章节内容为空"};
    return;
  }
  const result = await perform("保存章节资料", () =>
    createManualProposal({
      title: `Chapter Extract: ${chapter.title}`,
      node_type: "Note",
      content: [
        `# ${chapter.title}`,
        "",
        `项目：${activeProject.value.name}`,
        "来源：正文章节提取",
        "",
        chapter.content,
      ].join("\n"),
      authority: "experimental",
      tags: ["lore", "chapter", "chapter-extract", activeProject.value.id],
    }),
  );
  if (result) {
    markSaved("章节已保存为资料草稿")
    await refreshReview();
  }
}

function prefillKnowledgeFromChapter(): void {
  const chapter = activeChapter.value;
  if (!chapter) {
    return;
  }
  manualKnowledgeTitle.value = `章节资料：${chapter.title}`;
  manualKnowledgeContent.value = [
    `# ${chapter.title}`,
    "",
    `项目：${activeProject.value.name}`,
    "来源：正文章节提取",
    "",
    chapter.content,
  ].join("\n");
  manualKnowledgeTags.value = "lore, chapter, draft";
  activity.value = "context";
}

function parseManualKnowledgeTags(): string[] {
  const tags = manualKnowledgeTags.value
    .split(/[,\s，、]+/)
    .map((tag) => tag.trim())
    .filter(Boolean);
  return Array.from(new Set(["lore", ...tags]));
}

async function submitManualKnowledgeDraft(): Promise<void> {
  const title = manualKnowledgeTitle.value.trim();
  const content = manualKnowledgeContent.value.trim();
  if (!title || !content) {
    runState.value = {error: "资料标题和内容不能为空"};
    return;
  }
  const result = await perform("保存资料草稿", () =>
    createManualProposal({
      title,
      node_type: "Note",
      content,
      authority: "experimental",
      tags: [...parseManualKnowledgeTags(), activeProject.value.id],
    }),
  );
  if (result) {
    manualKnowledgeTitle.value = "";
    manualKnowledgeContent.value = "";
    markSaved("资料草稿已保存");
    toastSuccess("资料草稿已保存");
    await refreshReview();
  }
}

function openAdjacentChapter(direction: -1 | 1): void {
  const nextIndex = activeChapterIndex.value + direction;
  const nextChapter = activeProject.value.chapters[nextIndex];
  if (!nextChapter) {
    return;
  }
  selectChapter(nextChapter.id);
  resetReaderScroll();
}

function updateReadingProgress(): void {
  if (!readerSource.value || (readerSource.value === "novel" && readerMode.value !== "read")) {
    return;
  }
  if (readerPageMode.value === "page" && readerOverlayOpen.value) {
    readingProgress.value = readerPages.value.length > 0
      ? ((readerPageIndex.value + 1) / readerPages.value.length) * 100
      : 100;
    scheduleReaderPositionSave();
    return;
  }
  const wrap = readerScrollContainer();
  if (!wrap) {
    return;
  }
  const max = wrap.scrollHeight - wrap.clientHeight;
  readingProgress.value =
    max > 0 ? Math.min(100, Math.max(0, (wrap.scrollTop / max) * 100)) : 100;
  scheduleReaderPositionSave();
}

function maybeAutoAdvanceChapter(): void {
  if (!readerOverlayOpen.value || !readerAutoAdvance.value || readerPageMode.value === "page") {
    return;
  }
  const now = Date.now();
  if (now - lastReaderAutoAdvance.value < 900) {
    return;
  }
  if (!userScrolledReading.value) {
    return;
  }
  const wrap = readerScrollContainer();
  if (!wrap) {
    return;
  }
  const nearBottom = wrap.scrollTop + wrap.clientHeight >= wrap.scrollHeight - 140;
  if (!nearBottom) {
    return;
  }
  if (activity.value === "novel" && readerMode.value === "read") {
    if (activeChapterIndex.value >= activeProject.value.chapters.length - 1) {
      return;
    }
    lastReaderAutoAdvance.value = now;
    userScrolledReading.value = false;
    openAdjacentChapter(1);
    return;
  }
  if (activity.value === "read" && evolutionActiveChapter.value) {
    if (evolutionChapterIndex.value >= evolutionNovelChapters.value.length - 1) {
      return;
    }
    lastReaderAutoAdvance.value = now;
    userScrolledReading.value = false;
    openEvolutionAdjacentChapter(1);
    return;
  }
  if (activity.value === "shelf" && shelfChapter.value && shelfBook.value) {
    if (shelfChapterIndex.value >= shelfBook.value.chapters.length - 1) {
      return;
    }
    lastReaderAutoAdvance.value = now;
    userScrolledReading.value = false;
    openShelfAdjacentChapter(1);
  }
}

function handleReadingScroll(): void {
  updateReadingProgress();
  const wrap = readerScrollContainer();
  if (wrap && wrap.scrollTop > 0) {
    userScrolledReading.value = true;
  }
  maybeAutoAdvanceChapter();
}

function changeReaderPageMode(): void {
  persistReaderSettings();
  readerPageIndex.value = 0;
  void repaginate();
}

async function repaginate(): Promise<void> {
  if (readerPageMode.value !== "page") {
    return;
  }
  await nextTick();
  const area = readerOverlayOpen.value ? readerOverlayPageAreaRef.value : readerPageAreaRef.value;
  if (!area) {
    return;
  }
  const paragraphs = readerCurrentParagraphs.value;
  const pageHeight = area.clientHeight;
  if (pageHeight < 100) {
    return;
  }
  const areaStyle = getComputedStyle(area);
  const measure = document.createElement("div");
  measure.style.position = "fixed";
  measure.style.left = "-9999px";
  measure.style.top = "0";
  measure.style.visibility = "hidden";
  measure.style.boxSizing = "border-box";
  measure.style.width = `${area.clientWidth}px`;
  measure.style.fontFamily = areaStyle.fontFamily;
  measure.style.fontSize = areaStyle.fontSize;
  measure.style.fontStyle = areaStyle.fontStyle;
  measure.style.fontWeight = areaStyle.fontWeight;
  measure.style.letterSpacing = areaStyle.letterSpacing;
  measure.style.lineHeight = areaStyle.lineHeight;
  measure.style.textAlign = areaStyle.textAlign;
  measure.style.wordBreak = "normal";
  measure.style.overflowWrap = "break-word";
  measure.style.setProperty("line-break", "strict");
  document.body.appendChild(measure);
  const paragraphMeasure = document.createElement("p");
  paragraphMeasure.style.boxSizing = "border-box";
  paragraphMeasure.style.width = "100%";
  paragraphMeasure.style.margin = `0 0 ${readerParagraphSpacing.value}em`;
  paragraphMeasure.style.padding = "0";
  paragraphMeasure.style.font = "inherit";
  paragraphMeasure.style.lineHeight = "inherit";
  paragraphMeasure.style.textAlign = "inherit";
  paragraphMeasure.style.wordBreak = "normal";
  paragraphMeasure.style.overflowWrap = "break-word";
  paragraphMeasure.style.setProperty("line-break", "strict");
  measure.appendChild(paragraphMeasure);

  const paragraphHeight = (text: string, continuation: boolean): number => {
    paragraphMeasure.textContent = text;
    paragraphMeasure.style.textIndent = continuation || !readerIndent.value ? "0" : "2em";
    const margin = parseFloat(getComputedStyle(paragraphMeasure).marginBottom) || 0;
    return paragraphMeasure.getBoundingClientRect().height + margin;
  };

  const preferredBreak = (text: string, maximum: number): number => {
    let safeMaximum = maximum;
    const previousCode = text.charCodeAt(safeMaximum - 1);
    const nextCode = text.charCodeAt(safeMaximum);
    if (previousCode >= 0xd800 && previousCode <= 0xdbff && nextCode >= 0xdc00 && nextCode <= 0xdfff) {
      safeMaximum -= 1;
    }
    const minimum = Math.max(1, Math.floor(safeMaximum * 0.72));
    for (let index = safeMaximum - 1; index >= minimum; index -= 1) {
      if (/[。！？!?…；;，,、：:）】》」』”’\s]/.test(text[index])) {
        return index + 1;
      }
    }
    return Math.max(1, safeMaximum);
  };

  const pages: ReaderPage[] = [{kind: "title"}];
  let current: ReaderPageParagraph[] = [];
  let used = 0;
  const commitPage = () => {
    if (current.length > 0) {
      pages.push({kind: "content", paragraphs: current});
      current = [];
      used = 0;
    }
  };

  try {
    for (const paragraph of paragraphs) {
      let remaining = paragraph.trim();
      let continuation = false;
      while (remaining) {
        const available = pageHeight - used;
        const fullHeight = paragraphHeight(remaining, continuation);
        if (fullHeight <= available + 0.5) {
          current.push({text: remaining, continuation});
          used += fullHeight;
          break;
        }

        const minimumFragmentHeight = readerFontSize.value * readerLineHeight.value * 2
          + readerParagraphSpacing.value * readerFontSize.value;
        if (current.length > 0 && available < minimumFragmentHeight) {
          commitPage();
          continue;
        }

        let low = 1;
        let high = remaining.length;
        let fittingLength = 0;
        while (low <= high) {
          const middle = Math.floor((low + high) / 2);
          if (paragraphHeight(remaining.slice(0, middle), continuation) <= available + 0.5) {
            fittingLength = middle;
            low = middle + 1;
          } else {
            high = middle - 1;
          }
        }

        if (fittingLength <= 0) {
          if (current.length > 0) {
            commitPage();
            continue;
          }
          fittingLength = 1;
        }

        const splitAt = preferredBreak(remaining, fittingLength);
        const fragment = remaining.slice(0, splitAt).trimEnd();
        if (!fragment) {
          remaining = remaining.slice(splitAt).trimStart();
          continue;
        }
        current.push({text: fragment, continuation});
        commitPage();
        remaining = remaining.slice(splitAt).trimStart();
        continuation = true;
      }
    }
    commitPage();
  } finally {
    document.body.removeChild(measure);
  }
  readerPages.value = pages;
  if (readerPageIndex.value >= readerPages.value.length) {
    readerPageIndex.value = Math.max(0, readerPages.value.length - 1);
  }
  updateReadingProgress();
}

function readerPagePrev(): void {
  if (readerPageMode.value === "page") {
    if (readerPageIndex.value > 0) {
      readerPageIndex.value -= 1;
      updateReadingProgress();
      return;
    }
    void openReaderAdjacentChapter(-1);
    return;
  }
  void openReaderAdjacentChapter(-1);
}

function readerPageNext(): void {
  if (readerPageMode.value === "page") {
    if (readerPageIndex.value < readerPages.value.length - 1) {
      readerPageIndex.value += 1;
      updateReadingProgress();
      return;
    }
    void openReaderAdjacentChapter(1);
    return;
  }
  void openReaderAdjacentChapter(1);
}

function currentReaderPage(): ReaderPageParagraph[] {
  const page = readerPages.value[readerPageIndex.value];
  return page?.kind === "content" ? page.paragraphs : [];
}

function currentReaderPageIsTitle(): boolean {
  return readerPages.value[readerPageIndex.value]?.kind !== "content";
}

async function openReaderAdjacentChapter(direction: -1 | 1): Promise<void> {
  const next = readerCurrentChapterIndex.value + direction;
  const item = readerTocItems.value[next];
  if (!item) return;
  await selectReaderChapter(item.id, false);
}

async function seekReaderOverallProgress(value: number): Promise<void> {
  const total = readerTocItems.value.length;
  if (total <= 0) return;
  const normalized = Math.min(0.9999, Math.max(0, value / 100));
  const exact = normalized * total;
  const chapterIndex = Math.min(total - 1, Math.floor(exact));
  const chapterProgress = (exact - chapterIndex) * 100;
  const chapter = readerTocItems.value[chapterIndex];
  if (!chapter) return;
  await selectReaderChapter(chapter.id, false);
  await restoreReaderProgress({chapterId: chapter.id, progress: chapterProgress, pageIndex: 0});
}

async function enterReaderMode(): Promise<void> {
  if (activity.value === "novel") readerMode.value = "read";
  if (!readerCurrentChapterId.value) {
    return;
  }
  readerOverlayOpen.value = true;
  readerChromeVisible.value = true;
  userScrolledReading.value = false;
  const position = loadReaderPosition();
  if (position?.chapterId && position.chapterId !== readerCurrentChapterId.value) {
    await selectReaderChapter(position.chapterId, false);
  }
  await nextTick();
  await repaginate();
  await restoreReaderProgress(position);
}

function exitReaderMode(): void {
  saveReaderPosition();
  readerOverlayOpen.value = false;
  if (activity.value === "novel") readerMode.value = "edit";
  if (document.fullscreenElement) void document.exitFullscreen?.().catch(() => undefined);
}

function scrollReaderViewport(direction: -1 | 1): void {
  const wrap = readerScrollContainer();
  if (!wrap) return;
  wrap.scrollBy({top: direction * wrap.clientHeight * 0.86, behavior: "smooth"});
  window.setTimeout(updateReadingProgress, 240);
}

function handleReaderOverlayKeydown(event: KeyboardEvent): void {
  if (!readerOverlayOpen.value) return;
  const target = event.target as HTMLElement | null;
  if (target?.matches("input, textarea, [contenteditable='true']")) return;
  if (event.key === "Escape") {
    exitReaderMode();
    return;
  }
  if (event.key === "ArrowRight") {
    event.preventDefault();
    readerPageNext();
    return;
  }
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    readerPagePrev();
    return;
  }
  if (["PageDown", " "].includes(event.key)) {
    event.preventDefault();
    if (readerPageMode.value === "page") readerPageNext();
    else scrollReaderViewport(1);
    return;
  }
  if (event.key === "PageUp") {
    event.preventDefault();
    if (readerPageMode.value === "page") readerPagePrev();
    else scrollReaderViewport(-1);
    return;
  }
  if (event.key.toLocaleLowerCase() === "m") {
    toggleReaderBookmark();
  }
  if (event.key.toLocaleLowerCase() === "f") {
    toggleReaderFullscreen();
  }
}

function handleReaderResize(): void {
  if (window.innerWidth <= 720) {
    chatSidebarOpen.value = false;
  }
  if (readerResizeTimer) window.clearTimeout(readerResizeTimer);
  readerResizeTimer = window.setTimeout(() => {
    if (readerPageMode.value === "page" && readerCurrentChapterId.value) {
      void repaginate();
    }
  }, 120);
}

async function loadChapterContext(): Promise<void> {
  const chapter = activeChapter.value;
  const query = [
    activeProject.value.name,
    activeProject.value.summary,
    chapter?.title,
    chapter?.content.slice(0, 900),
  ].filter(Boolean).join("\n");
  contextQuery.value = query || contextQuery.value;
  await buildContext();
}

async function buildContext(): Promise<void> {
  await perform("查找资料", () =>
    buildContextBundle({
      query: contextQuery.value,
      profile_id: profileId.value,
      result_limit: resultLimit.value,
      tags: ["lore"],
    }),
  );
}

async function generateStoryBible(): Promise<void> {
  await perform("生成设定文档", () =>
    generateKnowledgeDocument({
      query: contextQuery.value || activeProject.value.name,
      profile_id: profileId.value,
      result_limit: resultLimit.value,
      title: `${activeProject.value.name} Story Bible`,
      audience: "writer",
      tags: ["lore"],
    }),
  );
}

async function refreshNodes(): Promise<void> {
  const rows = await perform("刷新资料", () => listNodes(), {collapseOutput: true});
  if (rows) {
    nodes.value = rows;
  }
}

async function refreshReview(): Promise<void> {
  const [proposalResult, stagingResult] = await Promise.allSettled([listProposals(), listStaging()]);
  if (proposalResult.status === "fulfilled") {
    proposals.value = proposalResult.value;
  }
  if (stagingResult.status === "fulfilled") {
    stagingEntries.value = stagingResult.value;
  }
  const draftKeys = new Set(knowledgeDraftItems.value.map((item) => item.key));
  const readyIds = new Set(knowledgeReadyItems.value.map((item) => item.entryId));
  selectedKnowledgeDraftKeys.value = selectedKnowledgeDraftKeys.value.filter((key) => draftKeys.has(key));
  selectedKnowledgeReadyIds.value = selectedKnowledgeReadyIds.value.filter((id) => readyIds.has(id));
}

async function refreshKnowledgeCenter(): Promise<void> {
  await Promise.allSettled([refreshReview(), refreshNodes()]);
}

function knowledgeSourceSummary(item: KnowledgeReviewItem): string {
  const source = parseKnowledgeSource(item.content);
  if (source.project && source.chapter && source.chapter !== "未选择") {
    return `${source.project} · ${source.chapter}`;
  }
  if (source.project) return source.project;
  if (source.kind) return source.kind;
  return "手动创建";
}

function toggleKnowledgeDraftSelection(item: KnowledgeReviewItem, selected: unknown): void {
  const next = new Set(selectedKnowledgeDraftKeys.value);
  if (Boolean(selected)) next.add(item.key);
  else next.delete(item.key);
  selectedKnowledgeDraftKeys.value = Array.from(next);
}

function toggleKnowledgeReadySelection(item: KnowledgeReviewItem, selected: unknown): void {
  if (!item.entryId) return;
  const next = new Set(selectedKnowledgeReadyIds.value);
  if (Boolean(selected)) next.add(item.entryId);
  else next.delete(item.entryId);
  selectedKnowledgeReadyIds.value = Array.from(next);
}

function toggleAllKnowledgeDrafts(): void {
  selectedKnowledgeDraftKeys.value = selectedKnowledgeDraftKeys.value.length === knowledgeDraftItems.value.length
    ? []
    : knowledgeDraftItems.value.map((item) => item.key);
}

function toggleAllKnowledgeReady(): void {
  selectedKnowledgeReadyIds.value = selectedKnowledgeReadyIds.value.length === knowledgeReadyItems.value.length
    ? []
    : knowledgeReadyItems.value.flatMap((item) => item.entryId ? [item.entryId] : []);
}

function openKnowledgeReview(item: KnowledgeReviewItem): void {
  activeKnowledgeReviewKey.value = item.key;
  knowledgeReviewForm.value = {
    title: item.title,
    nodeType: item.nodeType,
    body: knowledgeEditableBody(item),
    authority: item.authority || "experimental",
    tagsText: item.tags.join(", "),
  };
  const libraryMatches = knowledgeSimilarities(item)
    .filter((match) => match.item.stage === "library");
  const savedTargetKey = knowledgeConflictTargets.value[item.key];
  const target = libraryMatches.find((match) => match.item.key === savedTargetKey)?.item
    ?? libraryMatches[0]?.item
    ?? null;
  knowledgeConflictTargetKey.value = target?.key ?? "";
  if (target) {
    knowledgeConflictTargets.value = {...knowledgeConflictTargets.value, [item.key]: target.key};
  }
  const savedMode = knowledgeConflictModes.value[item.key] ?? "coexist";
  knowledgeConflictMode.value = savedMode !== "coexist" && !target ? "coexist" : savedMode;
  coexistNodeId(item);
  knowledgeReviewVisible.value = true;
}

function parseKnowledgeReviewTags(): string[] {
  return Array.from(new Set(
    knowledgeReviewForm.value.tagsText
      .split(/[,，、\s]+/)
      .map((tag) => tag.trim())
      .filter(Boolean),
  ));
}

async function saveActiveKnowledgeReview(options: {quiet?: boolean} = {}): Promise<boolean> {
  const item = activeKnowledgeReviewItem.value;
  const form = knowledgeReviewForm.value;
  if (!item || item.stage !== "draft" || !item.proposalId || !item.temporaryId) {
    return false;
  }
  if (!form.title.trim() || !form.body.trim()) {
    ElMessage.warning("标题和内容不能为空");
    return false;
  }
  const patch = knowledgeReviewPatch(item);
  const result = await perform(
    "保存资料修改",
    () => updateProposalNode(item.proposalId!, item.temporaryId!, patch),
    {collapseOutput: true},
  );
  if (!result) return false;
  knowledgeReviewForm.value = {
    ...knowledgeReviewForm.value,
    title: patch.title,
    nodeType: patch.node_type,
    body: splitKnowledgeEnvelope(patch.content, patch.title).body,
    authority: patch.authority,
  };
  await refreshReview();
  if (!options.quiet) {
    markSaved("资料修改已保存");
    toastSuccess("资料草稿已更新");
  }
  return true;
}

async function stageActiveKnowledgeReview(): Promise<void> {
  const item = activeKnowledgeReviewItem.value;
  if (!item || item.stage !== "draft" || !item.proposalId || !item.temporaryId) return;
  const saved = await saveActiveKnowledgeReview({quiet: true});
  if (!saved) return;
  const result = await perform(
    "保存并送审",
    () => stageProposal(item.proposalId!, [item.temporaryId!]),
    {collapseOutput: true},
  );
  if (!result) return;
  knowledgeReviewVisible.value = false;
  knowledgeQueueTab.value = "ready";
  await refreshReview();
  markSaved("资料已送去确认");
  toastSuccess("资料已送审，确认后即可用于创作");
}

async function rejectActiveKnowledgeReview(): Promise<void> {
  const item = activeKnowledgeReviewItem.value;
  if (!item || item.stage !== "draft" || !item.proposalId) return;
  try {
    await ElMessageBox.confirm(
      `驳回“${item.title}”后，它不会进入资料库，但来源记录仍会保留。`,
      "驳回资料草稿",
      {confirmButtonText: "确认驳回", cancelButtonText: "取消", type: "warning"},
    );
  } catch {
    return;
  }
  const result = await perform("驳回资料草稿", () => rejectProposal(item.proposalId!), {collapseOutput: true});
  if (!result) return;
  knowledgeReviewVisible.value = false;
  await refreshReview();
  markSaved("资料草稿已驳回");
}

async function stageSelectedKnowledgeDrafts(): Promise<void> {
  const selected = knowledgeDraftItems.value.filter((item) => selectedKnowledgeDraftKeys.value.includes(item.key));
  if (selected.length === 0) {
    ElMessage.warning("先选择要送审的资料草稿");
    return;
  }
  const groups = new Map<string, string[]>();
  for (const item of selected) {
    if (!item.proposalId || !item.temporaryId) continue;
    groups.set(item.proposalId, [...(groups.get(item.proposalId) ?? []), item.temporaryId]);
  }
  const result = await perform("批量送审", async () => {
    for (const item of selected) {
      if (!item.proposalId || !item.temporaryId) continue;
      await updateProposalNode(item.proposalId, item.temporaryId, {
        node_id: coexistNodeId(item),
        title: item.title,
        node_type: item.nodeType,
        content: item.content,
        authority: item.authority === "project" ? "approved" : item.authority || "experimental",
        tags: item.tags,
      });
    }
    for (const [proposalId, temporaryIds] of groups) {
      await stageProposal(proposalId, temporaryIds);
    }
    return {count: selected.length};
  }, {collapseOutput: true});
  if (!result) return;
  selectedKnowledgeDraftKeys.value = [];
  knowledgeQueueTab.value = "ready";
  await refreshReview();
  markSaved(`${result.count} 条资料已送审`);
  toastSuccess(`${result.count} 条资料已进入待入库`);
}

async function approveSelectedKnowledgeReady(): Promise<void> {
  if (selectedKnowledgeReadyIds.value.length === 0) {
    ElMessage.warning("先选择要入库的资料");
    return;
  }
  const entryIds = [...selectedKnowledgeReadyIds.value];
  const result = await perform("批量确认入库", () => approveStaging(entryIds), {collapseOutput: true});
  if (!result) return;
  selectedKnowledgeReadyIds.value = [];
  knowledgeReviewVisible.value = false;
  await Promise.allSettled([refreshReview(), refreshNodes()]);
  markSaved(`${entryIds.length} 条资料已入库`);
  toastSuccess(`${entryIds.length} 条资料现在可以用于对话参考`);
}

async function approveActiveKnowledgeReady(): Promise<void> {
  const item = activeKnowledgeReviewItem.value;
  if (!item?.entryId) return;
  selectedKnowledgeReadyIds.value = [item.entryId];
  await approveSelectedKnowledgeReady();
}

async function refreshWorkspaces(): Promise<void> {
  const rows = await listWorkspaces();
  backendStatus.value = "online";
  workspaces.value = rows;
  if (rows.length > 0 && !rows.some((item) => item.workspace_id === selectedWorkspaceId.value)) {
    selectedWorkspaceId.value = rows[0].workspace_id;
    setWorkspaceId(selectedWorkspaceId.value);
  }
}

async function switchWorkspace(): Promise<void> {
  setWorkspaceId(selectedWorkspaceId.value);
  await perform("切换 Workspace", async () => {
    await Promise.allSettled([refreshNodes(), refreshReview()]);
    return {workspace_id: selectedWorkspaceId.value};
  });
}

async function createWorkspace(): Promise<void> {
  const workspace = newWorkspaceId.value.trim();
  if (!workspace) {
    runState.value = {error: "workspace_id 为空"};
    return;
  }
  const result = await perform("创建 Workspace", () =>
    registerWorkspace({
      workspace_id: workspace,
      workspace_type: "project",
      display_name: newWorkspaceDisplayName.value.trim() || workspace,
    }),
  );
  if (result) {
    selectedWorkspaceId.value = workspace;
    setWorkspaceId(workspace);
    await refreshWorkspaces();
  }
}

function persistVaultRuntimeConfig(): void {
  localStorage.setItem("rhine-lore-vault-path", vaultPath.value.trim());
  localStorage.setItem("rhine-lore-vault-host", vaultHost.value.trim() || "127.0.0.1");
  localStorage.setItem("rhine-lore-vault-port", String(vaultPort.value || 8795));
  localStorage.setItem("rhine-lore-vault-database-path", vaultDatabasePath.value.trim());
  localStorage.setItem("rhine-lore-vault-python-path", vaultPythonPath.value.trim());
  localStorage.setItem("rhine-lore-external-vault-url", externalVaultUrl.value.trim());
}

function syncVaultRuntimeStatus(status: VaultRuntimeStatus): void {
  vaultStatus.value = status;
  backendStatus.value = status.connected ? "online" : "offline";
  if (!vaultPath.value && status.config.vault_path) {
    vaultPath.value = status.config.vault_path;
  }
  if (!vaultDatabasePath.value && status.config.database_path) {
    vaultDatabasePath.value = status.config.database_path;
  }
  const baseUrl = status.manager.base_url || status.config.base_url;
  try {
    const parsed = new URL(baseUrl);
    vaultHost.value = parsed.hostname || vaultHost.value;
    vaultPort.value = Number(parsed.port || (parsed.protocol === "https:" ? 443 : 80));
    if (!externalVaultUrl.value) {
      externalVaultUrl.value = baseUrl;
    }
  } catch {
    // Keep the editable form values when the backend returns an unexpected URL.
  }
}

async function refreshVaultWebStatus(): Promise<void> {
  vaultWebStatus.value = await getVaultWebStatus();
}

async function refreshVaultRuntime(): Promise<void> {
  const status = await getVaultRuntimeStatus();
  syncVaultRuntimeStatus(status);
  await refreshVaultWebStatus();
}

async function testBackend(): Promise<void> {
  await perform("检查连接", refreshVaultRuntime, {collapseOutput: true});
}

async function testServerBaseConnection(): Promise<void> {
  serverBaseBusy.value = true;
  serverBaseMessage.value = "测试中…";
  try {
    const result = await pingServerBase(serverBaseInput.value);
    serverBaseMessage.value = result.ok ? `✓ ${result.detail}` : `✗ ${result.detail}`;
  } catch (error) {
    serverBaseMessage.value = `✗ ${error instanceof Error ? error.message : String(error)}`;
  } finally {
    serverBaseBusy.value = false;
  }
}

async function applyServerBase(): Promise<void> {
  serverBaseBusy.value = true;
  try {
    setServerBase(serverBaseInput.value);
    serverBaseCurrent.value = getServerBase();
    await initProjects();
    await Promise.allSettled([refreshWorkspaces(), refreshReview(), refreshNodes(), loadShelfBooks()]);
    toastSuccess(serverBaseCurrent.value ? `已连接服务器 ${serverBaseCurrent.value}` : "已恢复内置服务器");
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  } finally {
    serverBaseBusy.value = false;
  }
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result ?? "");
      const base64 = result.includes(",") ? result.slice(result.indexOf(",") + 1) : result;
      resolve(base64);
    };
    reader.onerror = () => reject(reader.error ?? new Error("读取文件失败"));
    reader.readAsDataURL(blob);
  });
}

function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function exportBackup(): Promise<void> {
  backupBusy.value = true;
  backupMessage.value = "正在打包…";
  try {
    const result = await perform("导出备份", async () => {
      const {blob, filename} = await exportBackupZip();
      const bridge = (window as {AndroidBridge?: {saveBackup?: (name: string, base64: string) => string}}).AndroidBridge;
      if (bridge?.saveBackup) {
        const base64 = await blobToBase64(blob);
        return {saved: bridge.saveBackup(filename, base64), size: blob.size};
      }
      triggerBlobDownload(blob, filename);
      return {downloaded: filename, size: blob.size};
    });
    backupMessage.value = result ? "备份完成" : "导出失败";
  } finally {
    backupBusy.value = false;
  }
}

async function handleBackupImport(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    return;
  }
  backupBusy.value = true;
  backupMessage.value = "正在导入…";
  try {
    const result = await perform("导入备份", () => importBackupZip(file));
    if (result) {
      await initProjects();
      await Promise.allSettled([
        loadShelfBooks(),
        loadDiskBackups(),
        refreshWorkspaces(),
        refreshNodes(),
        refreshReview(),
      ]);
      backupMessage.value = `导入完成：${result.projects} 个项目、${result.books} 本书、${result.versions} 个版本、${result.knowledge ?? 0} 份资料库数据`;
      toastSuccess("备份导入完成");
    }
  } finally {
    backupBusy.value = false;
    input.value = "";
  }
}

async function updateBackendStatus(): Promise<void> {
  backendStatus.value = "checking";
  try {
    await refreshVaultRuntime();
  } catch {
    backendStatus.value = "offline";
  }
}

async function connectVault(): Promise<void> {
  persistVaultRuntimeConfig();
  const baseUrl = externalVaultUrl.value.trim();
  const result = await perform("应用资料库连接", () =>
    connectVaultRuntime(
      baseUrl ? {base_url: baseUrl} : {host: vaultHost.value.trim() || "127.0.0.1", port: vaultPort.value || 8795},
    ),
  );
  if (result) {
    syncVaultRuntimeStatus(result);
    await Promise.allSettled([refreshWorkspaces(), refreshNodes(), refreshReview()]);
  }
}

async function startDefaultVault(): Promise<void> {
  const result = await perform("启动默认资料库", () => startVaultRuntime({}));
  if (result) {
    syncVaultRuntimeStatus(result);
    window.setTimeout(() => void updateBackendStatus(), 1200);
  }
}

async function startVault(): Promise<void> {
  persistVaultRuntimeConfig();
  const result = await perform("启动自定义资料库", () =>
    startVaultRuntime({
      vault_path: vaultPath.value.trim(),
      host: vaultHost.value.trim() || "127.0.0.1",
      port: vaultPort.value || 8795,
      database_path: vaultDatabasePath.value.trim(),
      python_path: vaultPythonPath.value.trim(),
      base_url: "",
    }),
  );
  if (result) {
    syncVaultRuntimeStatus(result);
    window.setTimeout(() => void updateBackendStatus(), 1200);
  }
}

async function stopVault(): Promise<void> {
  const result = await perform("停止本机资料库", stopVaultRuntime);
  if (result) {
    syncVaultRuntimeStatus(result);
  }
}

async function installVaultWebUI(): Promise<void> {
  persistVaultRuntimeConfig();
  const result = await perform("安装 Vault Web", () => installVaultWeb({vault_path: vaultPath.value.trim()}));
  if (result) {
    vaultWebStatus.value = result;
    markSaved("Vault Web 已准备好");
  }
}

function openVaultWeb(): void {
  window.open(vaultWebUrl.value, "_blank", "noopener,noreferrer");
}

function preview(value: unknown, length = 160): string {
  const text = String(value ?? "");
  return text.length > length ? `${text.slice(0, length)}...` : text;
}

function chapterLength(chapter: Chapter): number {
  return chapter.content.trim().length;
}

function projectLength(project: StoryProject): number {
  return project.chapters.reduce((total, chapter) => total + chapterLength(chapter), 0);
}

const evolutionState = computed(() => evolutionView.value?.state ?? null);

const evolutionStats = computed(() => {
  const state = evolutionState.value;
  if (!state) {
    return [];
  }
  const alive = state.cast.filter((member) => member.alive).length;
  const activeThreads = state.threads.filter((thread) => thread.status === "active").length;
  const openSeeds = state.threads.filter((thread) => thread.kind === "伏笔" && thread.status === "active").length;
  return [
    {label: "回合", value: state.turn, tone: "blue"},
    {label: "世界张力", value: state.world.tension, tone: "amber"},
    {label: "存活角色", value: alive, tone: "green"},
    {label: "活动线索", value: activeThreads, tone: "gray"},
    {label: "未回收伏笔", value: openSeeds, tone: "amber"},
  ];
});

const evolutionHistory = computed(() => {
  const events = evolutionState.value?.history ?? [];
  return [...events].reverse();
});

const visibleEvolutionHistory = computed(() => {
  return evolutionHistory.value.slice(0, evolutionTimelineLimit.value);
});

function loadMoreEvolutionEvents(): void {
  evolutionTimelineLimit.value += 30;
}

const evolutionThreads = computed(() => evolutionState.value?.threads ?? []);
const evolutionCast = computed(() => evolutionState.value?.cast ?? []);
const evolutionPendingBranch = computed(() => evolutionState.value?.pending_branch ?? null);
const evolutionActNames = ["序幕", "发展", "转折", "高潮", "尾声"];
const evolutionActName = computed(() => {
  const index = evolutionState.value?.arc.act_index ?? 0;
  return evolutionActNames[index] ?? "尾声";
});

const evolutionChapterSize = computed(() => {
  return Math.min(8, Math.max(1, Number(activeProject.value.chapter_turns) || 4));
});

const evolutionNeedsCharacter = computed(() => {
  const view = evolutionView.value;
  return Boolean(
    view?.needs_character && !ignoredCharacterPromptProjects.value.includes(activeProject.value.id),
  );
});

function dismissCharacterPrompt(): void {
  if (!ignoredCharacterPromptProjects.value.includes(activeProject.value.id)) {
    ignoredCharacterPromptProjects.value.push(activeProject.value.id);
  }
}

function openEvolutionCharacterDialog(): void {
  const suggestion = evolutionView.value?.suggested_character;
  evolutionNewCharacter.value = {
    name: "",
    role: suggestion?.role ?? "配角",
    drive: suggestion?.drive ?? "寻找自己在故事中的位置",
    secret: "",
  };
  evolutionCharacterDialogVisible.value = true;
}

async function confirmAddEvolutionCharacter(): Promise<void> {
  const project = activeProject.value;
  const name = evolutionNewCharacter.value.name.trim();
  if (!name || !evolutionState.value) {
    return;
  }
  const card: CharacterCard = {
    id: uid("character"),
    name,
    identity: "",
    role: evolutionNewCharacter.value.role,
    age: "",
    stance: "",
    drive: evolutionNewCharacter.value.drive.trim(),
    fear: "",
    traits: "",
    abilities: "",
    weakness: "",
    secret: evolutionNewCharacter.value.secret.trim(),
    speech: "",
    appearance: "",
    background: "",
    relationships: [],
    status: "正常",
    notes: "",
  };
  project.characters.push(card);
  saveProjects();
  const view = await perform("添加角色", () =>
    addEvolutionCharacter({
      project_id: project.id,
      viewpoint_id: evolutionViewpoint.value || "",
      character: card,
    }),
  );
  if (view) {
    evolutionView.value = view;
    evolutionGuidance.value = view.state.guidance ?? "";
    evolutionCharacterDialogVisible.value = false;
    markSaved("新角色已加入演化");
  }
}

function buildEvolutionChatMessages(question: string): LlmChatMessage[] {
  const state = evolutionState.value;
  if (!state) {
    return [];
  }
  const actNames = ["序幕", "发展", "转折", "高潮", "尾声"];
  const actName = actNames[state.arc.act_index] ?? "尾声";
  const threads = state.threads
    .filter((thread) => thread.status === "active")
    .slice(0, 8)
    .map((thread) => `【${thread.kind}】${thread.title}${thread.secret ? `：${thread.secret}` : ""}`)
    .join("\n");
  const recent = state.history
    .slice(-6)
    .map((event) => `[第${event.turn}回合·${event.kind}] ${event.title}：${event.summary}`)
    .join("\n");
  const cast = state.cast
    .slice(0, 8)
    .map((member) => `${member.name}（${member.role}${member.alive ? "" : "·已故"}）所在地=${member.location || "未知"}`)
    .join("；");
  const system =
    "你是演化剧情的导演助理。基于当前沙盘状态回答创作问题、分析局势、给出下一步建议；回答简洁，必要时给出具体的事件方向。";
  const user = [
    `项目：《${state.project_name}》 类型：${state.genre}`,
    `当前第 ${state.turn} 回合 · ${actName} · 张力 ${state.world.tension}（目标 ${state.arc.tension_range[0]}–${state.arc.tension_range[1]}）`,
    `结局方向：${state.arc.ending_kind || "未定"}`,
    `引导指令：${state.guidance || "无"}`,
    `全局引导：${activeProject.value.global_guidance || "无"}`,
    buildStyleCard() ? `风格基准：\n${buildStyleCard()}` : "文风：未指定",
    `角色：${cast}`,
    threads ? `活跃线索：\n${threads}` : "活跃线索：无",
    `最近事件：\n${recent || "暂无"}`,
    "",
    question,
  ].join("\n\n");
  return [
    {role: "system", content: system},
    {role: "user", content: user},
  ];
}

async function sendEvolutionChatMessage(): Promise<void> {
  const text = evolutionChatInput.value.trim();
  const state = evolutionState.value;
  if (!text || !state || evolutionChatBusy.value) {
    return;
  }
  if (!llmConfigured.value) {
    runState.value = {error: "与故事对话需要 AI 通道，请先在首页或右上角配置 API Key"};
    return;
  }
  evolutionChat.value.push({id: uid("chat-message"), role: "user", content: text});
  evolutionChatInput.value = "";
  evolutionChatBusy.value = true;
  evolutionChatStreaming.value = "";
  let fullText = "";
  let revealTimer: ReturnType<typeof setInterval> | undefined;
  revealTimer = setInterval(() => {
    if (fullText.length === 0) {
      return;
    }
    const current = evolutionChatStreaming.value;
    if (current.length >= fullText.length) {
      return;
    }
    const step = Math.max(3, Math.ceil(fullText.length / 150));
    evolutionChatStreaming.value = fullText.slice(0, Math.min(fullText.length, current.length + step));
  }, 16);
  try {
    const result = await perform("与故事对话", async () => {
      const streamed = await llmServerChatStream(buildEvolutionChatMessages(text), [], (event) => {
        if (event.type === "delta") {
          fullText += event.text;
        }
      });
      return {answer: streamed.answer};
    });
    if (revealTimer) {
      clearInterval(revealTimer);
    }
    evolutionChatStreaming.value = fullText;
    const reply = result ? String(result.answer ?? "").trim() : "";
    evolutionChatStreaming.value = "";
    evolutionChat.value.push({
      id: uid("chat-message"),
      role: "assistant",
      content: reply || "（没有收到回复，请重试或简化问题）",
    });
  } finally {
    if (revealTimer) {
      clearInterval(revealTimer);
    }
    evolutionChatBusy.value = false;
  }
}

function setEvolutionMessageAsGuidance(message: EvolutionChatMessage): void {
  evolutionGuidance.value = message.content;
  void saveEvolutionGuidance();
}

function clearEvolutionChat(): void {
  evolutionChat.value = [];
}

function evolutionCastName(state: EvolutionState | null, memberId: string): string {
  return state?.cast.find((member) => member.id === memberId)?.name ?? memberId;
}

function evolutionRelationLabel(member: EvolutionCastMember, targetId: string): string {
  const score = member.relations[targetId] ?? 0;
  const labels: Record<number, string> = {
    "-2": "宿敌",
    "-1": "疏远",
    "0": "陌生",
    "1": "亲近",
    "2": "羁绊",
  };
  return labels[score] ?? String(score);
}

function stopEvolutionAutoPlay(): void {
  evolutionAutoPlay.value = false;
  if (evolutionTimer) {
    window.clearInterval(evolutionTimer);
    evolutionTimer = undefined;
  }
}

async function loadEvolutionView(): Promise<boolean> {
  const project = activeProject.value;
  if (!project) {
    return false;
  }
  try {
    const view = await getEvolutionState(project.id, evolutionViewpoint.value || "");
    evolutionView.value = view;
    evolutionGuidance.value = view.state.guidance ?? "";
    if (!evolutionViewpoint.value && view.viewpoints.length > 0) {
      evolutionViewpoint.value = view.viewpoints[0].id;
    }
    return true;
  } catch {
    evolutionView.value = null;
    return false;
  }
}

async function saveEvolutionGuidance(): Promise<void> {
  const project = activeProject.value;
  if (!project || !evolutionState.value) {
    return;
  }
  const view = await perform("保存引导", () =>
    guideEvolution({
      project_id: project.id,
      guidance: evolutionGuidance.value.trim(),
      viewpoint_id: evolutionViewpoint.value || "",
    }),
  );
  if (view) {
    evolutionView.value = view;
    evolutionGuidance.value = view.state.guidance ?? "";
    markSaved(evolutionGuidance.value ? "引导已保存，下一回合生效" : "引导已清空");
  }
}

function clearEvolutionGuidance(): void {
  evolutionGuidance.value = "";
  void saveEvolutionGuidance();
}

async function beginEvolution(): Promise<void> {
  const project = activeProject.value;
  if (!project) {
    return;
  }
  const seedText = evolutionSeedInput.value.trim();
  let seed: number | null = null;
  if (seedText) {
    seed = Number(seedText);
    if (!Number.isFinite(seed)) {
      runState.value = {error: "种子必须是数字"};
      return;
    }
  }
  const view = await perform("开始演化", () =>
    startEvolutionRun({
      project_id: project.id,
      project_name: project.name,
      genre: project.genre,
      characters: project.characters,
      world: project.world,
      map: project.map,
      seed,
      settings: {
        chaos: evolutionChaos.value,
        branch_frequency: evolutionBranchFrequency.value,
        events_per_turn: 1,
        auto_resolve: evolutionAutoResolve.value,
      },
    }),
  );
  if (view) {
    evolutionView.value = view;
    evolutionGuidance.value = view.state.guidance ?? "";
    if (view.viewpoints.length > 0) {
      evolutionViewpoint.value = view.viewpoints[0].id;
    }
    markSaved("演化沙盘已建立，存档在本地 data/projects");
  }
}

async function runEvolutionTurn(choiceId?: string): Promise<void> {
  const project = activeProject.value;
  const state = evolutionState.value;
  if (!project || !state || evolutionTurnRunning) {
    return;
  }
  evolutionTurnRunning = true;
  try {
    const view = await advanceEvolution({
      project_id: project.id,
      choice_id: choiceId ?? null,
      viewpoint_id: evolutionViewpoint.value || "",
    });
    evolutionView.value = view;
    evolutionGuidance.value = view.state.guidance ?? "";
    if (llmConfigured.value && aiAutoProse.value && view.result?.advanced) {
      void generateStoredProse();
    }
    if (view.message) {
      markSaved(view.message);
    }
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  } finally {
    evolutionTurnRunning = false;
  }
}

async function chooseBranch(optionId: string): Promise<void> {
  await runEvolutionTurn(optionId);
}

async function fateDice(): Promise<void> {
  await runEvolutionTurn("fate");
}

function toggleEvolutionAutoPlay(): void {
  if (evolutionAutoPlay.value) {
    stopEvolutionAutoPlay();
    return;
  }
  evolutionAutoPlay.value = true;
  startEvolutionTimer();
}

function startEvolutionTimer(): void {
  if (evolutionTimer) {
    window.clearInterval(evolutionTimer);
  }
  evolutionTimer = window.setInterval(() => {
    void runEvolutionTurn("fate");
  }, evolutionSpeed.value * 1000);
}

function changeEvolutionSpeed(): void {
  if (evolutionAutoPlay.value) {
    startEvolutionTimer();
  }
}

async function resetEvolution(): Promise<void> {
  const project = activeProject.value;
  if (!project || !evolutionState.value) {
    return;
  }
  if (!window.confirm("清空当前演化存档，重新开始？")) {
    return;
  }
  stopEvolutionAutoPlay();
  const result = await perform("重置演化", () => resetEvolutionRun(project.id));
  if (result) {
    evolutionView.value = null;
    markSaved("演化已重置");
  }
}

async function switchEvolutionViewpoint(): Promise<void> {
  const project = activeProject.value;
  if (!project || !evolutionState.value) {
    return;
  }
  try {
    const view = await getEvolutionState(project.id, evolutionViewpoint.value || "");
    evolutionView.value = view;
    evolutionGuidance.value = view.state.guidance ?? "";
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  }
}

function acceptEvolutionIntoChapter(): void {
  const project = activeProject.value;
  const view = evolutionView.value;
  if (!project || !view) {
    return;
  }
  const novel = view.novel;
  const sourceTitle = novel?.viewpoint_name ? `${novel.viewpoint_name}的视角` : "演化记录";
  const chapters = evolutionNovelChapters.value;
  const body =
    chapters.length > 0
      ? chapters.flatMap((chapter) => chapter.paragraphs).join("\n\n")
      : view.sandbox;
  const entry = [
    `## 演化记录 · ${sourceTitle}（第 ${view.state.turn} 回合）`,
    "",
    body,
  ].join("\n");
  let chapter = activeChapter.value;
  if (!chapter) {
    addChapter();
    chapter = activeChapter.value;
  }
  if (!chapter) {
    return;
  }
  chapter.content = [chapter.content.trim(), entry.trim()].filter(Boolean).join("\n\n");
  saveProjects();
  markSaved("演化记录已接收进正文");
  readerMode.value = "edit";
  activity.value = "novel";
}

const llmStatusLabel = computed(() => {
  if (!llmConfigured.value) {
    return "未配置（离线模板模式）";
  }
  return `${llmModel.value.trim() || "模型"} · ${llmMaskedKey.value || "已配置"}`;
});

const llmChannelLabel = computed(() => {
  return llmConfigured.value ? `已接入 ${llmModel.value.trim() || "模型"}` : "离线模板";
});

const aiStatusLabel = computed(() => {
  if (aiStatus.value === "ok") {
    return "正常";
  }
  if (aiStatus.value === "error") {
    return "异常";
  }
  if (aiStatus.value === "checking") {
    return "检查中";
  }
  return "未配置";
});

const aiStatusTone = computed(() => {
  if (aiStatus.value === "ok") {
    return "online";
  }
  if (aiStatus.value === "error") {
    return "offline";
  }
  return "checking";
});

function apiErrorMessage(error: unknown): string {
  if (!(error instanceof Error)) {
    return String(error);
  }
  try {
    const parsed = JSON.parse(error.message);
    if (parsed?.detail) {
      return String(parsed.detail);
    }
  } catch {
    // 保留原始错误文本
  }
  return error.message;
}

async function runAiCheck(): Promise<void> {
  aiStatus.value = "checking";
  aiStatusDetail.value = "正在检查通道…";
  if (!llmConfigured.value) {
    aiStatus.value = "unset";
    aiStatusDetail.value = "未配置 API Key：对话创作与演化扩写将使用离线模板。";
    return;
  }
  await persistLlmConfig();
  try {
    const result = await llmServerPing("你好");
    aiStatus.value = "ok";
    aiStatusDetail.value = `功能正常（${String(result.model || llmModel.value)} 响应正常）`;
  } catch (error) {
    aiStatus.value = "error";
    aiStatusDetail.value = apiErrorMessage(error);
  }
}

function toggleAiPanel(): void {
  aiPanelOpen.value = !aiPanelOpen.value;
  if (aiPanelOpen.value) {
    void loadLlmServerConfig();
    if (aiStatus.value === "unset") {
      void runAiCheck();
    }
  }
}

async function applyLlmProvider(provider: "deepseek" | "openai" | "custom"): Promise<void> {
  llmPreset.value = provider;
  if (provider === "deepseek") {
    llmBaseUrl.value = "https://api.deepseek.com/v1";
    llmModel.value = "deepseek-chat";
  } else if (provider === "openai") {
    llmBaseUrl.value = "https://api.openai.com/v1";
    llmModel.value = "gpt-4o-mini";
  }
  await persistLlmConfig();
  markSaved("模型预设已切换");
}

async function persistLlmConfig(): Promise<void> {
  try {
    const config = await saveLlmServerConfig({
      base_url: llmBaseUrl.value.trim() || undefined,
      model: llmModel.value.trim() || undefined,
      preset: llmPreset.value,
      api_key: llmApiKey.value.trim() || undefined,
    });
    llmConfigured.value = config.configured;
    llmMaskedKey.value = config.masked_key;
    llmApiKey.value = "";
  } catch {
    // 保存失败时保持现状
  }
}

async function saveLlmConfig(): Promise<void> {
  await persistLlmConfig();
  markSaved("模型设置已保存");
  toastSuccess("模型设置已保存");
  void runAiCheck();
}

async function loadLlmServerConfig(): Promise<void> {
  try {
    const config = await getLlmServerConfig();
    llmConfigured.value = config.configured;
    llmBaseUrl.value = config.base_url || llmBaseUrl.value;
    llmModel.value = config.model || llmModel.value;
    llmPreset.value = config.preset || llmPreset.value;
    llmMaskedKey.value = config.masked_key;
  } catch {
    llmConfigured.value = false;
  }
}

function clearLlmKey(): void {
  void saveLlmServerConfig({clear_key: true}).then((config) => {
    llmConfigured.value = config.configured;
    llmMaskedKey.value = config.masked_key;
    markSaved("API Key 已清除");
  });
}

function toggleAiAutoProse(): void {
  localStorage.setItem("rhine-lore-ai-auto", aiAutoProse.value ? "1" : "0");
}

function evolutionProseKey(state: EvolutionState, viewpointId: string): string {
  const latestTurn = state.history.length > 0 ? state.history[state.history.length - 1].turn : state.turn;
  return `${latestTurn}:${viewpointId}`;
}

const evolutionNovelChapters = computed(() => {
  const state = evolutionState.value;
  const novel = evolutionView.value?.novel;
  if (!state || !novel) {
    return [];
  }
  const viewpointId = evolutionViewpoint.value || novel.viewpoint_id;
  const parts = novel.chapters.map((chapter) => {
    const aiText = state.ai_prose?.[`${chapter.turn}:${viewpointId}`];
    if (aiText) {
      return {turn: chapter.turn, paragraphs: [aiText]};
    }
    return {turn: chapter.turn, paragraphs: chapter.paragraphs};
  });
  const groups: {
    index: number;
    title: string;
    startTurn: number;
    endTurn: number;
    actName: string;
    paragraphs: string[];
  }[] = [];
  const chapterSize = evolutionChapterSize.value;
  for (const part of parts) {
    const groupIndex = Math.floor((part.turn - 1) / chapterSize);
    let group = groups.find((item) => Math.floor((item.startTurn - 1) / chapterSize) === groupIndex);
    if (!group) {
      group = {
        index: groups.length,
        title: `第${groups.length + 1}章`,
        startTurn: part.turn,
        endTurn: part.turn,
        actName: evolutionActNameForTurn(part.turn),
        paragraphs: [],
      };
      groups.push(group);
    }
    group.endTurn = part.turn;
    group.paragraphs.push(...part.paragraphs);
  }
  for (const group of groups) {
    const chapterText = state.ai_prose?.[`chapter:${group.startTurn}:${viewpointId}`];
    if (chapterText) {
      group.paragraphs = [chapterText];
    }
  }
  return groups;
});

const evolutionActiveChapter = computed(() => {
  const chapters = evolutionNovelChapters.value;
  const index = Math.min(evolutionChapterIndex.value, Math.max(0, chapters.length - 1));
  return chapters[index] ?? null;
});

const readerSource = computed<ReaderSource | null>(() => {
  if (activity.value === "novel") return "novel";
  if (activity.value === "read") return "evolution";
  if (activity.value === "shelf" && shelfBook.value) return "shelf";
  return null;
});

const readerWorkId = computed(() => {
  if (readerSource.value === "shelf") return shelfBookId.value;
  return activeProject.value.id;
});

const readerWorkTitle = computed(() => {
  if (readerSource.value === "shelf") return shelfBook.value?.name || "TXT 书籍";
  if (readerSource.value === "evolution") return `${activeProject.value.name} · 演化小说`;
  return activeProject.value.name;
});

const readerCurrentChapterId = computed(() => {
  if (readerSource.value === "shelf") return shelfChapter.value?.id || "";
  if (readerSource.value === "evolution") return evolutionActiveChapter.value ? String(evolutionActiveChapter.value.index) : "";
  return activeChapter.value?.id || "";
});

const readerCurrentTitle = computed(() => {
  if (readerSource.value === "shelf") return shelfChapter.value?.title || "";
  if (readerSource.value === "evolution") return evolutionActiveChapter.value?.title || "";
  return activeChapter.value?.title || "";
});

const readerCurrentParagraphs = computed(() => {
  if (readerSource.value === "shelf") {
    return shelfChapter.value ? shelfChapterParagraphs(shelfChapter.value) : [];
  }
  if (readerSource.value === "evolution") {
    return (evolutionActiveChapter.value?.paragraphs ?? []).flatMap(splitReaderParagraphs);
  }
  return activeChapterParagraphs.value;
});

const readerTocItems = computed<ReaderTocItem[]>(() => {
  if (readerSource.value === "shelf") {
    const chapters = shelfBook.value?.chapters ?? [];
    return chapters.map((chapter, index) => {
      const chapterNumber = chapters.slice(0, index + 1).filter((item) => !isReaderVolumeTitle(item.title)).length;
      return {
        id: chapter.id,
        title: chapter.title,
        meta: isReaderVolumeTitle(chapter.title)
          ? `卷 · 全书 ${index + 1} / ${chapters.length}`
          : `第 ${chapterNumber} 章 · ${chapter.char_count.toLocaleString()} 字`,
      };
    });
  }
  if (readerSource.value === "evolution") {
    return evolutionNovelChapters.value.map((chapter) => ({
      id: String(chapter.index),
      title: chapter.title,
      meta: `${chapter.actName} · ${chapter.paragraphs.join("\n").length.toLocaleString()} 字`,
    }));
  }
  const chapters = activeProject.value.chapters;
  return chapters.map((chapter, index) => {
    const chapterNumber = chapters.slice(0, index + 1).filter((item) => !isReaderVolumeTitle(item.title)).length;
    return {
      id: chapter.id,
      title: chapter.title,
      meta: isReaderVolumeTitle(chapter.title)
        ? `卷 · 全书 ${index + 1} / ${chapters.length}`
        : `第 ${chapterNumber} 章 · ${chapterLength(chapter).toLocaleString()} 字`,
    };
  });
});

const readerCurrentChapterIndex = computed(() => {
  if (readerSource.value === "shelf") return shelfChapterIndex.value;
  if (readerSource.value === "evolution") return evolutionChapterIndex.value;
  return activeChapterIndex.value;
});

const readerCurrentBookmarks = computed(() =>
  readerBookmarks.value.filter(
    (item) => item.source === readerSource.value && item.workId === readerWorkId.value,
  ),
);

const readerCurrentBookmark = computed(() =>
  readerCurrentBookmarks.value.find((item) => item.chapterId === readerCurrentChapterId.value),
);

const readerEstimatedMinutes = computed(() => {
  const chars = readerCurrentParagraphs.value.join("").length;
  return chars > 0 ? Math.max(1, Math.ceil(chars / 350)) : 0;
});

const readerCurrentTitleIsVolume = computed(() => isReaderVolumeTitle(readerCurrentTitle.value));

const readerTitlePageMeta = computed(() => {
  const items = readerTocItems.value;
  const index = readerCurrentChapterIndex.value;
  if (index < 0 || items.length === 0) return "";
  if (readerCurrentTitleIsVolume.value) {
    return `卷 · 全书 ${index + 1} / ${items.length}`;
  }
  const chapters = items.filter((item) => !isReaderVolumeTitle(item.title));
  const chapterNumber = items.slice(0, index + 1).filter((item) => !isReaderVolumeTitle(item.title)).length;
  const chars = readerCurrentParagraphs.value.join("").length;
  return `第 ${chapterNumber} / ${chapters.length} 章${chars > 0 ? ` · ${chars.toLocaleString()} 字` : ""}`;
});

const readerOverallProgress = computed(() => {
  const total = readerTocItems.value.length;
  const index = readerCurrentChapterIndex.value;
  if (total <= 0 || index < 0) return 0;
  return Math.min(100, ((index + readingProgress.value / 100) / total) * 100);
});

watch([readerSource, readerWorkId], () => {
  readerSearchQuery.value = "";
  readerSearchResults.value = [];
  readingProgress.value = 0;
});

watch([activity, readerCurrentChapterId], async () => {
  capturedBranchSelection.value = null;
  await nextTick();
  bindReaderScrollListener(readerScrollContainer());
});

function readerPositionKey(source = readerSource.value, workId = readerWorkId.value): string {
  return `rhine-lore-reader-position-${source || "none"}-${workId || "none"}`;
}

function loadReaderPosition(source = readerSource.value, workId = readerWorkId.value): ReaderPosition | null {
  try {
    const value = JSON.parse(localStorage.getItem(readerPositionKey(source, workId)) || "null") as ReaderPosition | null;
    return value && typeof value.chapterId === "string" ? value : null;
  } catch {
    return null;
  }
}

function saveReaderPosition(): void {
  if (!readerSource.value || !readerWorkId.value || !readerCurrentChapterId.value) return;
  const position: ReaderPosition = {
    chapterId: readerCurrentChapterId.value,
    progress: readingProgress.value,
    pageIndex: readerPageIndex.value,
  };
  localStorage.setItem(readerPositionKey(), JSON.stringify(position));
}

function scheduleReaderPositionSave(): void {
  if (readerPositionTimer) window.clearTimeout(readerPositionTimer);
  readerPositionTimer = window.setTimeout(saveReaderPosition, 240);
}

async function restoreReaderProgress(position: ReaderPosition | null): Promise<void> {
  if (!position) return;
  await nextTick();
  requestAnimationFrame(() => {
    if (readerPageMode.value === "page") {
      readerPageIndex.value = Math.min(Math.max(0, position.pageIndex), Math.max(0, readerPages.value.length - 1));
      readingProgress.value = readerPages.value.length > 0
        ? ((readerPageIndex.value + 1) / readerPages.value.length) * 100
        : position.progress;
      return;
    }
    const wrap = readerScrollContainer();
    if (wrap) {
      const max = Math.max(0, wrap.scrollHeight - wrap.clientHeight);
      wrap.scrollTop = max * Math.min(1, Math.max(0, position.progress / 100));
      updateReadingProgress();
    }
  });
}

async function selectReaderChapter(chapterId: string, closeNavigator = true): Promise<void> {
  saveReaderPosition();
  if (readerSource.value === "shelf") {
    await loadShelfChapter(chapterId);
  } else if (readerSource.value === "evolution") {
    selectReadingChapter(Number(chapterId));
  } else {
    selectChapter(chapterId);
  }
  readerPageIndex.value = 0;
  if (readerPageMode.value === "page") await repaginate();
  if (closeNavigator) readerNavigatorVisible.value = false;
}

function openReaderNavigator(tab: "toc" | "search" | "bookmarks" = "toc"): void {
  readerNavigatorTab.value = tab;
  readerNavigatorVisible.value = true;
  if (tab === "search" && readerSearchQuery.value.trim() && readerSearchResults.value.length === 0) {
    void runReaderSearch();
  }
}

function searchReaderChapter(content: string, chapterId: string, title: string, query: string): ReaderSearchItem | null {
  const lowerContent = content.toLocaleLowerCase();
  const lowerQuery = query.toLocaleLowerCase();
  let cursor = 0;
  let matches = 0;
  while ((cursor = lowerContent.indexOf(lowerQuery, cursor)) >= 0) {
    matches += 1;
    cursor += Math.max(1, lowerQuery.length);
  }
  if (matches === 0) return null;
  const first = lowerContent.indexOf(lowerQuery);
  const clean = content.replace(/\s+/g, " ").trim();
  const cleanFirst = clean.toLocaleLowerCase().indexOf(lowerQuery);
  const start = Math.max(0, (cleanFirst >= 0 ? cleanFirst : first) - 34);
  const end = Math.min(clean.length, start + query.length + 78);
  return {
    id: `${chapterId}-${first}`,
    chapterId,
    title,
    snippet: `${start > 0 ? "…" : ""}${clean.slice(start, end)}${end < clean.length ? "…" : ""}`,
    matches,
  };
}

async function runReaderSearch(): Promise<void> {
  const query = readerSearchQuery.value.trim();
  if (!query || !readerSource.value) {
    readerSearchResults.value = [];
    return;
  }
  readerSearching.value = true;
  try {
    let chapters: {id: string; title: string; content: string}[] = [];
    if (readerSource.value === "novel") {
      chapters = activeProject.value.chapters.map((chapter) => ({...chapter}));
    } else if (readerSource.value === "evolution") {
      chapters = evolutionNovelChapters.value.map((chapter) => ({
        id: String(chapter.index),
        title: chapter.title,
        content: chapter.paragraphs.join("\n\n"),
      }));
    } else if (shelfBook.value && shelfBookId.value) {
      const bookId = shelfBookId.value;
      chapters = await Promise.all(
        shelfBook.value.chapters.map(async (chapter) => {
          if (shelfChapter.value?.id === chapter.id) {
            return {id: chapter.id, title: shelfChapter.value.title, content: shelfChapter.value.content};
          }
          const result = await getBookChapter(bookId, chapter.id);
          return {id: chapter.id, title: result.chapter.title, content: result.chapter.content};
        }),
      );
    }
    readerSearchResults.value = chapters
      .map((chapter) => searchReaderChapter(chapter.content, chapter.id, chapter.title, query))
      .filter((item): item is ReaderSearchItem => Boolean(item));
  } catch (error) {
    toastError(error instanceof Error ? error.message : "全书搜索失败");
  } finally {
    readerSearching.value = false;
  }
}

async function openReaderSearchResult(item: ReaderSearchItem): Promise<void> {
  await selectReaderChapter(item.chapterId);
}

function persistReaderBookmarks(): void {
  localStorage.setItem("rhine-lore-reader-bookmarks", JSON.stringify(readerBookmarks.value));
}

function toggleReaderBookmark(): void {
  const current = readerCurrentBookmark.value;
  if (current) {
    removeReaderBookmark(current.id);
    toastSuccess("已移除本章书签");
    return;
  }
  if (!readerSource.value || !readerCurrentChapterId.value) return;
  const content = readerCurrentParagraphs.value.join(" ").trim();
  const offset = Math.max(0, Math.floor((content.length - 70) * readingProgress.value / 100));
  readerBookmarks.value.unshift({
    id: uid("reader-bookmark"),
    source: readerSource.value,
    workId: readerWorkId.value,
    chapterId: readerCurrentChapterId.value,
    title: readerCurrentTitle.value,
    excerpt: content.slice(offset, offset + 70),
    progress: readingProgress.value,
    createdAt: new Date().toLocaleString("zh-CN", {month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"}),
  });
  persistReaderBookmarks();
  toastSuccess("书签已保存");
}

function removeReaderBookmark(id: string): void {
  readerBookmarks.value = readerBookmarks.value.filter((item) => item.id !== id);
  persistReaderBookmarks();
}

async function openReaderBookmark(item: ReaderBookmarkItem): Promise<void> {
  await selectReaderChapter(item.chapterId);
  await restoreReaderProgress({chapterId: item.chapterId, progress: item.progress, pageIndex: 0});
}

function toggleReaderFullscreen(): void {
  if (!document.fullscreenElement) {
    void document.documentElement.requestFullscreen?.().catch(() => undefined);
  } else {
    void document.exitFullscreen?.().catch(() => undefined);
  }
}

function handleReaderFullscreenChange(): void {
  readerFullscreenActive.value = Boolean(document.fullscreenElement);
}

function evolutionActNameForTurn(turn: number): string {
  if (turn <= 5) return "序幕";
  if (turn <= 12) return "发展";
  if (turn <= 18) return "转折";
  if (turn <= 24) return "高潮";
  return "尾声";
}

function openEvolutionAdjacentChapter(direction: -1 | 1): void {
  const next = evolutionChapterIndex.value + direction;
  if (next < 0 || next >= evolutionNovelChapters.value.length) {
    return;
  }
  evolutionChapterIndex.value = next;
  resetReaderScroll();
}

function selectReadingChapter(index: number): void {
  evolutionChapterIndex.value = index;
  resetReaderScroll();
}

function setChapterTurns(turns: number): void {
  activeProject.value.chapter_turns = Math.min(8, Math.max(1, Number(turns) || 4));
  saveProjects();
  markSaved(`单章长度已设为 ${activeProject.value.chapter_turns} 回合`);
}

async function generateNextChapter(): Promise<void> {
  const project = activeProject.value;
  const state = evolutionState.value;
  if (!project || !state || chapterBusy.value) {
    return;
  }
  chapterBusy.value = true;
  try {
    if (chapterGuidanceInput.value.trim()) {
      evolutionGuidance.value = chapterGuidanceInput.value.trim();
      await saveEvolutionGuidance();
    }
    const view = await advanceEvolutionChapter({
      project_id: project.id,
      viewpoint_id: evolutionViewpoint.value || "",
      turns: evolutionChapterSize.value,
      global_guidance: project.global_guidance || "",
      writing_style: project.writing_style || "",
      style_card: buildStyleCard(),
      quality_pass: project.polish_writing,
    });
    evolutionView.value = view;
    evolutionGuidance.value = view.state.guidance ?? "";
    evolutionChapterIndex.value = Math.max(0, evolutionNovelChapters.value.length - 1);
    chapterGuidanceInput.value = "";
    markSaved("下一章已生成");
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  } finally {
    chapterBusy.value = false;
  }
}

async function regenerateCurrentChapter(): Promise<void> {
  const project = activeProject.value;
  const state = evolutionState.value;
  const chapter = evolutionActiveChapter.value;
  if (!project || !state || !chapter || chapterBusy.value) {
    return;
  }
  if (!llmConfigured.value) {
    runState.value = {error: "重新生成本章需要 AI 通道，请先配置 API Key"};
    return;
  }
  chapterBusy.value = true;
  try {
    const view = await regenerateEvolutionChapter({
      project_id: project.id,
      viewpoint_id: evolutionViewpoint.value || "",
      start_turn: chapter.startTurn,
      end_turn: chapter.endTurn,
      global_guidance: project.global_guidance || "",
      writing_style: project.writing_style || "",
      style_card: buildStyleCard(),
      quality_pass: project.polish_writing,
    });
    evolutionView.value = view;
    evolutionGuidance.value = view.state.guidance ?? "";
    markSaved("本章已重新生成");
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  } finally {
    chapterBusy.value = false;
  }
}

async function generateStoredProse(): Promise<void> {
  const project = activeProject.value;
  const state = evolutionState.value;
  if (!project || !state || aiGenerating.value) {
    return;
  }
  aiGenerating.value = true;
  try {
    const view = await generateEvolutionProseApi({
      project_id: project.id,
      viewpoint_id: evolutionViewpoint.value || "",
      global_guidance: activeProject.value.global_guidance || "",
      writing_style: activeProject.value.writing_style || "",
      style_card: buildStyleCard(),
      quality_pass: activeProject.value.polish_writing,
    });
    if (view) {
      evolutionView.value = view;
      evolutionGuidance.value = view.state.guidance ?? "";
    }
  } catch {
    // 生成失败时保留模板正文，不打断演化。
  } finally {
    aiGenerating.value = false;
  }
}

async function generateEvolutionProse(): Promise<void> {
  const state = evolutionState.value;
  if (!state || aiProseBusy.value) {
    return;
  }
  aiProseBusy.value = true;
  const result = await perform("AI 扩写", () =>
    generateEvolutionProseApi({
      project_id: activeProject.value.id,
      viewpoint_id: evolutionViewpoint.value || "",
      global_guidance: activeProject.value.global_guidance || "",
      writing_style: activeProject.value.writing_style || "",
      style_card: buildStyleCard(),
      quality_pass: activeProject.value.polish_writing,
    }),
  );
  aiProseBusy.value = false;
  if (!result) {
    return;
  }
  evolutionView.value = result;
  evolutionGuidance.value = result.state.guidance ?? "";
  const viewpointId = evolutionViewpoint.value || (result.state.cast[0]?.id ?? "");
  aiProse.value = result.state.ai_prose?.[evolutionProseKey(result.state, viewpointId)] ?? "";
  if (aiProse.value) {
    markSaved("AI 扩写完成，已保存到演化存档");
  }
}

function appendAIProseToChapter(): void {
  const text = aiProse.value.trim();
  const state = evolutionState.value;
  if (!text || !state) {
    return;
  }
  let chapter = activeChapter.value;
  if (!chapter) {
    addChapter();
    chapter = activeChapter.value;
  }
  if (!chapter) {
    return;
  }
  chapter.content = [
    chapter.content.trim(),
    `## AI 扩写 · 第 ${state.turn} 回合`,
    "",
    text,
  ]
    .filter(Boolean)
    .join("\n\n");
  saveProjects();
  markSaved("AI 扩写已追加进正文");
  readerMode.value = "edit";
  activity.value = "novel";
}

async function testLlmConnection(): Promise<void> {
  await runAiCheck();
  if (aiStatus.value === "ok") {
    markSaved("AI 通道功能正常");
  } else if (aiStatus.value === "error") {
    runState.value = {error: aiStatusDetail.value};
  }
}

function openDeepSeekKeyAssistant(): void {
  const bridge = (
    window as unknown as {
      AndroidBridge?: {openDeepSeekLogin?: () => void};
    }
  ).AndroidBridge;
  if (bridge?.openDeepSeekLogin) {
    bridge.openDeepSeekLogin();
    return;
  }
  window.open("https://platform.deepseek.com/", "_blank", "noopener");
  markSaved("已打开 DeepSeek 控制台：登录后创建 API Key 并复制，再点「从剪贴板读取」");
}

async function pasteDeepSeekKey(): Promise<void> {
  try {
    if (!navigator.clipboard?.readText) {
      runState.value = {error: "当前环境不支持读取剪贴板，请手动把 Key 粘贴到上方输入框"};
      return;
    }
    const text = await navigator.clipboard.readText();
    const match = (text || "").trim().match(/sk-[A-Za-z0-9_-]{16,}/);
    if (!match) {
      runState.value = {error: "剪贴板中没有找到 sk- 开头的 API Key"};
      return;
    }
    await perform("配置 DeepSeek Key", () =>
      saveLlmServerConfig({
        base_url: "https://api.deepseek.com",
        api_key: match[0],
        model: llmModel.value.trim() || "deepseek-chat",
        preset: "deepseek",
      }),
    );
    await loadLlmServerConfig();
    markSaved("DeepSeek API Key 已配置");
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  }
}

onUnmounted(() => {
  delete (window as NativeBackWindow).rhineLoreHandleBack;
  flushPendingProjectDrafts();
  window.matchMedia("(prefers-color-scheme: dark)").removeEventListener("change", handleSystemThemeChange);
  document.removeEventListener("click", closeChatMore);
  window.removeEventListener("scroll", handleReadingScroll);
  readerBoundScrollElement?.removeEventListener("scroll", handleReadingScroll);
  window.removeEventListener("resize", handleReaderResize);
  window.removeEventListener("keydown", handleReaderOverlayKeydown);
  window.removeEventListener("pagehide", handleProjectPageHide);
  document.removeEventListener("fullscreenchange", handleReaderFullscreenChange);
  for (const timer of projectDraftTimers.values()) window.clearTimeout(timer);
  for (const timer of projectBackupTimers.values()) window.clearTimeout(timer);
  projectDraftTimers.clear();
  projectBackupTimers.clear();
  if (readerPositionTimer) window.clearTimeout(readerPositionTimer);
  if (readerResizeTimer) window.clearTimeout(readerResizeTimer);
  clearShelfAnalysisPoll();
  if (evolutionTimer) {
    window.clearInterval(evolutionTimer);
    evolutionTimer = undefined;
  }
});
</script>

<template>
  <div
    class="app-shell"
    :class="{'sidebar-collapsed': sidebarCollapsed, 'mobile-nav-open': mobileNavOpen}"
  >
    <input
      ref="projectImportInput"
      class="sr-only"
      type="file"
      accept="application/json"
      @change="importProjectFile"
    />
    <input
      ref="shelfImportInput"
      class="sr-only"
      type="file"
      accept=".txt,.text,text/plain"
      @change="handleShelfTxtImport"
    />
    <input
      ref="chatAttachInput"
      class="sr-only"
      type="file"
      accept=".txt,.text,.json,text/plain,application/json"
      @change="handleChatAttach"
    />
    <aside class="sidebar">
      <button
        ref="mobileCloseBtnRef"
        class="sidebar-close mobile-only"
        type="button"
        aria-label="关闭菜单"
        @click="closeMobileNav"
      >
        <GameIcon name="close" :size="20" />
      </button>
      <div class="sidebar-project">
        <el-select
          v-model="activeProjectId"
          class="project-select"
          size="small"
          @change="handleProjectChange"
        >
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
      </div>
      <div class="sidebar-mode-switch" role="group" aria-label="侧边栏模式">
        <button
          type="button"
          :class="{active: sidebarMode === 'workbench'}"
          :aria-pressed="sidebarMode === 'workbench'"
          @click="setSidebarMode('workbench')"
        >
          <GameIcon name="pen" :size="15" />
          工作台
        </button>
        <button
          type="button"
          :class="{active: sidebarMode === 'reader'}"
          :aria-pressed="sidebarMode === 'reader'"
          @click="setSidebarMode('reader')"
        >
          <GameIcon name="book-open" :size="15" />
          阅读器
        </button>
      </div>
      <nav class="sidebar-nav" aria-label="主导航">
        <div v-for="group in visibleActivityGroups" :key="group.label" class="sidebar-nav-group">
          <span class="sidebar-nav-group-label">{{ group.label }}</span>
          <el-button
            v-for="item in group.items"
            :key="item.id"
            class="nav-item"
            :class="{
              active: activity === item.id,
              'nav-item-secondary': !isPrimaryActivity(item.id),
              'mobile-parent-active': isStudioChildActivity(item.id),
              'nav-chat': item.id === 'chat',
            }"
            :aria-current="activity === item.id ? 'page' : undefined"
            @click="openActivity(item.id); mobileNavOpen = false"
            :title="sidebarCollapsed ? item.label : ''"
          >
            <span class="nav-icon-dot"><GameIcon :name="item.icon" :label="item.label" /></span>
            <span class="nav-label">
              <strong>{{ item.label }}</strong>
              <small>{{ item.description }}</small>
            </span>
          </el-button>
        </div>
      </nav>
      <div class="sidebar-footer">
        <span class="sidebar-footer-status">
          <span class="status-dot" :class="backendStatusTone" />
          {{ backendStatusLabel }}
        </span>
        <span class="sidebar-footer-meta">
          <img class="sidebar-footer-brand" :src="rhineLoreMark" alt="Rhine-Lore">
          v0.1.0
        </span>
      </div>
      <el-button
        class="collapse-button"
        title="折叠/展开侧边栏"
        aria-label="折叠/展开侧边栏"
        :aria-expanded="!sidebarCollapsed"
        @click="toggleSidebar"
      >
        <GameIcon
          :name="sidebarCollapsed ? 'panel-left-open' : 'panel-left-close'"
          :size="17"
        />
      </el-button>
    </aside>

    <div v-if="mobileNavOpen" class="sidebar-backdrop" @click="closeMobileNav" />

    <section class="workspace" :class="{'no-topbar': activity === 'chat'}">
      <header v-if="activity !== 'chat'" class="workspace-topbar">
        <el-button
          ref="mobileMenuBtnRef"
          class="mobile-menu-button"
          aria-label="打开菜单"
          :aria-expanded="mobileNavOpen"
          @click="openMobileNav"
        >
          <GameIcon name="menu" :size="19" />
        </el-button>
        <div class="workspace-title-group">
          <span class="section-icon"><GameIcon :name="activeTabMeta.icon" /></span>
          <div>
            <strong>{{ activeTabMeta.label }}</strong>
            <small>
              {{ activeProject?.name ?? "未选择故事" }}
              <span class="topbar-notice"> · {{ notice }}</span>
            </small>
          </div>
        </div>
        <div class="workspace-topbar-actions">
          <button class="backend-chip ai-status-chip" :class="aiStatusTone" type="button" @click="toggleAiPanel">
            <span class="status-dot" />
            <span>AI：{{ aiStatusLabel }}</span>
          </button>
        </div>
      </header>

      <el-scrollbar class="workspace-main" :class="{'chat-workspace-main': activity === 'chat'}">
        <main
          ref="contentMainRef"
          tabindex="-1"
          class="content-grid"
          :class="{'content-grid--chat': activity === 'chat'}"
          :aria-label="activeTabMeta.label"
        >
          <section v-if="activity === 'studio'" class="activity-panel home-panel">
            <el-card shadow="never" class="home-hero">
              <div class="home-hero-main">
                <div class="home-hero-copy">
                  <p class="home-kicker">写作引导台</p>
                  <h2>{{ activeProject.name || "未命名故事" }}</h2>
                  <p>{{ activeProject.summary || "选择一个故事，然后进入正文、对话或资料库继续创作。" }}</p>
                  <div class="hero-meta">
                    <span>{{ activeProject.genre || "未分类" }}</span>
                    <span>{{ activeProject.chapters.length }} 章</span>
                    <span>{{ projectCharacterCount }} 字</span>
                  </div>
                </div>
                <el-space wrap class="home-hero-actions">
                  <el-button type="primary" @click="startWriting">
                    {{ activeProject.chapters.length > 0 ? "继续写作" : "写第一章" }}
                  </el-button>
                  <el-button @click="activity = 'chat'">对话创作</el-button>
                  <el-button @click="activity = 'evolution'">演化沙盘</el-button>
                </el-space>
              </div>
              <HomeIllustration class="home-hero-art" />
            </el-card>

            <button class="ai-entry-banner" type="button" @click="openActivity('chat')">
              <img class="ai-entry-logo" :src="rhineLoreMark" alt="Rhine-Lore">
              <span class="ai-entry-copy">
                <strong>AI 创作助手</strong>
                <small>续写 · 修订 · 导入 · 角色与设定管理</small>
              </span>
              <span class="ai-entry-arrow"><GameIcon name="arrow-right" :size="20" /></span>
            </button>

            <div class="home-path-row">
              <span class="home-path-label">创作路径</span>
              <button
                v-for="step in createPathSteps"
                :key="step.index"
                type="button"
                class="home-path-chip"
                @click="step.action()"
              >
                <span class="home-path-index">{{ step.index }}</span>
                <span class="home-path-copy">
                  <strong>{{ step.label }}</strong>
                  <small>{{ step.hint }}</small>
                </span>
                <i aria-hidden="true"><GameIcon name="chevron-right" :size="16" /></i>
              </button>
            </div>

            <div class="home-quick-grid">
              <button class="home-quick-tile" type="button" @click="startWriting">
                <span class="home-quick-icon"><GameIcon name="pen" label="正文" /></span>
                <strong>正文</strong>
                <small>{{ activeProject.chapters.length > 0 ? "继续写作" : "写第一章" }}</small>
              </button>
              <button class="home-quick-tile" type="button" @click="openActivity('read')">
                <span class="home-quick-icon"><GameIcon name="book-open" label="小说阅读" /></span>
                <strong>小说阅读</strong>
                <small>追演化连载</small>
              </button>
              <button class="home-quick-tile" type="button" @click="openActivity('shelf')">
                <span class="home-quick-icon"><GameIcon name="library" label="书架" /></span>
                <strong>书架</strong>
                <small>TXT 长篇小说</small>
              </button>
              <button class="home-quick-tile" type="button" @click="openActivity('context')">
                <span class="home-quick-icon"><GameIcon name="database" label="资料库" /></span>
                <strong>资料库</strong>
                <small>草稿与检索</small>
              </button>
            </div>

            <section v-if="needsProjectGuidance" class="setup-guide">
              <div class="setup-guide-copy">
                <span>从这里开始</span>
                <strong>{{ nextStepLabel }}</strong>
                <small>不用先配置世界观或 AI，写下第一个想法就可以继续。</small>
              </div>
              <div class="setup-steps" aria-label="故事开始进度">
                <div
                  v-for="(step, index) in projectSetupSteps"
                  :key="step.label"
                  class="setup-step"
                  :class="{complete: step.complete}"
                >
                  <span>{{ step.complete ? "✓" : index + 1 }}</span>
                  <strong>{{ step.label }}</strong>
                </div>
              </div>
              <el-button type="primary" @click="continueSetup">{{ nextStepLabel }}</el-button>
            </section>

            <div v-if="projects.length === 0 && diskBackups.length > 0" class="disk-restore-strip">
              <div>
                <strong>检测到磁盘备份</strong>
                <small>项目列表被浏览器清空，但磁盘上还有 {{ diskBackups.length }} 份项目备份，可以一键恢复。</small>
              </div>
              <el-button size="small" type="primary" @click="openRestoreDialog">从磁盘恢复</el-button>
            </div>

            <el-card shadow="never" class="story-picker-card">
              <template #header>
                <div class="card-header">
                  <span>我的故事</span>
                  <el-space wrap>
                    <el-button size="small" type="primary" @click="createProject">新建故事</el-button>
                    <el-button size="small" @click="requestProjectImport">导入</el-button>
                    <el-button size="small" @click="openRestoreDialog">从磁盘恢复</el-button>
                  </el-space>
                </div>
              </template>
              <EmptyState
                v-if="projects.length === 0"
                icon="home"
                title="创建你的第一个故事"
                description="故事是正文、AI 对话与演化的数据基础，先给它一个名字和一句话想法。"
                compact
              >
                <el-button type="primary" size="small" @click="createProject">新建故事</el-button>
                <el-button size="small" @click="activity = 'chat'">先聊聊想法</el-button>
              </EmptyState>
              <div v-else class="project-grid project-grid-home">
                <button
                  v-for="project in projects"
                  :key="project.id"
                  type="button"
                  class="project-card"
                  :class="{active: activeProject.id === project.id}"
                  @click="selectProject(project.id)"
                >
                  <span class="project-card-top">
                    <strong>{{ project.name || "未命名故事" }}</strong>
                    <small>{{ project.genre || "未分类" }}</small>
                  </span>
                  <span class="project-card-summary">
                    {{ preview(project.summary || "还没有概要。进入故事档案补上它。", 88) }}
                  </span>
                  <span class="project-card-meta">
                    <span>{{ project.chapters.length }} 章</span>
                    <span>{{ project.world.length }} 设定</span>
                    <span>{{ project.characters.length }} 角色</span>
                    <span>{{ projectLength(project) }} 字</span>
                  </span>
                </button>
              </div>
            </el-card>
          </section>

          <section v-else-if="activity === 'story'" class="activity-panel story-panel">
            <el-row :gutter="14">
              <el-col :xs="24" :lg="10">
                <el-card shadow="never">
                  <template #header>
                    <div class="card-header">
                      <span>故事档案</span>
                      <el-space wrap>
                        <el-button size="small" @click="createProject">新建故事</el-button>
                        <el-button size="small" @click="requestProjectImport">导入</el-button>
                        <el-button size="small" @click="exportActiveProject">导出</el-button>
                        <el-button size="small" @click="duplicateProject">复制</el-button>
                      </el-space>
                    </div>
                  </template>
                  <el-form label-position="top">
                    <el-form-item label="当前故事">
                      <el-select v-model="activeProjectId" @change="handleProjectChange">
                        <el-option
                          v-for="project in projects"
                          :key="project.id"
                          :label="project.name"
                          :value="project.id"
                        />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="名称">
                      <el-input v-model="activeProject.name" placeholder="给故事起一个容易记住的名字" @input="saveProjects" />
                    </el-form-item>
                    <el-form-item label="类型">
                      <el-input v-model="activeProject.genre" placeholder="例如：悬疑、奇幻、都市" @input="saveProjects" />
                    </el-form-item>
                    <el-form-item label="概要">
                      <el-input
                        v-model="activeProject.summary"
                        type="textarea"
                        :rows="8"
                        placeholder="用一两句话写下主角是谁、想做什么、会遇到什么困难"
                        @input="saveProjects"
                      />
                    </el-form-item>
                    <el-form-item label="全局引导">
                      <el-input
                        v-model="activeProject.global_guidance"
                        type="textarea"
                        :rows="3"
                        placeholder="贯穿整个故事的方向，例如：保持校园日常基调，百合线缓慢推进，伏笔必须回收"
                        @input="saveProjects"
                      />
                      <div class="preset-chips">
                        <button
                          v-for="preset in guidancePresets"
                          :key="preset"
                          type="button"
                          class="preset-chip"
                          @click="setGlobalGuidance(preset)"
                        >
                          {{ preset }}
                        </button>
                      </div>
                    </el-form-item>
                    <el-form-item>
                      <button
                        type="button"
                        class="fold-toggle"
                        @click="storyStyleOpen = !storyStyleOpen"
                      >
                        {{ storyStyleOpen ? "收起文风设置" : "展开文风设置（AI 写作基准）" }}
                      </button>
                    </el-form-item>
                    <template v-if="storyStyleOpen">
                    <el-form-item label="文风">
                      <div class="preset-chips">
                        <button
                          v-for="style in writingStylePresets"
                          :key="style"
                          type="button"
                          class="preset-chip"
                          :class="{used: activeProject.writing_style === style}"
                          @click="setWritingStyle(style)"
                        >
                          {{ style }}
                        </button>
                      </div>
                      <el-switch
                        v-model="activeProject.polish_writing"
                        active-text="生成后自动润色"
                        inactive-text="不润色"
                        @change="saveProjects"
                      />
                    </el-form-item>
                    <el-form-item label="风格参考（可选）">
                      <el-input
                        v-model="activeProject.style_example"
                        type="textarea"
                        :rows="4"
                        placeholder="粘贴一段你满意的正文，作为全故事的语感、句式、节奏基准"
                        @input="saveProjects"
                      />
                      <el-button size="small" @click="setStyleExampleFromChapter">
                        取当前正文为基准
                      </el-button>
                    </el-form-item>
                    <el-form-item label="风格要点（可选）">
                      <el-input
                        v-model="activeProject.style_notes"
                        placeholder="例如：多用短句；心理描写克制；对话带一点疏离感"
                        @input="saveProjects"
                      />
                    </el-form-item>
                    <el-form-item label="避免（可选）">
                      <el-input
                        v-model="activeProject.style_avoid"
                        placeholder="例如：避免华丽辞藻、网络用语、过度比喻"
                        @input="saveProjects"
                      />
                    </el-form-item>
                    </template>
                  </el-form>
                </el-card>
              </el-col>
              <el-col :xs="24" :lg="14">
                <el-card shadow="never" class="story-preview-card">
                  <template #header>故事预览</template>
                  <h3>{{ activeProject.name || "未命名故事" }}</h3>
                  <p>{{ activeProject.summary || "这里会显示故事概要，方便你在进入正文前快速找回方向。" }}</p>
                  <div class="stat-grid">
                    <div v-for="stat in stats" :key="stat.label" class="stat-card" :class="stat.tone">
                      <b>{{ stat.value }}</b>
                      <span>{{ stat.label }}</span>
                    </div>
                  </div>
                  <el-space wrap>
                    <el-button type="primary" @click="activity = 'novel'">写正文</el-button>
                    <el-button @click="activity = 'world'">编辑世界观</el-button>
                    <el-button @click="activity = 'characters'">编辑角色</el-button>
                  </el-space>
                </el-card>
              </el-col>
            </el-row>
          </section>

          <section v-else-if="activity === 'world'" class="activity-panel world-panel">
            <el-card shadow="never">
              <template #header>
                <div class="card-header">
                  <span>世界观设定</span>
                  <el-space wrap>
                    <el-button size="small" type="primary" @click="addLoreItem()">添加设定</el-button>
                    <el-button size="small" @click="activity = 'map'">打开地图</el-button>
                  </el-space>
                </div>
              </template>
              <EmptyState
                v-if="activeProject.world.length === 0"
                icon="globe"
                title="还没有世界观设定"
                description="先写地点、势力或规则；地点可以一键放置到地图，设定会进入演化与资料库。"
              >
                <el-button type="primary" @click="addLoreItem()">添加第一条设定</el-button>
                <el-button @click="activity = 'map'">看看地图</el-button>
              </EmptyState>
              <div class="world-card-grid">
                <div v-for="(item, index) in activeProject.world" :key="item.id" class="character-card world-card">
                  <div class="character-card-head">
                    <div class="character-card-avatar">{{ (item.name || "?").slice(0, 1) }}</div>
                    <div class="character-card-title">
                      <strong class="character-card-name">{{ item.name || "未命名" }}</strong>
                      <span class="character-card-type">{{ item.type }}</span>
                    </div>
                    <el-button size="small" @click="openWorldEditor(index)">编辑</el-button>
                  </div>
                  <div class="character-card-section">
                    <label>一句话概述</label>
                    <p class="card-readonly-text">{{ item.summary || "（空）" }}</p>
                  </div>
                  <div class="character-card-section">
                    <label>详细描述</label>
                    <p class="card-readonly-text">{{ item.details || "（空）" }}</p>
                  </div>
                  <div class="character-card-section">
                    <label>对故事的意义</label>
                    <p class="card-readonly-text">{{ item.significance || "（空）" }}</p>
                  </div>
                  <div class="character-card-section">
                    <label>标签</label>
                    <div class="cast-trait-chips">
                      <span v-for="tag in splitTags(item.tags)" :key="tag">{{ tag }}</span>
                    </div>
                  </div>
                  <div class="character-card-actions">
                    <el-button size="small" @click="submitLoreItem('world', item)">同步到资料库</el-button>
                    <el-button size="small" type="primary" @click="placeWorldOnMap(item)">放置到地图</el-button>
                    <el-button size="small" type="danger" plain @click="removeWorldItem(item)">删除</el-button>
                  </div>
                </div>
              </div>
            </el-card>

            <el-drawer v-model="worldEditVisible" title="编辑设定" direction="btt" size="82%">
              <div class="shelf-settings">
                <label>名称</label>
                <el-input v-model="worldDraft.name" placeholder="如：雾港" />
                <label>类型</label>
                <el-select v-model="worldDraft.type" style="width: 100%">
                  <el-option v-for="type in worldTypes" :key="type" :label="type" :value="type" />
                </el-select>
                <label>一句话概述</label>
                <el-input v-model="worldDraft.summary" type="textarea" :rows="2" />
                <label>详细描述</label>
                <el-input v-model="worldDraft.details" type="textarea" :rows="5" />
                <label>对故事的意义</label>
                <el-input v-model="worldDraft.significance" type="textarea" :rows="2" />
                <label>标签</label>
                <el-input v-model="worldDraft.tags" placeholder="港口、海雾（逗号分隔）" />
                <div class="preset-chips">
                  <button
                    v-for="tag in worldTagPresets[worldDraft.type] || worldTagPresets['其他']"
                    :key="tag"
                    type="button"
                    class="preset-chip"
                    :class="{used: hasTag(worldDraft.tags, tag)}"
                    @click="fillWorldTags(worldDraft, tag)"
                  >
                    {{ tag }}
                  </button>
                </div>
                <el-button type="primary" @click="saveWorldEditor">保存设定</el-button>
              </div>
            </el-drawer>
          </section>

          <section v-else-if="activity === 'map'" class="activity-panel map-panel">
            <el-card shadow="never" class="map-card map-immersive">
              <template #header>
                <div class="card-header">
                  <span>故事地图</span>
                  <el-space wrap>
                    <el-button size="small" type="primary" @click="addMapNode">添加地点</el-button>
                    <el-button
                      size="small"
                      :type="mapConnectMode ? 'primary' : 'default'"
                      @click="mapConnectMode = !mapConnectMode"
                    >
                      {{ mapConnectMode ? "连接中：点两个地点" : "连接" }}
                    </el-button>
                    <el-button size="small" @click="removeMapSelection">删除选中</el-button>
                    <el-button size="small" @click="mapZoomIn">放大</el-button>
                    <el-button size="small" @click="mapZoomOut">缩小</el-button>
                  </el-space>
                </div>
              </template>
              <EmptyState
                v-if="activeProject.map.nodes.length === 0"
                icon="map"
                title="地图还是空的"
                description="点击“添加地点”，或从世界观设定里一键放置地点，然后用“连接”画出路线。"
              >
                <el-button type="primary" @click="addMapNode">添加第一个地点</el-button>
                <el-button @click="activity = 'world'">去世界观放地点</el-button>
              </EmptyState>
              <svg
                class="story-map"
                :viewBox="mapViewBox"
                @pointerdown="onMapSvgPointerDown"
                @pointermove="onMapPointerMove"
                @pointerup="onMapPointerUp"
                @pointerleave="onMapPointerUp"
              >
                <line
                  v-for="edge in activeProject.map.edges"
                  :key="edge.id"
                  :x1="mapNodeX(edge.from)"
                  :y1="mapNodeY(edge.from)"
                  :x2="mapNodeX(edge.to)"
                  :y2="mapNodeY(edge.to)"
                  class="map-edge"
                  :class="{selected: mapSelectedEdgeId === edge.id}"
                  @click.stop="selectMapEdge(edge)"
                />
                <g
                  v-for="node in activeProject.map.nodes"
                  :key="node.id"
                  class="map-node-group"
                  :transform="`translate(${node.x},${node.y})`"
                  @pointerdown.stop="onMapNodePointerDown(node, $event)"
                  @click.stop="selectMapNode(node)"
                >
                  <circle
                    r="26"
                    class="map-node-circle"
                    :class="{selected: mapSelectedNodeId === node.id, pending: mapPendingNodeId === node.id}"
                  />
                  <text text-anchor="middle" dy="5" class="map-node-text">{{ (node.name || "?").slice(0, 4) }}</text>
                </g>
              </svg>
              <p class="map-edit-hint">
                拖动节点调整位置；点选连线可高亮，再按「删除选中」删除该连线；
                选中节点后可在下方编辑名称与描述。
              </p>
              <div v-if="mapSelectedNode" class="map-node-editor">
                <el-input v-model="mapSelectedNode.name" placeholder="地点名称" @input="saveProjects" />
                <el-input
                  v-model="mapSelectedNode.description"
                  type="textarea"
                  :rows="2"
                  placeholder="地点描述（会进入演化的事件发生地）"
                  @input="saveProjects"
                />
              </div>
            </el-card>
          </section>

          <section v-else-if="activity === 'characters'" class="activity-panel characters-panel">
            <el-card shadow="never">
              <template #header>
                <div class="card-header">
                  <span>角色卡</span>
                  <el-space wrap>
                    <el-button size="small" type="primary" @click="addCharacter">添加角色</el-button>
                    <el-button size="small" @click="activity = 'evolution'">去演化沙盘</el-button>
                  </el-space>
                </div>
              </template>
              <EmptyState
                v-if="activeProject.characters.length === 0"
                icon="users"
                title="还没有角色卡"
                description="角色卡驱动演化与 AI 一致性：从主角开始，写下名字、身份、欲望与恐惧。"
              >
                <el-button type="primary" @click="addCharacter">添加第一张角色卡</el-button>
                <el-button @click="activity = 'chat'">让 AI 生成一个</el-button>
              </EmptyState>
              <div class="character-card-grid">
                <div v-for="(card, index) in activeProject.characters" :key="card.id" class="character-card">
                  <div class="character-card-head">
                    <div class="character-card-avatar">{{ (card.name || "?").slice(0, 1) }}</div>
                    <div class="character-card-title">
                      <strong class="character-card-name">{{ card.name || "未命名" }}</strong>
                      <span class="character-card-type">
                        {{ card.role }}<template v-if="card.identity"> · {{ card.identity }}</template>
                      </span>
                    </div>
                    <el-button size="small" @click="openCharacterEditor(index)">编辑</el-button>
                  </div>

                  <div class="character-card-section character-detail-grid">
                    <div>
                      <label>欲望 / 目标</label>
                      <p class="card-readonly-text">{{ card.drive || "（空）" }}</p>
                    </div>
                    <div>
                      <label>恐惧</label>
                      <p class="card-readonly-text">{{ card.fear || "（空）" }}</p>
                    </div>
                  </div>

                  <div class="character-card-section">
                    <label>性格标签</label>
                    <div class="cast-trait-chips">
                      <span v-for="tag in splitTags(card.traits)" :key="tag">{{ tag }}</span>
                    </div>
                  </div>

                  <div class="character-card-section">
                    <label>秘密（会成为演化伏笔）</label>
                    <p class="card-readonly-text">{{ card.secret || "（空）" }}</p>
                  </div>

                  <div class="character-card-section">
                    <label>关系</label>
                    <p class="card-readonly-text">
                      {{
                        card.relationships.map((relation) => `${relation.name || "?"}（${relation.relation || "?"}）`).join("、") || "（无）"
                      }}
                    </p>
                  </div>

                  <div class="character-card-section">
                    <label>背景</label>
                    <p class="card-readonly-text">{{ card.background || "（空）" }}</p>
                  </div>

                  <div class="character-card-actions">
                    <el-button size="small" @click="submitLoreItem('characters', card)">同步到资料库</el-button>
                    <el-button size="small" type="danger" plain @click="removeCharacter(card)">删除</el-button>
                  </div>
                </div>
              </div>
            </el-card>

            <el-drawer v-model="characterEditVisible" title="编辑角色卡" direction="btt" size="88%">
              <div v-if="characterDraft" class="shelf-settings">
                <label>姓名</label>
                <el-input v-model="characterDraft.name" />
                <div class="character-identity-row">
                  <el-input v-model="characterDraft.identity" placeholder="身份 / 称号" />
                  <el-select v-model="characterDraft.role" style="width: 140px">
                    <el-option v-for="role in characterRoles" :key="role" :label="role" :value="role" />
                  </el-select>
                </div>
                <div class="character-detail-grid">
                  <div>
                    <label>年龄</label>
                    <el-input v-model="characterDraft.age" />
                  </div>
                  <div>
                    <label>立场 / 阵营</label>
                    <el-input v-model="characterDraft.stance" />
                  </div>
                  <div>
                    <label>能力 / 特长</label>
                    <el-input v-model="characterDraft.abilities" />
                  </div>
                  <div>
                    <label>弱点</label>
                    <el-input v-model="characterDraft.weakness" />
                  </div>
                </div>
                <label>欲望 / 目标</label>
                <el-input v-model="characterDraft.drive" />
                <label>恐惧</label>
                <el-input v-model="characterDraft.fear" />
                <label>性格标签</label>
                <el-input v-model="characterDraft.traits" placeholder="谨慎、毒舌、重情义" />
                <div class="preset-chips">
                  <button
                    v-for="tag in characterTraitPresets"
                    :key="tag"
                    type="button"
                    class="preset-chip"
                    :class="{used: hasTag(characterDraft.traits, tag)}"
                    @click="fillCharacterTraits(characterDraft, tag)"
                  >
                    {{ tag }}
                  </button>
                </div>
                <label>秘密（会成为演化伏笔）</label>
                <el-input v-model="characterDraft.secret" type="textarea" :rows="2" />
                <label>说话风格 / 口头禅</label>
                <el-input v-model="characterDraft.speech" />
                <label>外貌特征</label>
                <el-input v-model="characterDraft.appearance" type="textarea" :rows="3" />
                <label>背景故事</label>
                <el-input v-model="characterDraft.background" type="textarea" :rows="3" />
                <label>关系</label>
                <div
                  v-for="(relation, index) in characterDraft.relationships"
                  :key="index"
                  class="relationship-row"
                >
                  <el-input v-model="relation.name" placeholder="对方姓名" size="small" />
                  <el-input v-model="relation.relation" placeholder="关系，如：恋人 / 死敌" size="small" />
                  <el-button
                    size="small"
                    title="移除关系"
                    aria-label="移除关系"
                    @click="removeRelationship(characterDraft, index)"
                  >
                    <GameIcon name="close" :size="16" />
                  </el-button>
                </div>
                <el-button size="small" @click="addRelationship(characterDraft)">添加关系</el-button>
                <div class="character-status-row">
                  <div>
                    <label>当前状态</label>
                    <el-select v-model="characterDraft.status" style="width: 100%">
                      <el-option v-for="status in characterStatusOptions" :key="status" :label="status" :value="status" />
                    </el-select>
                  </div>
                  <div class="character-notes-field">
                    <label>备注</label>
                    <el-input v-model="characterDraft.notes" type="textarea" :rows="2" />
                  </div>
                </div>
                <el-button type="primary" @click="saveCharacterEditor">保存角色</el-button>
              </div>
            </el-drawer>
          </section>

          <section
            v-else-if="activity === 'chat'"
            class="activity-panel chat-panel"
            :class="{
              'chat-sidebar-closed': !chatSidebarOpen,
              'chat-sidebar-open': chatSidebarOpen,
            }"
          >
            <el-card shadow="never" class="chat-thread-card ai-chat-card">
              <div class="ai-chat-header">
                <el-button
                  class="mobile-menu-button"
                  aria-label="打开菜单"
                  :aria-expanded="mobileNavOpen"
                  @click="openMobileNav"
                >
                  <GameIcon name="menu" :size="19" />
                </el-button>
                <div class="ai-chat-title">
                  <img class="ai-chat-logo" :src="rhineLoreMark" alt="Rhine-Lore">
                  <div>
                    <strong>AI 创作助手</strong>
                    <small>{{ activeProject.name }} · {{ chatContextLabel }}</small>
                  </div>
                </div>
                <div class="ai-chat-header-actions">
                  <span class="llm-channel-chip">{{ llmChannelLabel }}</span>
                  <el-button
                    size="small"
                    text
                    :type="chatSidebarOpen ? 'primary' : 'default'"
                    @click="chatSidebarOpen = !chatSidebarOpen"
                  >
                    <GameIcon name="panel-right" :size="16" />
                    上下文
                    <span v-if="selectedKnowledgeNodes.length + pendingIssueCount > 0" class="ai-chat-badge">
                      {{ selectedKnowledgeNodes.length + pendingIssueCount }}
                    </span>
                  </el-button>
                  <el-radio-group v-model="chatMode" size="small">
                    <el-radio-button value="chat">对话</el-radio-button>
                    <el-radio-button value="adjust">调整正文</el-radio-button>
                  </el-radio-group>
                  <div class="ai-chat-more">
                    <el-button
                      class="ai-chat-more-btn"
                      size="small"
                      title="更多操作"
                      aria-label="更多操作"
                      @click.stop="chatMoreOpen = !chatMoreOpen"
                    >
                      <GameIcon name="more" :size="18" />
                    </el-button>
                    <div v-if="chatMoreOpen" class="ai-chat-more-menu">
                      <button
                        type="button"
                        @click="chatMoreOpen = false; saveChatAsKnowledge()"
                      >
                        保存对话为资料
                      </button>
                      <button
                        type="button"
                        @click="chatMoreOpen = false; clearProjectChat()"
                      >
                        清空对话
                      </button>
                      <button
                        type="button"
                        @click="chatMoreOpen = false; toggleAiPanel()"
                      >
                        AI 设置
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div
                v-if="selectedKnowledgeNodes.length > 0 || pendingIssueCount > 0"
                class="ai-chat-context"
              >
                <button
                  v-for="node in selectedKnowledgeNodes"
                  :key="recordId(node)"
                  type="button"
                  class="reference-chip"
                  @click="removeKnowledgeReference(node)"
                >
                  {{ recordTitle(node) }}
                  <span>x</span>
                </button>
                <span v-if="pendingIssueCount > 0" class="pending-count-chip">
                  待处理 {{ pendingIssueCount }}
                </span>
              </div>

              <div ref="chatThreadRef" class="chat-thread ai-chat-thread" role="log" aria-live="polite">
                <div v-if="activeProject.chat.length === 0 && !chatThinking" class="chat-welcome">
                  <img class="chat-welcome-mark" :src="rhineLoreMark" alt="" />
                  <span>开始一段创作对话</span>
                  <strong>先说说你想写什么</strong>
                  <p>续写、讨论、修订、导入——都可以直接说，或点下方快捷提示。</p>
                  <div class="chat-welcome-actions">
                    <button
                      v-for="starter in promptStarters.slice(0, 3)"
                      :key="starter"
                      type="button"
                      @click="usePromptStarter(starter)"
                    >
                      {{ starter }}
                    </button>
                  </div>
                </div>
                <article
                  v-for="message in activeProject.chat"
                  :key="message.id"
                  class="chat-message"
                  :class="[message.role, {'source-highlight': highlightedKnowledgeMessageId === message.id}]"
                  :data-message-id="message.id"
                >
                  <img
                    v-if="message.role === 'assistant'"
                    class="chat-avatar assistant"
                    :src="rhineLoreMark"
                    alt="Rhine-Lore"
                  />
                  <span v-else class="chat-avatar user">我</span>
                  <div class="chat-bubble">
                    <div class="chat-message-head">
                      <small>{{ chatTime(message.created_at) }}</small>
                    </div>
                    <p>{{ message.content }}</p>
                    <div
                      v-if="message.actions && message.actions.length > 0"
                      class="chat-tool-actions"
                    >
                      <span
                        v-for="(action, index) in message.actions"
                        :key="index"
                        class="chat-tool-chip"
                      >
                        ✓ {{ toolActionLabel(action.tool) }}
                      </span>
                    </div>
                    <div class="chat-message-actions">
                      <el-button size="small" text @click="copyChatText(message.content)">
                        复制
                      </el-button>
                      <el-button size="small" text @click="saveMessageAsKnowledge(message)">
                        保存为资料
                      </el-button>
                      <el-button
                        v-if="message.role === 'assistant'"
                        size="small"
                        text
                        @click="insertMessageIntoChapter(message)"
                      >
                        插入正文
                      </el-button>
                    </div>
                  </div>
                </article>
                <div v-if="chatThinking" class="chat-message assistant">
                  <img class="chat-avatar assistant" :src="rhineLoreMark" alt="Rhine-Lore" />
                  <div class="chat-bubble chat-thinking" :class="{streaming: streamingChatText}">
                    <template v-if="streamingChatText">
                      <p class="streaming-text">{{ streamingChatText }}<span class="stream-cursor" /></p>
                    </template>
                    <template v-else>
                      <span class="thinking-dot" />
                      <span class="thinking-dot" />
                      <span class="thinking-dot" />
                    </template>
                  </div>
                </div>
              </div>

              <div class="ai-chat-composer">
                <div v-if="pendingAgentAction" class="agent-confirm-card">
                  <div class="agent-confirm-head">
                    <strong>AI 建议：{{ toolActionLabel(pendingAgentAction.tool) }}</strong>
                    <span>待确认</span>
                  </div>
                  <div v-if="pendingAgentAction.tool === 'add_character'" class="agent-character-preview">
                    <div class="agent-character-name">
                      {{ String(pendingAgentAction.args.name || "未命名角色") }}
                    </div>
                    <div class="agent-character-meta">
                      <span v-if="pendingAgentAction.args.role">
                        角色：{{ pendingAgentAction.args.role }}
                      </span>
                      <span v-if="pendingAgentAction.args.identity">
                        身份：{{ pendingAgentAction.args.identity }}
                      </span>
                      <span v-if="pendingAgentAction.args.stance">
                        立场：{{ pendingAgentAction.args.stance }}
                      </span>
                    </div>
                    <dl>
                      <template v-if="pendingAgentAction.args.drive">
                        <dt>欲望</dt>
                        <dd>{{ pendingAgentAction.args.drive }}</dd>
                      </template>
                      <template v-if="pendingAgentAction.args.fear">
                        <dt>恐惧</dt>
                        <dd>{{ pendingAgentAction.args.fear }}</dd>
                      </template>
                      <template v-if="pendingAgentAction.args.traits">
                        <dt>特质</dt>
                        <dd>{{ pendingAgentAction.args.traits }}</dd>
                      </template>
                      <template v-if="pendingAgentAction.args.background">
                        <dt>背景</dt>
                        <dd>{{ pendingAgentAction.args.background }}</dd>
                      </template>
                      <template v-if="pendingAgentAction.args.secret">
                        <dt>秘密</dt>
                        <dd>{{ pendingAgentAction.args.secret }}</dd>
                      </template>
                    </dl>
                  </div>
                  <pre v-else class="agent-json-preview">
                    {{ JSON.stringify(pendingAgentAction.args, null, 2) }}
                  </pre>
                  <div
                    v-if="agentImpactPreview"
                    class="agent-impact"
                    :class="{'danger': agentImpactDanger}"
                  >
                    <div class="agent-impact-head">
                      <strong>执行影响</strong>
                      <span>{{ agentImpactPreview.label }}</span>
                    </div>
                    <ul>
                      <li v-for="(line, index) in agentImpactPreview.lines" :key="index">
                        {{ line }}
                      </li>
                    </ul>
                  </div>
                  <div class="agent-confirm-actions">
                    <el-button size="small" type="primary" @click="confirmAgentAction">
                      确认执行
                    </el-button>
                    <el-button size="small" @click="adjustAgentAction">让 AI 调整</el-button>
                    <el-button size="small" text @click="discardAgentAction">取消</el-button>
                  </div>
                </div>
                <div v-if="chatMode === 'chat'" class="chat-composer ai-composer">
                  <div class="chat-composer-main">
                    <div v-if="chatAttachment" class="chat-attachment-chip">
                      <span>{{ chatAttachment.name }}</span>
                      <button type="button" title="移除附件" aria-label="移除附件" @click="removeChatAttachment">
                        <GameIcon name="close" :size="14" />
                      </button>
                    </div>
                    <el-input
                      v-model="chatInput"
                      type="textarea"
                      :rows="1"
                      :autosize="{minRows: 1, maxRows: 6}"
                      placeholder="输入消息（Enter 发送，Shift+Enter 换行）"
                      @keydown="handleChatKeydown"
                    />
                  </div>
                  <div class="chat-send-column">
                    <el-button
                      type="primary"
                      :loading="busyAction === '对话创作'"
                      @click="sendCreativeMessage"
                    >
                      <GameIcon name="send" :size="16" />
                      发送
                    </el-button>
                    <el-button
                      title="附加文件（TXT / 项目 JSON）"
                      aria-label="附加文件"
                      @click="chatAttachInput?.click()"
                    >
                      <GameIcon name="attachment" :size="16" />
                    </el-button>
                  </div>
                  <div v-if="activeProject.chat.length > 0" class="chat-starter-row">
                    <el-button
                      v-for="starter in promptStarters"
                      :key="starter"
                      size="small"
                      text
                      @click="usePromptStarter(starter)"
                    >
                      {{ starter }}
                    </el-button>
                  </div>
                </div>
                <div v-else class="chat-composer adjust-composer">
                  <el-input
                    v-model="adjustInput"
                    type="textarea"
                    :rows="3"
                    placeholder="描述要调整的内容，例如：把林薇改成从小认识陈栩，并检查整体影响"
                    @keydown.ctrl.enter.prevent="generateRevision"
                  />
                  <el-button
                    type="primary"
                    :loading="revisionBusy || busyAction === '生成修订与评估'"
                    :disabled="!llmConfigured"
                    @click="generateRevision"
                  >
                    生成修订 + 评估
                  </el-button>
                  <small v-if="!llmConfigured">需要先配置 AI 通道</small>
                </div>
              </div>
              <div v-if="revisionPreview" class="revision-panel">
                <div class="revision-head">
                  <strong>修订预览与整体评估</strong>
                  <el-space wrap>
                    <el-button size="small" type="primary" @click="applyRevision">应用修订</el-button>
                    <el-button size="small" @click="discardRevision">放弃</el-button>
                  </el-space>
                </div>
                <div v-for="(revision, index) in revisionPreview.revisions" :key="index" class="revision-block">
                  <strong>{{ revision.chapter_title || "章节" }}</strong>
                  <div class="revision-compare">
                    <div>
                      <label>原文</label>
                      <p>{{ preview(revisionOriginalText(revision), 240) || "（空）" }}</p>
                    </div>
                    <div>
                      <label>修订后</label>
                      <p>{{ preview(revision.revised_text, 240) }}</p>
                    </div>
                  </div>
                </div>
                <div v-if="revisionPreview.evaluation.length > 0" class="evaluation-block">
                  <strong>整体影响评估（{{ revisionPreview.evaluation.length }} 项）</strong>
                  <div
                    v-for="issue in revisionPreview.evaluation"
                    :key="issue.id"
                    class="issue-row"
                    :class="`kind-${issue.kind}`"
                  >
                    <span class="issue-kind">{{ issue.kind }}</span>
                    <div>
                      <strong>{{ issue.item }}</strong>
                      <small v-if="issue.reason">依据：{{ issue.reason }}</small>
                      <small v-if="issue.suggestion">建议：{{ issue.suggestion }}</small>
                    </div>
                  </div>
                </div>
                <p v-else class="evaluation-ok">评估通过：未发现冲突、误区或不一致。</p>
              </div>
            </el-card>

            <div v-if="chatSidebarOpen" class="chat-sidebar-backdrop" @click="chatSidebarOpen = false" />

            <el-card shadow="never" class="chat-side-card">
              <template #header>
                <div class="card-header">
                  <span>创作上下文</span>
                  <el-space wrap>
                    <el-button size="small" @click="refreshChatReferences">刷新资料</el-button>
                    <el-button
                      class="chat-sidebar-close mobile-only"
                      size="small"
                      text
                      title="关闭上下文"
                      aria-label="关闭上下文"
                      @click="chatSidebarOpen = false"
                    >
                      <GameIcon name="close" :size="18" />
                    </el-button>
                  </el-space>
                </div>
              </template>

              <div class="chat-side-section">
                <button
                  type="button"
                  class="chat-side-section-head"
                  @click="chatSideSections.chapter = !chatSideSections.chapter"
                >
                  <strong>当前章节</strong>
                  <span>{{ chatSideSections.chapter ? "−" : "+" }}</span>
                </button>
                <div v-show="chatSideSections.chapter" class="chat-side-section-body">
                  <div v-if="!activeChapter" class="product-empty-state compact">
                    <strong>还没有章节</strong>
                    <p>创建第一章后，就可以在右侧开始对话或写正文。</p>
                    <el-button type="primary" @click="startWriting">创建第一章</el-button>
                  </div>
                  <template v-else>
                    <strong class="side-chapter-title">{{ activeChapter.title }}</strong>
                    <p class="side-chapter-preview">{{ preview(activeChapter.content, 520) }}</p>
                    <el-space wrap>
                      <el-button size="small" @click="activity = 'novel'">打开正文</el-button>
                      <el-button size="small" @click="addChapter">新章节</el-button>
                      <el-button size="small" @click="loadChapterContext">查资料</el-button>
                      <el-button
                        size="small"
                        :disabled="!activeChapter.content.trim()"
                        @click="submitChapterExtract"
                      >
                        本章存为资料
                      </el-button>
                    </el-space>
                  </template>
                </div>
              </div>

              <div class="chat-side-section">
                <button
                  type="button"
                  class="chat-side-section-head"
                  @click="chatSideSections.refs = !chatSideSections.refs"
                >
                  <strong>写作参考</strong>
                  <span>{{ chatSideSections.refs ? "−" : "+" }}</span>
                </button>
                <div v-show="chatSideSections.refs" class="chat-side-section-body">
                  <div class="reference-picker">
                    <div class="reference-picker-head">
                      <strong>已选择</strong>
                      <span>{{ selectedKnowledgeNodes.length }} / 6</span>
                    </div>
                    <el-empty v-if="chatReferenceNodes.length === 0" description="暂无已入库资料" />
                    <button
                      v-for="node in chatReferenceNodes"
                      :key="recordId(node)"
                      type="button"
                      class="reference-item"
                      :class="{active: isKnowledgeSelected(node)}"
                      @click="toggleKnowledgeReference(node)"
                    >
                      <strong>{{ recordTitle(node) }}</strong>
                      <span>{{ recordPreview(node, 92) }}</span>
                    </button>
                    <el-button size="small" @click="activity = 'context'">去资料库管理</el-button>
                  </div>
                </div>
              </div>

              <div class="chat-side-section">
                <button
                  type="button"
                  class="chat-side-section-head"
                  @click="chatSideSections.issues = !chatSideSections.issues"
                >
                  <strong>待处理项</strong>
                  <span>{{ chatSideSections.issues ? "−" : "+" }}</span>
                </button>
                <div v-show="chatSideSections.issues" class="chat-side-section-body">
                  <div class="pending-issues-panel">
                    <div v-if="pendingIssueCount === 0" class="product-empty-state compact">
                      没有待处理项
                    </div>
                    <div
                      v-for="issue in activeProject.issues.filter((item) => item.status === '待处理')"
                      :key="issue.id"
                      class="issue-row"
                      :class="`kind-${issue.kind}`"
                    >
                      <span class="issue-kind">{{ issue.kind }}</span>
                      <div>
                        <strong>{{ issue.item }}</strong>
                        <small v-if="issue.reason">依据：{{ issue.reason }}</small>
                        <small v-if="issue.suggestion">建议：{{ issue.suggestion }}</small>
                      </div>
                      <el-space wrap class="issue-actions">
                        <el-button size="small" @click="setIssueStatus(issue, '已处理')">
                          已处理
                        </el-button>
                        <el-button size="small" @click="setIssueStatus(issue, '忽略')">忽略</el-button>
                        <el-button size="small" type="danger" plain @click="removeIssue(issue)">
                          删除
                        </el-button>
                      </el-space>
                    </div>
                  </div>
                </div>
              </div>
            </el-card>
          </section>

          <section
            v-else-if="activity === 'novel'"
            class="activity-panel novel-panel"
            :class="{'novel-immersive': readerMode === 'read' && activeChapter}"
          >
            <el-card shadow="never" class="novel-index-card">
              <template #header>
                <div class="card-header">
                  <span>章节</span>
                  <el-button size="small" @click="addChapter">添加</el-button>
                </div>
              </template>
              <div class="novel-chapter-list">
                <el-button
                  v-for="chapter in activeProject.chapters"
                  :key="chapter.id"
                  :type="activeChapter?.id === chapter.id ? 'primary' : 'default'"
                  @click="selectChapter(chapter.id)"
                >
                  <span class="chapter-tab-content">
                    <strong>{{ chapter.title }}</strong>
                    <small>{{ chapterLength(chapter) }} 字</small>
                  </span>
                </el-button>
                <div v-if="activeProject.chapters.length === 0" class="product-empty-state compact">
                  <strong>从第一章开始</strong>
                  <el-button type="primary" @click="startWriting">创建并编辑</el-button>
                </div>
              </div>
            </el-card>

            <el-card
              shadow="never"
              class="novel-reader-card"
              :class="{'immersive': readerMode === 'read' && activeChapter}"
            >
              <template #header>
                <div class="card-header">
                  <span>正文</span>
                  <el-space wrap>
                    <el-button size="small" @click="openNovelVersions">版本</el-button>
                    <el-button size="small" @click="openReaderNavigator('toc')">目录</el-button>
                    <el-button size="small" @click="readerSettingsVisible = true">阅读设置</el-button>
                    <el-button :type="readerMode === 'read' ? 'primary' : 'default'" @click="enterReaderMode">
                      阅读
                    </el-button>
                    <el-button :type="readerMode === 'edit' ? 'primary' : 'default'" @click="exitReaderMode">
                      编辑
                    </el-button>
                    <el-button v-if="activeChapter && readerMode === 'edit'" @click="openProjectBranchFromCursor">
                      <GameIcon name="git-merge" :size="15" />
                      从光标分支
                    </el-button>
                    <el-button class="desktop-only-control" @click="submitChapterExtract">
                      保存为资料
                    </el-button>
                  </el-space>
                </div>
              </template>

              <div
                v-if="readerMode === 'read' && activeChapter"
                class="reading-progress"
              >
                <i :style="{width: `${readingProgress}%`}" />
              </div>

              <div v-if="readerMode === 'read' && activeChapter" class="reader-tap-zones">
                <button
                  type="button"
                  class="reader-tap-zone left"
                  :disabled="activeChapterIndex <= 0"
                  aria-label="上一章"
                  @click="readerPagePrev"
                />
                <button
                  type="button"
                  class="reader-tap-zone right"
                  :disabled="activeChapterIndex >= activeProject.chapters.length - 1"
                  aria-label="下一章"
                  @click="readerPageNext"
                />
              </div>

              <EmptyState
                v-if="!activeChapter"
                class="reader-empty-state"
                icon="pen"
                title="正文还没有开始"
                description="正文是作品本身：我们会自动创建“第一章”，也可以先去 AI 对话找灵感。"
              >
                <el-button type="primary" @click="startWriting">创建第一章</el-button>
                <el-button @click="activity = 'chat'">先聊聊想法</el-button>
              </EmptyState>
              <div v-else class="novel-reader-shell">
                <div v-if="saveNotice" class="save-notice">{{ saveNotice }}</div>
                <div class="reader-meta-band">
                  <span>{{ activeProject.name }}</span>
                  <strong>{{ chapterNavigationLabel }}</strong>
                  <span>{{ chapterCharacterCount }} 字</span>
                </div>
                <el-input v-model="activeChapter.title" class="novel-title-input" @input="saveProjects" />
                <div
                  v-if="readerMode === 'read'"
                  class="novel-reader"
                  :class="[readerThemeClass(), {'reader-paged': readerPageMode === 'page'}]"
                  :style="readerContentStyle()"
                  @mouseup="captureBranchSelection"
                  @touchend="captureBranchSelection"
                >
                  <template v-if="readerPageMode === 'page'">
                    <div
                      ref="readerPageAreaRef"
                      class="reader-page-area"
                      :class="{'is-title-page': currentReaderPageIsTitle()}"
                    >
                      <section
                        v-if="currentReaderPageIsTitle()"
                        class="reader-title-page"
                        :class="{'is-volume': readerCurrentTitleIsVolume}"
                      >
                        <p class="reader-title-page-work">{{ activeProject.name }}</p>
                        <h2>{{ activeChapter.title }}</h2>
                        <p class="reader-title-page-meta">{{ readerTitlePageMeta }}</p>
                      </section>
                      <template v-else>
                        <p
                          v-for="(paragraph, index) in currentReaderPage()"
                          :key="`${readerPageIndex}-${index}`"
                          :class="{'reader-paragraph-continuation': paragraph.continuation}"
                        >
                          {{ paragraph.text }}
                        </p>
                      </template>
                    </div>
                    <div class="reader-page-meta">{{ readerPageIndex + 1 }} / {{ Math.max(1, readerPages.length) }} 页</div>
                  </template>
                  <template v-else>
                    <h2>{{ activeChapter.title }}</h2>
                    <p v-for="(paragraph, index) in activeChapterParagraphs" :key="index">
                      {{ paragraph }}
                    </p>
                    <p v-if="activeChapterParagraphs.length === 0" class="empty-paragraph">这一章还没有正文。</p>
                  </template>
                </div>
                <el-input
                  v-else
                  v-model="activeChapter.content"
                  class="novel-editor"
                  type="textarea"
                  :rows="24"
                  placeholder="从这一章开始写。你也可以先去 AI 对话梳理情节，再插入正文。"
                  @input="saveProjects"
                />
              </div>

              <div
                v-if="readerMode === 'read' && activeChapter"
                class="immersive-toolbar"
              >
                <el-button size="small" @click="openReaderNavigator('toc')">目录</el-button>
                <el-button size="small" @click="readerSettingsVisible = true">阅读设置</el-button>
                <el-button size="small" @click="openReaderBranch">
                  <GameIcon name="git-merge" :size="15" />
                  分支续写
                </el-button>
                <template v-if="readerPageMode === 'page'">
                  <el-button size="small" :disabled="readerPageIndex <= 0" @click="readerPagePrev">
                    上一页
                  </el-button>
                  <span class="immersive-chapter">
                    {{ readerPageIndex + 1 }} / {{ Math.max(1, readerPages.length) }} 页
                  </span>
                  <el-button size="small" :disabled="readerPageIndex >= readerPages.length - 1" @click="readerPageNext">
                    下一页
                  </el-button>
                </template>
                <el-button
                  size="small"
                  :disabled="activeChapterIndex <= 0"
                  @click="openAdjacentChapter(-1)"
                >
                  上一章
                </el-button>
                <span class="immersive-chapter">{{ chapterNavigationLabel }}</span>
                <el-button
                  size="small"
                  :disabled="activeChapterIndex >= activeProject.chapters.length - 1"
                  @click="openAdjacentChapter(1)"
                >
                  下一章
                </el-button>
                <el-button size="small" type="primary" @click="exitReaderMode">编辑</el-button>
              </div>
            </el-card>

            <div v-if="activeChapter && readerMode !== 'read'" class="mobile-chapter-bar">
              <el-button
                size="small"
                :disabled="activeChapterIndex <= 0"
                @click="openAdjacentChapter(-1)"
              >
                上一章
              </el-button>
              <span>{{ chapterNavigationLabel }}</span>
              <el-button
                size="small"
                :disabled="activeChapterIndex >= activeProject.chapters.length - 1"
                @click="openAdjacentChapter(1)"
              >
                下一章
              </el-button>
            </div>

            <el-drawer v-model="novelVersionsVisible" title="版本历史" direction="rtl" size="min(420px, 92vw)">
              <div class="version-panel">
                <div class="version-commit-row">
                  <el-input
                    v-model="novelVersionMessage"
                    placeholder="提交说明，例如：完成第二章初稿"
                    size="small"
                  />
                  <el-button
                    size="small"
                    type="primary"
                    :loading="versionBusy === '提交版本'"
                    @click="commitNovelVersion"
                  >
                    提交
                  </el-button>
                </div>
                <p class="version-hint">AI 写操作会自动备份；恢复前也会先备份当前状态。</p>
                <div class="version-list">
                  <div
                    v-for="record in novelVersions"
                    :key="record.snapshot_id"
                    class="version-item"
                  >
                    <div class="version-item-copy">
                      <strong>{{ record.message }}</strong>
                      <small>{{ record.created_at }} · {{ record.char_count.toLocaleString() }} 字</small>
                    </div>
                    <el-button
                      size="small"
                      :type="pendingRestoreVersion?.snapshot_id === record.snapshot_id ? 'danger' : 'default'"
                      @click="requestNovelRestore(record)"
                    >
                      {{ pendingRestoreVersion?.snapshot_id === record.snapshot_id ? "确认恢复" : "恢复" }}
                    </el-button>
                  </div>
                  <div v-if="novelVersions.length === 0" class="product-empty-state compact">
                    还没有版本记录
                  </div>
                </div>
              </div>
            </el-drawer>

          </section>

          <section v-else-if="activity === 'context'" class="activity-panel context-panel">
            <header class="knowledge-commandbar">
              <nav class="knowledge-page-tabs" aria-label="资料库视图">
                <button type="button" :class="{active: knowledgePageTab === 'review'}" @click="knowledgePageTab = 'review'">
                  <GameIcon name="check" :size="17" />
                  <span>审核队列</span>
                  <b v-if="knowledgeDraftItems.length + knowledgeReadyItems.length > 0">
                    {{ knowledgeDraftItems.length + knowledgeReadyItems.length }}
                  </b>
                </button>
                <button type="button" :class="{active: knowledgePageTab === 'library'}" @click="knowledgePageTab = 'library'">
                  <GameIcon name="database" :size="17" />
                  <span>已入库</span>
                </button>
                <button type="button" :class="{active: knowledgePageTab === 'tools'}" @click="knowledgePageTab = 'tools'">
                  <GameIcon name="edit" :size="17" />
                  <span>新增与查找</span>
                </button>
              </nav>
              <div class="knowledge-pipeline compact">
                <div v-for="stat in knowledgePipelineStats" :key="stat.label" class="stat-card" :class="stat.tone">
                  <b>{{ stat.value }}</b>
                  <span>{{ stat.label }}</span>
                </div>
              </div>
            </header>

            <section v-if="knowledgePageTab === 'review'" class="knowledge-page-view knowledge-review-workbench">
              <div class="knowledge-view-heading">
                <div>
                  <span class="section-icon"><GameIcon name="check" :size="18" /></span>
                  <div>
                    <h2>资料审核</h2>
                    <p>先整理内容和来源，再确认进入资料库。AI 提炼的结果不会自动成为事实。</p>
                  </div>
                </div>
                <el-button @click="refreshKnowledgeCenter">
                  <GameIcon name="search" :size="15" />
                  刷新
                </el-button>
              </div>

              <div class="knowledge-queue-tabs" role="tablist" aria-label="审核状态">
                <button type="button" role="tab" :aria-selected="knowledgeQueueTab === 'draft'" :class="{active: knowledgeQueueTab === 'draft'}" @click="knowledgeQueueTab = 'draft'">
                  待整理 <b>{{ knowledgeDraftItems.length }}</b>
                </button>
                <button type="button" role="tab" :aria-selected="knowledgeQueueTab === 'ready'" :class="{active: knowledgeQueueTab === 'ready'}" @click="knowledgeQueueTab = 'ready'">
                  待入库 <b>{{ knowledgeReadyItems.length }}</b>
                </button>
              </div>

              <template v-if="knowledgeQueueTab === 'draft'">
                <div v-if="knowledgeDraftItems.length > 0" class="knowledge-batchbar">
                  <el-button text @click="toggleAllKnowledgeDrafts">
                    {{ selectedKnowledgeDraftKeys.length === knowledgeDraftItems.length ? "取消全选" : "全选" }}
                  </el-button>
                  <span>已选择 {{ selectedKnowledgeDraftKeys.length }} 条</span>
                  <el-button type="primary" :disabled="selectedKnowledgeDraftKeys.length === 0" @click="stageSelectedKnowledgeDrafts">
                    批量送审
                    <GameIcon name="arrow-right" :size="15" />
                  </el-button>
                </div>
                <div v-if="knowledgeDraftItems.length > 0" class="knowledge-review-list">
                  <article v-for="item in knowledgeDraftItems" :key="item.key" class="knowledge-review-row" @click="openKnowledgeReview(item)">
                    <el-checkbox
                      :model-value="selectedKnowledgeDraftKeys.includes(item.key)"
                      :aria-label="`选择 ${item.title}`"
                      @click.stop
                      @change="toggleKnowledgeDraftSelection(item, $event)"
                    />
                    <span class="knowledge-row-icon"><GameIcon name="file-text" :size="18" /></span>
                    <div class="knowledge-row-copy">
                      <header>
                        <strong>{{ item.title }}</strong>
                        <span>{{ knowledgeTypeLabel(item.nodeType) }}</span>
                      </header>
                      <p>{{ preview(knowledgeEditableBody(item), 150) || "暂无内容" }}</p>
                      <footer>
                        <span>{{ knowledgeSourceSummary(item) }}</span>
                        <time>{{ formatKnowledgeDate(item.createdAt) }}</time>
                      </footer>
                    </div>
                    <div class="knowledge-row-actions">
                      <span v-if="knowledgeDuplicateCount(item) > 0" class="similarity-alert">
                        {{ knowledgeDuplicateCount(item) }} 条相似
                      </span>
                      <el-button size="small" @click.stop="openKnowledgeReview(item)">审核</el-button>
                    </div>
                  </article>
                </div>
                <EmptyState
                  v-else
                  icon="check"
                  title="没有待整理资料"
                  description="从对话提炼、保存章节或手动新增后，资料草稿会出现在这里。"
                  compact
                >
                  <el-button type="primary" @click="activity = 'chat'">去对话创作</el-button>
                  <el-button @click="knowledgePageTab = 'tools'">手动新增</el-button>
                </EmptyState>
              </template>

              <template v-else>
                <div v-if="knowledgeReadyItems.length > 0" class="knowledge-batchbar">
                  <el-button text @click="toggleAllKnowledgeReady">
                    {{ selectedKnowledgeReadyIds.length === knowledgeReadyItems.length ? "取消全选" : "全选" }}
                  </el-button>
                  <span>已选择 {{ selectedKnowledgeReadyIds.length }} 条</span>
                  <el-button type="primary" :disabled="selectedKnowledgeReadyIds.length === 0" @click="approveSelectedKnowledgeReady">
                    确认入库
                    <GameIcon name="check" :size="15" />
                  </el-button>
                </div>
                <div v-if="knowledgeReadyItems.length > 0" class="knowledge-review-list">
                  <article v-for="item in knowledgeReadyItems" :key="item.key" class="knowledge-review-row ready" @click="openKnowledgeReview(item)">
                    <el-checkbox
                      :model-value="Boolean(item.entryId && selectedKnowledgeReadyIds.includes(item.entryId))"
                      :aria-label="`选择 ${item.title}`"
                      @click.stop
                      @change="toggleKnowledgeReadySelection(item, $event)"
                    />
                    <span class="knowledge-row-icon"><GameIcon name="database" :size="18" /></span>
                    <div class="knowledge-row-copy">
                      <header>
                        <strong>{{ item.title }}</strong>
                        <span>{{ knowledgeTypeLabel(item.nodeType) }}</span>
                      </header>
                      <p>{{ preview(knowledgeEditableBody(item), 150) || "暂无内容" }}</p>
                      <footer>
                        <span>{{ knowledgeSourceSummary(item) }}</span>
                        <time>{{ formatKnowledgeDate(item.createdAt) }}</time>
                      </footer>
                    </div>
                    <div class="knowledge-row-actions">
                      <span v-if="knowledgeDuplicateCount(item) > 0" class="similarity-alert">
                        {{ knowledgeDuplicateCount(item) }} 条相似
                      </span>
                      <el-button size="small" @click.stop="openKnowledgeReview(item)">查看</el-button>
                    </div>
                  </article>
                </div>
                <EmptyState
                  v-else
                  icon="database"
                  title="没有待入库资料"
                  description="整理好的草稿送审后，会在这里等待最终确认。"
                  compact
                />
              </template>
            </section>

            <section v-else-if="knowledgePageTab === 'library'" class="knowledge-page-view">
              <div class="knowledge-view-heading">
                <div>
                  <span class="section-icon"><GameIcon name="database" :size="18" /></span>
                  <div>
                    <h2>已入库资料</h2>
                    <p>这里的内容可以加入对话参考。一次最多携带 6 条，避免上下文过载。</p>
                  </div>
                </div>
                <el-space wrap>
                  <el-button @click="refreshNodes">刷新</el-button>
                  <el-button type="primary" :disabled="selectedKnowledgeNodes.length === 0" @click="activity = 'chat'">
                    去对话使用 {{ selectedKnowledgeNodes.length > 0 ? `(${selectedKnowledgeNodes.length})` : "" }}
                  </el-button>
                </el-space>
              </div>
              <EmptyState
                v-if="nodes.length === 0"
                icon="database"
                title="还没有已入库资料"
                description="对话或正文可以保存为资料草稿，经过审核后会出现在这里。"
                compact
              >
                <el-button type="primary" @click="activity = 'chat'">去对话创作</el-button>
                <el-button @click="knowledgePageTab = 'tools'">手动新增</el-button>
              </EmptyState>
              <div v-else class="knowledge-library-grid">
                <article v-for="row in nodes" :key="recordId(row)" class="knowledge-library-row">
                  <span class="knowledge-row-icon"><GameIcon name="file-text" :size="18" /></span>
                  <div class="node-title-cell">
                    <strong>{{ recordTitle(row) }}</strong>
                    <span>{{ recordPreview(row, 150) }}</span>
                    <small>{{ knowledgeTypeLabel(String(row.node_type || 'Note')) }}</small>
                  </div>
                  <el-button size="small" :type="isKnowledgeSelected(row) ? 'primary' : 'default'" @click="toggleKnowledgeReference(row)">
                    {{ isKnowledgeSelected(row) ? "已选择" : "加入参考" }}
                  </el-button>
                </article>
              </div>
            </section>

            <section v-else class="knowledge-page-view knowledge-tools-view">
              <div class="knowledge-tool-panel">
                <div class="knowledge-view-heading compact">
                  <div>
                    <span class="section-icon"><GameIcon name="edit" :size="18" /></span>
                    <div><h2>新增资料草稿</h2><p>手动记录需要长期保持一致的设定和事实。</p></div>
                  </div>
                  <el-button size="small" :disabled="!activeChapter" @click="prefillKnowledgeFromChapter">取当前章节</el-button>
                </div>
                <el-form label-position="top">
                  <el-form-item label="标题">
                    <el-input v-model="manualKnowledgeTitle" placeholder="例如：城邦禁令、角色秘密、重要伏笔" />
                  </el-form-item>
                  <el-form-item label="内容">
                    <el-input v-model="manualKnowledgeContent" type="textarea" :rows="9" placeholder="写下需要被记住的设定、事实、约束或素材。" />
                  </el-form-item>
                  <el-form-item label="标签">
                    <el-input v-model="manualKnowledgeTags" placeholder="lore, character, chapter" />
                  </el-form-item>
                  <el-button type="primary" :loading="busyAction === '保存资料草稿'" @click="submitManualKnowledgeDraft">
                    保存为资料草稿
                  </el-button>
                </el-form>
              </div>
              <div class="knowledge-tool-panel">
                <div class="knowledge-view-heading compact">
                  <div>
                    <span class="section-icon"><GameIcon name="search" :size="18" /></span>
                    <div><h2>查找资料</h2><p>按问题检索已批准的资料，或生成一份设定文档。</p></div>
                  </div>
                </div>
                <el-form label-position="top">
                  <el-form-item label="想查什么">
                    <el-input v-model="contextQuery" type="textarea" :rows="9" />
                  </el-form-item>
                  <el-form-item label="最多显示几条">
                    <el-input-number v-model="resultLimit" :min="1" :max="30" />
                  </el-form-item>
                  <div class="knowledge-tool-actions">
                    <el-button type="primary" @click="buildContext"><GameIcon name="search" :size="15" />查找</el-button>
                    <el-button @click="generateStoryBible">生成设定文档</el-button>
                  </div>
                </el-form>
              </div>
            </section>
          </section>

          <section v-else-if="activity === 'evolution'" class="activity-panel evolution-panel">
            <el-card v-if="!evolutionState" shadow="never" class="evolution-start-card">
              <template #header>
                <div class="card-header">
                  <span>演化沙盘</span>
                  <small>让小说自己演下去</small>
                </div>
              </template>
              <div class="evolution-intro">
                <strong>规则很简单：</strong>
                <p>
                  引擎会按回合推进故事——角色会相遇、冲突、结盟、发现秘密，世界张力会起伏。分支时刻你可以亲自选择，也可以交给命运骰子。同一颗种子会得到同样的故事，每次演化都会自动保存在本地磁盘。
                </p>
              </div>
              <el-form label-position="top" class="evolution-setup-form">
                <div class="preset-chips evolution-start-presets">
                  <span class="preset-label">难度预设</span>
                  <button
                    v-for="preset in evolutionStartPresets"
                    :key="preset.label"
                    type="button"
                    class="preset-chip"
                    @click="applyEvolutionStartPreset(preset)"
                  >
                    {{ preset.label }}
                  </button>
                </div>
                <el-row :gutter="14">
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="种子（留空自动生成）">
                      <el-input v-model="evolutionSeedInput" placeholder="同一颗种子 = 同样的故事" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="混乱度">
                      <el-slider v-model="evolutionChaos" :min="0" :max="100" />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="14">
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="分支频率">
                      <el-slider v-model="evolutionBranchFrequency" :min="0" :max="100" />
                    </el-form-item>
                  </el-col>
                  <el-col :xs="24" :sm="12">
                    <el-form-item label="分支处理">
                      <el-switch v-model="evolutionAutoResolve" active-text="命运骰子自动决定" inactive-text="由我选择" />
                    </el-form-item>
                  </el-col>
                </el-row>
                <div class="evolution-cast-preview">
                  <strong>参演角色（{{ activeProject.characters.length }}）</strong>
                  <div class="evolution-cast-chips">
                    <span v-for="character in activeProject.characters" :key="character.id">
                      {{ character.name }}
                    </span>
                    <span v-if="activeProject.characters.length === 0">还没有角色，会自动生成一位“主人公”</span>
                  </div>
                  <small>世界观设定会作为初始地点与势力进入沙盘。</small>
                </div>
              </el-form>
              <el-space wrap>
                <el-button type="primary" :loading="busyAction === '开始演化'" @click="beginEvolution">
                  开始演化
                </el-button>
                <el-button @click="activity = 'characters'">先补角色</el-button>
              </el-space>
            </el-card>

            <template v-else>
              <el-card shadow="never" class="evolution-control-card">
                <template #header>
                  <div class="card-header">
                    <span>
                      演化控制台 · 第 {{ evolutionState.turn }} 回合
                      <small class="evolution-seed">种子 {{ evolutionState.seed }}</small>
                    </span>
                    <el-space wrap>
                      <el-radio-group v-model="evolutionTab" size="small">
                        <el-radio-button value="sandbox">沙盘</el-radio-button>
                        <el-radio-button value="novel">小说</el-radio-button>
                        <el-radio-button value="chat">对话</el-radio-button>
                      </el-radio-group>
                      <el-button
                        type="primary"
                        :disabled="!!evolutionPendingBranch"
                        @click="runEvolutionTurn()"
                      >
                        推进一回合
                      </el-button>
                      <el-switch
                        v-model="evolutionAutoPlay"
                        active-text="自动演化"
                        inactive-text="手动"
                        @change="toggleEvolutionAutoPlay"
                      />
                      <el-switch
                        v-model="aiAutoProse"
                        active-text="AI 扩写"
                        inactive-text="模板"
                        :disabled="!llmConfigured"
                        @change="toggleAiAutoProse"
                      />
                      <span v-if="aiGenerating" class="ai-generating-tag">AI 生成中…</span>
                      <el-select
                        v-if="evolutionAutoPlay"
                        v-model="evolutionSpeed"
                        size="small"
                        style="width: 110px"
                        @change="changeEvolutionSpeed"
                      >
                        <el-option :value="2" label="2 秒" />
                        <el-option :value="4" label="4 秒" />
                        <el-option :value="8" label="8 秒" />
                      </el-select>
                      <el-button size="small" @click="resetEvolution">重新开始</el-button>
                    </el-space>
                  </div>
                </template>
                <div class="evolution-stats">
                  <div v-for="stat in evolutionStats" :key="stat.label" class="stat-card" :class="stat.tone">
                    <b>{{ stat.value }}</b>
                    <span>{{ stat.label }}</span>
                  </div>
                </div>
                <div v-if="evolutionNeedsCharacter" class="needs-character-banner">
                  <div>
                    <strong>角色偏少，故事需要新面孔</strong>
                    <small>
                      建议加入一位「{{ evolutionView?.suggested_character?.role || "配角" }}」：
                      {{ evolutionView?.suggested_character?.drive || "寻找自己在故事中的位置" }}
                    </small>
                  </div>
                  <el-space wrap>
                    <el-button size="small" type="primary" @click="openEvolutionCharacterDialog">
                      添加角色
                    </el-button>
                    <el-button size="small" @click="dismissCharacterPrompt">稍后</el-button>
                  </el-space>
                </div>
                <div class="evolution-guidance-row">
                  <el-input
                    v-model="evolutionGuidance"
                    placeholder="引导方向：例如“让沈砚背叛林澈”“下一场戏发生在旧码头”"
                    clearable
                    @keydown.enter.prevent="saveEvolutionGuidance"
                  />
                  <el-button
                    size="small"
                    type="primary"
                    :loading="busyAction === '保存引导'"
                    @click="saveEvolutionGuidance"
                  >
                    保存引导
                  </el-button>
                  <el-button size="small" :disabled="!evolutionGuidance.trim()" @click="clearEvolutionGuidance">
                    清空
                  </el-button>
                  <small>会偏置下一回合的事件与角色，并进入 AI 正文；不清空则持续生效。</small>
                  <small v-if="activeProject.global_guidance">全局引导：{{ activeProject.global_guidance }}</small>
                  <div class="preset-chips">
                    <button
                      v-for="preset in guidancePresets"
                      :key="preset"
                      type="button"
                      class="preset-chip"
                      @click="applyGuidancePreset(preset)"
                    >
                      {{ preset }}
                    </button>
                  </div>
                </div>
                <div v-if="evolutionState.ending" class="evolution-ending">
                  <strong>尾声</strong>
                  <span>{{ evolutionState.ending }}</span>
                </div>
                <div v-if="evolutionPendingBranch" class="branch-banner">
                  <strong>{{ evolutionPendingBranch.question }}</strong>
                  <div class="branch-options">
                    <el-button
                      v-for="option in evolutionPendingBranch.options"
                      :key="option.id"
                      type="primary"
                      plain
                      @click="chooseBranch(option.id)"
                    >
                      {{ option.label }}
                    </el-button>
                    <el-button @click="fateDice">命运骰子</el-button>
                  </div>
                  <small v-if="evolutionPendingBranch.options[0]">
                    {{ evolutionPendingBranch.options[0].hint }}（选项提示）
                  </small>
                </div>
              </el-card>

              <div v-if="evolutionTab === 'sandbox'" class="evolution-sandbox-grid">
                <el-card shadow="never" class="evolution-timeline-card">
                  <template #header>
                    <div class="card-header">
                      <span>事件时间线</span>
                      <small>最新在上</small>
                    </div>
                  </template>
                  <div v-if="evolutionHistory.length === 0" class="product-empty-state compact">
                    还没有事件，按“推进一回合”开始。
                  </div>
                  <div v-for="event in visibleEvolutionHistory" :key="event.id" class="evolution-event">
                    <div class="evolution-event-head">
                      <span class="evolution-kind" :class="`kind-${event.kind}`">{{ event.kind }}</span>
                      <strong>{{ event.title }}</strong>
                      <small>第 {{ event.turn }} 回合</small>
                    </div>
                    <p>{{ event.summary }}</p>
                    <div v-if="event.chosen_option_label" class="evolution-choice-tag">
                      抉择：{{ event.chosen_option_label }}
                    </div>
                    <div class="evolution-event-effects">
                      <span v-if="event.effects.tension">
                        张力 {{ event.effects.tension > 0 ? '+' : '' }}{{ event.effects.tension }}
                      </span>
                      <span v-for="(targets, fromId) in event.effects.relations" :key="fromId">
                        {{ evolutionCastName(evolutionState, String(fromId)) }} ↔
                        {{ Object.keys(targets).map((id) => evolutionCastName(evolutionState, String(id))).join('、') }}
                      </span>
                    </div>
                  </div>
                  <el-button
                    v-if="evolutionHistory.length > evolutionTimelineLimit"
                    size="small"
                    class="load-more-events"
                    @click="loadMoreEvolutionEvents"
                  >
                    加载更早事件（{{ evolutionHistory.length - evolutionTimelineLimit }} 条）
                  </el-button>
                </el-card>

                <div class="evolution-side-stack">
                  <el-card shadow="never" class="evolution-state-card">
                    <template #header><span>状态面板</span></template>
                    <el-tabs v-model="evolutionStateTab" class="evolution-state-tabs">
                      <el-tab-pane label="故事弧线" name="arc">
                        <div class="arc-block">
                          <div class="arc-act">
                            <strong>{{ evolutionActName }}</strong>
                            <small>目标张力 {{ evolutionState.arc.tension_range[0] }} – {{ evolutionState.arc.tension_range[1] }}</small>
                          </div>
                          <div class="arc-ending">
                            <small>结局方向</small>
                            <span>{{ evolutionState.arc.ending_kind || "未定" }}</span>
                          </div>
                          <div class="arc-beats">
                            <div
                              v-for="beat in evolutionState.arc.beats"
                              :key="beat.id"
                              class="arc-beat"
                              :class="{done: beat.status === 'done'}"
                            >
                              <span>{{ beat.status === 'done' ? '✓' : '○' }}</span>
                              <div>
                                <strong>{{ beat.title }}</strong>
                                <small>第 {{ beat.due_turn }} 回合起</small>
                              </div>
                            </div>
                          </div>
                        </div>
                      </el-tab-pane>
                      <el-tab-pane label="世界状态" name="world">
                        <div class="world-state-block">
                          <div><strong>张力</strong><span>{{ evolutionState.world.tension }} / 100</span></div>
                          <div>
                            <strong>地点</strong>
                            <span>{{ evolutionState.world.locations.join('、') || '暂无' }}</span>
                          </div>
                          <div>
                            <strong>势力</strong>
                            <span>{{ evolutionState.world.factions.map((faction) => faction.name).join('、') || '暂无' }}</span>
                          </div>
                          <div>
                            <strong>已知事实</strong>
                            <span>{{ evolutionState.world.facts.join('；') || '暂无' }}</span>
                          </div>
                        </div>
                        <el-button size="small" class="world-edit-map-button" @click="activity = 'map'">
                          编辑地图
                        </el-button>
                      </el-tab-pane>
                      <el-tab-pane label="线索伏笔" name="threads">
                        <div v-if="evolutionThreads.length === 0" class="product-empty-state compact">
                          还没有线索。
                        </div>
                        <div v-for="thread in evolutionThreads" :key="thread.id" class="thread-row" :class="thread.status">
                          <span>{{ thread.status === 'resolved' ? '已回收' : thread.status === 'dormant' ? '潜伏' : '进行中' }}</span>
                          <strong>{{ thread.title }}</strong>
                          <small>{{ thread.kind }}<template v-if="thread.secret"> · {{ thread.secret }}</template></small>
                        </div>
                      </el-tab-pane>
                      <el-tab-pane label="角色状态" name="cast">
                        <div v-if="evolutionCast.length === 0" class="product-empty-state compact">
                          还没有角色。
                        </div>
                        <div v-for="member in evolutionCast" :key="member.id" class="cast-row" :class="{dead: !member.alive}">
                          <strong>{{ member.name }} <small>{{ member.role }}</small></strong>
                          <span v-if="member.identity">{{ member.identity }}</span>
                          <small v-if="member.location">所在地：{{ member.location }}</small>
                          <span>{{ member.drive }}</span>
                          <small>恐惧：{{ member.fear }}</small>
                          <div v-if="member.traits?.length" class="cast-trait-chips">
                            <span v-for="trait in member.traits" :key="trait">{{ trait }}</span>
                          </div>
                          <small>
                            关系：{{
                              Object.keys(member.relations)
                                .map((id) => `${evolutionCastName(evolutionState, String(id))} ${evolutionRelationLabel(member, String(id))}`)
                                .join('；') || '暂无'
                            }}
                          </small>
                        </div>
                      </el-tab-pane>
                    </el-tabs>
                  </el-card>
                </div>
              </div>

              <el-card v-else-if="evolutionTab === 'novel'" shadow="never" class="evolution-novel-card">
                <template #header>
                  <div class="card-header">
                    <span>演化小说 · {{ evolutionActiveChapter?.title || "暂无章节" }}</span>
                    <el-space wrap>
                      <el-select
                        v-model="evolutionViewpoint"
                        size="small"
                        style="width: 180px"
                        @change="switchEvolutionViewpoint"
                      >
                        <el-option
                          v-for="viewpoint in evolutionView?.viewpoints ?? []"
                          :key="viewpoint.id"
                          :label="`${viewpoint.name} 的视角`"
                          :value="viewpoint.id"
                        />
                      </el-select>
                      <el-select
                        v-model="activeProject.chapter_turns"
                        size="small"
                        style="width: 130px"
                        @change="setChapterTurns"
                      >
                        <el-option
                          v-for="size in chapterTurnsOptions"
                          :key="size"
                          :label="`单章 ${size} 回合`"
                          :value="size"
                        />
                      </el-select>
                      <el-input-number v-model="readerFontSize" :min="15" :max="26" size="small" />
                      <el-button size="small" type="primary" @click="acceptEvolutionIntoChapter">
                        接收进正文
                      </el-button>
                    </el-space>
                  </div>
                </template>
                <p class="limited-perspective-note">
                  你只能看到 {{ evolutionView?.novel.viewpoint_name || '主角' }} 亲眼所见或亲身经历的事。
                  沙盘里还有 <strong>{{ evolutionView?.novel.hidden_events ?? 0 }}</strong> 件未被看见的事件。
                </p>
                <div class="ai-prose-panel">
                  <div class="ai-prose-actions">
                    <el-button
                      size="small"
                      type="primary"
                      :loading="aiProseBusy || busyAction === 'AI 扩写'"
                      :disabled="!llmConfigured"
                      @click="generateEvolutionProse"
                    >
                      AI 扩写当前回合
                    </el-button>
                    <el-button size="small" :disabled="!aiProse.trim()" @click="appendAIProseToChapter">
                      追加进正文
                    </el-button>
                    <el-button size="small" :disabled="!aiProse" @click="aiProse = ''">清空</el-button>
                    <small>在设置 → 高级设置中配置模型；未配置时使用本地模板正文</small>
                  </div>
                  <el-input
                    v-if="aiProse"
                    v-model="aiProse"
                    type="textarea"
                    :rows="7"
                    class="ai-prose-editor"
                    placeholder="AI 生成的正文草稿，可在这里修改"
                  />
                </div>
                <template v-if="evolutionNovelChapters.length > 0">
                  <div class="evolution-chapter-strip">
                    <button
                      v-for="chapter in evolutionNovelChapters"
                      :key="chapter.index"
                      type="button"
                      class="evolution-chapter-chip"
                      :class="{active: evolutionActiveChapter?.index === chapter.index}"
                      @click="evolutionChapterIndex = chapter.index"
                    >
                      {{ chapter.title }}
                      <small>
                        {{
                          chapter.startTurn === chapter.endTurn
                            ? `第${chapter.startTurn}回合`
                            : `第${chapter.startTurn}–${chapter.endTurn}回合`
                        }}
                      </small>
                    </button>
                  </div>
                  <div class="evolution-chapter-reader" :style="{fontSize: `${readerFontSize}px`}">
                    <h2>{{ evolutionActiveChapter.title }}</h2>
                    <p class="evolution-chapter-meta">
                      {{
                        evolutionActiveChapter.startTurn === evolutionActiveChapter.endTurn
                          ? `第 ${evolutionActiveChapter.startTurn} 回合`
                          : `第 ${evolutionActiveChapter.startTurn}–${evolutionActiveChapter.endTurn} 回合`
                      }}
                      · {{ evolutionActiveChapter.actName }}
                    </p>
                    <p v-for="(paragraph, index) in evolutionActiveChapter.paragraphs" :key="index">
                      {{ paragraph }}
                    </p>
                    <div
                      v-if="evolutionActiveChapter.index === evolutionNovelChapters.length - 1 && evolutionState.ending"
                      class="novel-ending-block"
                    >
                      <strong>尾声</strong>
                      <p>{{ evolutionState.ending }}</p>
                    </div>
                    <div class="evolution-chapter-nav">
                      <el-button
                        size="small"
                        :disabled="evolutionChapterIndex <= 0"
                        @click="openEvolutionAdjacentChapter(-1)"
                      >
                        上一章
                      </el-button>
                      <el-button
                        size="small"
                        :disabled="evolutionChapterIndex >= evolutionNovelChapters.length - 1"
                        @click="openEvolutionAdjacentChapter(1)"
                      >
                        下一章
                      </el-button>
                    </div>
                    <div class="regenerate-chapter-bar">
                      <el-button
                        size="small"
                        :loading="chapterBusy"
                        :disabled="!llmConfigured"
                        @click="regenerateCurrentChapter"
                      >
                        重新生成本章
                      </el-button>
                      <small v-if="!llmConfigured">需要 AI 通道</small>
                    </div>
                    <div
                      v-if="evolutionActiveChapter.index === evolutionNovelChapters.length - 1"
                      class="next-chapter-panel"
                    >
                      <div class="next-chapter-copy">
                        <strong>生成下一章</strong>
                        <small>读完本章后点击生成；可以给下一章一个方向，留空则由故事自己延续。</small>
                      </div>
                      <el-input
                        v-model="chapterGuidanceInput"
                        placeholder="引导下一章，例如：让林薇在旧码头发现火光"
                        clearable
                      />
                      <el-button type="primary" :loading="chapterBusy" @click="generateNextChapter">
                        生成下一章
                      </el-button>
                    </div>
                  </div>
                </template>
                <p v-else class="empty-paragraph">还没有可读的章节，先推进一回合。</p>
              </el-card>

              <el-card v-else shadow="never" class="evolution-chat-card">
                <template #header>
                  <div class="card-header">
                    <span>与故事对话</span>
                    <el-button size="small" :disabled="evolutionChat.length === 0" @click="clearEvolutionChat">
                      清空
                    </el-button>
                  </div>
                </template>
                <div class="evolution-chat-thread">
                  <div v-if="evolutionChat.length === 0" class="product-empty-state compact">
                    <strong>像和导演助理聊天一样</strong>
                    <p>可以问局势、要建议、下指令（例如“总结现在的处境”“下一步制造一场冲突”）。</p>
                  </div>
                  <article v-for="message in evolutionChat" :key="message.id" class="chat-message" :class="message.role">
                    <div class="chat-message-head">
                      <strong>{{ message.role === "user" ? "我" : "导演助理" }}</strong>
                      <el-button
                        v-if="message.role === 'user'"
                        size="small"
                        @click="setEvolutionMessageAsGuidance(message)"
                      >
                        设为引导
                      </el-button>
                    </div>
                    <p>{{ message.content }}</p>
                  </article>
                  <div v-if="evolutionChatStreaming" class="chat-message assistant">
                    <div class="chat-message-head"><strong>导演助理</strong></div>
                    <p class="streaming-text">{{ evolutionChatStreaming }}<span class="stream-cursor" /></p>
                  </div>
                </div>
                <div class="prompt-starters evolution-chat-starters">
                  <el-button
                    v-for="starter in evolutionChatStarters"
                    :key="starter"
                    size="small"
                    @click="evolutionChatInput = starter"
                  >
                    {{ starter }}
                  </el-button>
                </div>
                <div class="chat-composer evolution-chat-composer">
                  <el-input
                    v-model="evolutionChatInput"
                    type="textarea"
                    :rows="3"
                    placeholder="问剧情、要建议、下指令……"
                    @keydown.ctrl.enter.prevent="sendEvolutionChatMessage"
                  />
                  <el-button
                    type="primary"
                    :loading="evolutionChatBusy"
                    :disabled="!llmConfigured"
                    @click="sendEvolutionChatMessage"
                  >
                    发送
                  </el-button>
                </div>
                <small v-if="!llmConfigured" class="chat-key-hint">需要先配置 AI 通道（首页或右上角）</small>
              </el-card>
            </template>
          </section>

          <section v-else-if="activity === 'read'" class="activity-panel reading-panel">
            <el-card v-if="!evolutionState" shadow="never" class="reading-empty-card">
              <template #header>
                <div class="card-header">
                  <span>小说阅读</span>
                  <small>由演化沙盘驱动的连载阅读</small>
                </div>
              </template>
              <div class="reading-empty">
                <strong>还没有演化存档</strong>
                <p>先去「演化沙盘」建立故事并推进几回合，这里就会像连载小说一样逐章呈现。</p>
                <el-button type="primary" @click="openActivity('evolution')">去演化沙盘</el-button>
              </div>
            </el-card>

            <template v-else>
              <div class="reading-toolbar">
                <div class="reading-toolbar-title">
                  <span class="section-icon"><GameIcon name="book-open" /></span>
                  <div>
                    <strong>演化小说</strong>
                    <small>{{ evolutionView?.novel.viewpoint_name || "主角" }} 的视角</small>
                  </div>
                </div>
                <div class="reading-toolbar-controls">
                  <el-button size="small" @click="openReaderNavigator('toc')">目录</el-button>
                  <el-button size="small" @click="openReaderNavigator('search')">搜索</el-button>
                  <el-button size="small" @click="readerSettingsVisible = true">排版</el-button>
                  <el-button size="small" type="primary" @click="enterReaderMode">沉浸阅读</el-button>
                  <el-select
                    v-model="evolutionViewpoint"
                    size="small"
                    class="reading-viewpoint desktop-only-control"
                    @change="switchEvolutionViewpoint"
                  >
                    <el-option
                      v-for="viewpoint in evolutionView?.viewpoints ?? []"
                      :key="viewpoint.id"
                      :label="`${viewpoint.name} 的视角`"
                      :value="viewpoint.id"
                    />
                  </el-select>
                  <el-select
                    v-model="activeProject.chapter_turns"
                    size="small"
                    class="reading-chapter-size desktop-only-control"
                    @change="setChapterTurns"
                  >
                    <el-option
                      v-for="size in chapterTurnsOptions"
                      :key="size"
                      :label="`单章 ${size} 回合`"
                      :value="size"
                    />
                  </el-select>
                  <el-input-number
                    v-model="readerFontSize"
                    :min="15"
                    :max="26"
                    size="small"
                    title="字号"
                    class="desktop-only-control"
                  />
                  <el-input-number
                    v-model="readerLineHeight"
                    :min="1.4"
                    :max="2.6"
                    :step="0.1"
                    size="small"
                    title="行距"
                    class="desktop-only-control"
                    @change="persistReaderSettings"
                  />
                  <el-select
                    v-model="readerTheme"
                    size="small"
                    style="width: 96px"
                    class="desktop-only-control"
                    @change="persistReaderSettings"
                  >
                    <el-option label="白" value="day" />
                    <el-option label="米黄" value="sepia" />
                    <el-option label="夜间" value="night" />
                  </el-select>
                  <el-button size="small" @click="openActivity('evolution')">演化沙盘</el-button>
                  <el-button
                    size="small"
                    type="primary"
                    class="desktop-only-control"
                    @click="acceptEvolutionIntoChapter"
                  >
                    接收进正文
                  </el-button>
                </div>
              </div>

              <p class="limited-perspective-note">
                你只能看到 {{ evolutionView?.novel.viewpoint_name || '主角' }} 亲眼所见或亲身经历的事。
                沙盘里还有 <strong>{{ evolutionView?.novel.hidden_events ?? 0 }}</strong> 件未被看见的事件。
              </p>

              <template v-if="evolutionNovelChapters.length > 0">
                <div class="evolution-chapter-strip">
                  <button
                    v-for="chapter in evolutionNovelChapters"
                    :key="chapter.index"
                    type="button"
                    class="evolution-chapter-chip"
                    :class="{active: evolutionActiveChapter?.index === chapter.index}"
                    @click="selectReadingChapter(chapter.index)"
                  >
                    {{ chapter.title }}
                    <small>
                      {{
                        chapter.startTurn === chapter.endTurn
                          ? `第${chapter.startTurn}回合`
                          : `第${chapter.startTurn}–${chapter.endTurn}回合`
                      }}
                    </small>
                  </button>
                </div>

                <div class="reading-stage">
                  <article
                    class="evolution-chapter-reader reading-main"
                    :class="readerThemeClass()"
                    :style="readerContentStyle()"
                  >
                    <div v-if="evolutionActiveChapter" class="reader-tap-zones">
                      <button
                        type="button"
                        class="reader-tap-zone left"
                        :disabled="evolutionChapterIndex <= 0"
                        aria-label="上一章"
                        @click="openEvolutionAdjacentChapter(-1)"
                      />
                      <button
                        type="button"
                        class="reader-tap-zone right"
                        :disabled="evolutionChapterIndex >= evolutionNovelChapters.length - 1"
                        aria-label="下一章"
                        @click="openEvolutionAdjacentChapter(1)"
                      />
                    </div>
                    <h2>{{ evolutionActiveChapter.title }}</h2>
                    <p class="evolution-chapter-meta">
                      {{
                        evolutionActiveChapter.startTurn === evolutionActiveChapter.endTurn
                          ? `第 ${evolutionActiveChapter.startTurn} 回合`
                          : `第 ${evolutionActiveChapter.startTurn}–${evolutionActiveChapter.endTurn} 回合`
                      }}
                      · {{ evolutionActiveChapter.actName }}
                    </p>
                    <p v-for="(paragraph, index) in evolutionActiveChapter.paragraphs" :key="index">
                      {{ paragraph }}
                    </p>
                    <div
                      v-if="evolutionActiveChapter.index === evolutionNovelChapters.length - 1 && evolutionState.ending"
                      class="novel-ending-block"
                    >
                      <strong>尾声</strong>
                      <p>{{ evolutionState.ending }}</p>
                    </div>
                    <div class="evolution-chapter-nav">
                      <el-button
                        size="small"
                        :disabled="evolutionChapterIndex <= 0"
                        @click="openEvolutionAdjacentChapter(-1)"
                      >
                        上一章
                      </el-button>
                      <el-button
                        size="small"
                        :disabled="evolutionChapterIndex >= evolutionNovelChapters.length - 1"
                        @click="openEvolutionAdjacentChapter(1)"
                      >
                        下一章
                      </el-button>
                    </div>
                    <div class="regenerate-chapter-bar">
                      <el-button
                        size="small"
                        :loading="chapterBusy"
                        :disabled="!llmConfigured"
                        @click="regenerateCurrentChapter"
                      >
                        重新生成本章
                      </el-button>
                      <small v-if="!llmConfigured">需要 AI 通道</small>
                    </div>
                    <div
                      v-if="evolutionActiveChapter.index === evolutionNovelChapters.length - 1"
                      class="next-chapter-panel"
                    >
                      <div class="next-chapter-copy">
                        <strong>生成下一章</strong>
                        <small>读完本章后点击生成；可以给下一章一个方向，留空则由故事自己延续。</small>
                      </div>
                      <el-input
                        v-model="chapterGuidanceInput"
                        placeholder="引导下一章，例如：让林薇在旧码头发现火光"
                        clearable
                      />
                      <el-button type="primary" :loading="chapterBusy" @click="generateNextChapter">
                        生成下一章
                      </el-button>
                    </div>
                  </article>
                </div>
              </template>
              <p v-else class="empty-paragraph reading-empty-hint">还没有可读的章节，先推进一回合。</p>
            </template>

          </section>

          <section v-else-if="activity === 'shelf'" class="activity-panel shelf-panel">
            <template v-if="!shelfBook">
              <div class="shelf-head">
                <div>
                  <strong>TXT 书库</strong>
                  <small>导入 TXT 长篇小说，逐章阅读，支持 AI 续写 / 改写 / 扩写</small>
                </div>
                <el-button type="primary" @click="shelfImportInput?.click()">导入 TXT</el-button>
              </div>
              <EmptyState
                v-if="shelfBooks.length === 0"
                icon="library"
                title="书架还是空的"
                description="把 TXT 长篇小说导入这里：自动拆章、按章加载，支持 AI 续写/改写/扩写与全书分析。"
              >
                <el-button type="primary" @click="shelfImportInput?.click()">选择 TXT 文件</el-button>
                <el-button @click="activity = 'chat'">去 AI 对话试试</el-button>
              </EmptyState>
              <div v-else class="shelf-grid">
                <el-card
                  v-for="book in shelfBooks"
                  :key="book.book_id"
                  shadow="never"
                  class="shelf-card"
                >
                  <template #header>
                    <div class="card-header">
                      <span>{{ book.name }}</span>
                      <small>{{ book.genre }}</small>
                    </div>
                  </template>
                  <div class="shelf-cover" :style="shelfCoverStyle(book)">
                    <span>{{ (book.name || "书").slice(0, 1) }}</span>
                  </div>
                  <p class="shelf-card-summary">{{ book.summary || "暂无简介" }}</p>
                  <div class="shelf-card-meta">
                    <span>{{ book.chapter_count }} 章</span>
                    <span>{{ book.total_chars.toLocaleString() }} 字</span>
                    <span v-if="book.source_encoding">{{ textEncodingLabel(book.source_encoding) }}</span>
                    <span>{{ book.updated_at }}</span>
                  </div>
                  <div class="shelf-card-actions">
                    <el-button type="primary" size="small" @click="openShelfBook(book.book_id)">
                      阅读
                    </el-button>
                    <el-button size="small" @click="removeShelfBook(book.book_id)">删除</el-button>
                  </div>
                </el-card>
              </div>
            </template>

            <template v-else>
              <div class="reading-toolbar shelf-toolbar">
                <div class="reading-toolbar-title">
                  <span class="section-icon"><GameIcon name="book-open" /></span>
                  <div>
                    <strong>{{ shelfBook.name }}</strong>
                    <small>
                      {{ shelfProgressLabel() }} ·
                      {{ (shelfChapter?.char_count ?? 0).toLocaleString() }} 字
                    </small>
                  </div>
                </div>
                <div class="reading-toolbar-controls">
                  <el-button
                    size="small"
                    @click="closeShelfBook"
                  >
                    返回书架
                  </el-button>
                  <el-button size="small" @click="openShelfVersions">版本</el-button>
                  <el-button size="small" @click="openReaderNavigator('toc')">目录</el-button>
                  <el-button size="small" @click="openReaderNavigator('search')">搜索</el-button>
                  <el-button size="small" @click="readerSettingsVisible = true">排版</el-button>
                  <el-button size="small" @click="openReaderBranch">
                    <GameIcon name="git-merge" :size="15" />
                    分支续写
                  </el-button>
                  <el-button size="small" @click="openShelfBranchTree">
                    <GameIcon name="route" :size="15" />
                    故事树<span v-if="shelfBranches.length"> · {{ shelfBranches.length }}</span>
                  </el-button>
                  <el-button size="small" :loading="branchProjectBusy" @click="materializeShelfProject()">
                    导入工作台
                  </el-button>
                  <el-button size="small" type="primary" @click="enterReaderMode">沉浸阅读</el-button>
                  <el-button
                    size="small"
                    :disabled="shelfChapterIndex <= 0"
                    @click="openShelfAdjacentChapter(-1)"
                  >
                    上一章
                  </el-button>
                  <el-button
                    size="small"
                    :disabled="shelfChapterIndex < 0 || shelfChapterIndex >= shelfBook.chapters.length - 1"
                    @click="openShelfAdjacentChapter(1)"
                  >
                    下一章
                  </el-button>
                </div>
              </div>

              <div v-if="!shelfChapter" class="product-empty-state">
                <strong>加载章节中</strong>
              </div>
              <template v-else>
                <article
                  class="novel-reader shelf-reader"
                  :class="readerThemeClass()"
                  :style="readerContentStyle()"
                  @mouseup="captureBranchSelection"
                  @touchend="captureBranchSelection"
                >
                  <div class="reader-tap-zones">
                    <button
                      type="button"
                      class="reader-tap-zone left"
                      :disabled="shelfChapterIndex <= 0"
                      aria-label="上一章"
                      @click="openShelfAdjacentChapter(-1)"
                    />
                    <button
                      type="button"
                      class="reader-tap-zone right"
                      :disabled="shelfChapterIndex < 0 || shelfChapterIndex >= shelfBook.chapters.length - 1"
                      aria-label="下一章"
                      @click="openShelfAdjacentChapter(1)"
                    />
                  </div>
                  <h2>{{ shelfChapter.title }}</h2>
                  <div
                    v-for="(paragraph, index) in shelfChapterParagraphs(shelfChapter)"
                    :key="index"
                    class="shelf-reader-paragraph"
                  >
                    <p>{{ paragraph }}</p>
                    <button
                      type="button"
                      class="shelf-branch-button"
                      title="从本段末尾分支续写"
                      :aria-label="`从第 ${index + 1} 段末尾分支续写`"
                      @click.stop="openShelfParagraphBranch(paragraph, index)"
                    >
                      <GameIcon name="git-merge" :size="16" />
                    </button>
                  </div>
                </article>

                <div class="shelf-ai-panel">
                  <section class="shelf-analysis-console">
                    <div class="shelf-analysis-toolbar">
                      <div class="shelf-analysis-title">
                        <span class="shelf-analysis-icon"><GameIcon name="database" :size="19" /></span>
                        <div>
                          <strong>全书档案</strong>
                          <small>
                            {{ shelfAnalysisStatus?.message || "逐章阅读正文，整理人物、时间线、设定与伏笔" }}
                          </small>
                        </div>
                      </div>
                      <div class="shelf-analysis-actions">
                        <el-button
                          v-if="shelfAnalysisRunning"
                          size="small"
                          @click="pauseShelfAnalysis"
                        >
                          暂停
                        </el-button>
                        <el-button
                          v-else
                          type="primary"
                          size="small"
                          :loading="shelfAnalyzeBusy"
                          @click="runShelfAnalysis"
                        >
                          {{ shelfAnalysisActionLabel }}
                        </el-button>
                        <el-button
                          class="shelf-analysis-settings-button"
                          size="small"
                          circle
                          :title="shelfAnalysisAdvanced ? '收起分析设置' : '分析设置'"
                          aria-label="分析设置"
                          @click="shelfAnalysisAdvanced = !shelfAnalysisAdvanced"
                        >
                          <GameIcon name="settings" :size="16" />
                        </el-button>
                      </div>
                    </div>

                    <div v-if="shelfAnalysisRunning || shelfAnalysisStatus?.can_resume" class="shelf-analysis-progress">
                      <el-progress
                        :percentage="shelfAnalysisStatus?.progress ?? 0"
                        :stroke-width="7"
                        :show-text="false"
                      />
                      <div>
                        <span>{{ shelfAnalysisStatus?.progress ?? 0 }}%</span>
                        <span v-if="shelfAnalysisStatus?.current_chapter">
                          {{ shelfAnalysisStatus.current_chapter }}
                        </span>
                        <span v-else-if="shelfAnalysisStatus?.cached_steps">
                          已复用 {{ shelfAnalysisStatus.cached_steps }} 个分析节点
                        </span>
                        <span v-if="shelfAnalysisStatus?.error" class="analysis-error">
                          {{ shelfAnalysisStatus.error }}
                        </span>
                      </div>
                    </div>

                    <div v-show="shelfAnalysisAdvanced" class="shelf-analysis-advanced">
                      <div class="shelf-analysis-mode-row">
                        <label>阅读深度</label>
                        <el-radio-group v-model="shelfAnalysisMode" size="small">
                          <el-radio-button value="quick">快速</el-radio-button>
                          <el-radio-button value="smart">智能</el-radio-button>
                          <el-radio-button value="deep">深读</el-radio-button>
                        </el-radio-group>
                      </div>
                      <p>
                        <template v-if="shelfAnalysisMode === 'quick'">适合先看全局轮廓，长片段合并阅读。</template>
                        <template v-else-if="shelfAnalysisMode === 'deep'">更细地阅读长章节，适合复杂群像和多线叙事。</template>
                        <template v-else>自动平衡细节、耗时与费用，适合大多数长篇。</template>
                      </p>
                      <div v-if="shelfAnalysisPlan" class="shelf-analysis-plan">
                        <span>{{ shelfAnalysisPlan.chapter_count }} 项正文</span>
                        <span>{{ shelfAnalysisPlan.total_chars.toLocaleString() }} 字</span>
                        <span>{{ shelfAnalysisPlan.fragment_count }} 个阅读片段</span>
                        <span>约 {{ shelfAnalysisPlan.estimated_requests }} 次分析</span>
                      </div>
                      <el-checkbox v-model="shelfAnalysisForce" :disabled="shelfAnalysisRunning">
                        忽略已有结果，从头重新分析
                      </el-checkbox>
                    </div>

                    <div v-if="shelfAnalysis" class="shelf-analysis">
                      <div v-if="shelfAnalysis.offline || shelfAnalysis.stale" class="shelf-analysis-notice">
                        <span v-if="shelfAnalysis.stale">正文已修改，更新档案时只会重读变化部分。</span>
                        <span v-else>当前是本地基础索引，连接 AI 后可获得完整时间线与伏笔追踪。</span>
                      </div>
                      <el-tabs v-model="shelfAnalysisTab" class="shelf-analysis-tabs">
                        <el-tab-pane label="总览" name="overview">
                          <div class="shelf-analysis-metrics">
                            <div><strong>{{ shelfAnalysis.characters.length }}</strong><span>角色</span></div>
                            <div><strong>{{ shelfAnalysis.settings.length }}</strong><span>设定</span></div>
                            <div><strong>{{ shelfAnalysis.timeline?.length ?? 0 }}</strong><span>事件</span></div>
                            <div><strong>{{ shelfAnalysis.unresolved_threads.length }}</strong><span>待回收</span></div>
                          </div>
                          <p v-if="shelfAnalysis.summary" class="shelf-analysis-summary">{{ shelfAnalysis.summary }}</p>
                          <div v-if="shelfAnalysis.key_facts.length" class="shelf-analysis-list">
                            <article v-for="(fact, index) in shelfAnalysis.key_facts.slice(0, 8)" :key="index">
                              <p>{{ fact.text }}</p>
                              <small>{{ analysisSourceLabel(fact.source_chapters) }}</small>
                            </article>
                          </div>
                        </el-tab-pane>
                        <el-tab-pane label="人物" name="characters">
                          <div class="shelf-analysis-entity-grid">
                            <article v-for="item in shelfAnalysis.characters" :key="item.name">
                              <div><strong>{{ item.name }}</strong><span>{{ item.role }}</span></div>
                              <p>{{ item.notes || "暂无补充说明" }}</p>
                              <small>{{ analysisSourceLabel(item.source_chapters) }}</small>
                            </article>
                          </div>
                        </el-tab-pane>
                        <el-tab-pane label="时间线" name="timeline">
                          <div class="shelf-analysis-timeline">
                            <article v-for="(item, index) in shelfAnalysis.timeline" :key="`${item.title}-${index}`">
                              <span>{{ analysisSourceLabel(item.source_chapters) }}</span>
                              <div><strong>{{ item.title }}</strong><p>{{ item.summary }}</p></div>
                            </article>
                            <p v-if="!shelfAnalysis.timeline?.length" class="shelf-analysis-empty">暂无时间线记录</p>
                          </div>
                        </el-tab-pane>
                        <el-tab-pane label="世界" name="world">
                          <div class="shelf-analysis-entity-grid">
                            <article v-for="item in shelfAnalysis.settings" :key="item.name">
                              <div><strong>{{ item.name }}</strong><span>{{ item.type }}</span></div>
                              <p>{{ item.notes || "暂无补充说明" }}</p>
                              <small>{{ analysisSourceLabel(item.source_chapters) }}</small>
                            </article>
                          </div>
                          <div v-if="shelfAnalysis.relations?.length" class="shelf-relation-list">
                            <span v-for="(item, index) in shelfAnalysis.relations.slice(0, 40)" :key="index">
                              {{ item.from }} · {{ item.relation }} · {{ item.to }}
                            </span>
                          </div>
                        </el-tab-pane>
                        <el-tab-pane label="伏笔" name="threads">
                          <div class="shelf-thread-columns">
                            <section>
                              <strong>待回收</strong>
                              <article v-for="(item, index) in shelfAnalysis.unresolved_threads" :key="index">
                                <p>{{ item.text }}</p><small>{{ analysisSourceLabel(item.source_chapters) }}</small>
                              </article>
                            </section>
                            <section>
                              <strong>已回收</strong>
                              <article v-for="(item, index) in shelfAnalysis.resolved_threads" :key="index">
                                <p>{{ item.text }}</p><small>{{ analysisSourceLabel(item.source_chapters) }}</small>
                              </article>
                            </section>
                          </div>
                        </el-tab-pane>
                      </el-tabs>
                    </div>
                  </section>

                  <section class="shelf-compose-section">
                    <div class="shelf-ai-head">
                      <strong>AI 创作</strong>
                      <el-radio-group v-model="shelfAiMode" size="small">
                        <el-radio-button value="continue">续写</el-radio-button>
                        <el-radio-button value="rewrite">改写</el-radio-button>
                        <el-radio-button value="expand">扩写</el-radio-button>
                      </el-radio-group>
                      <el-button type="primary" size="small" :loading="shelfAiBusy" @click="runShelfAiWrite">
                        生成
                      </el-button>
                    </div>
                    <el-input
                      v-model="shelfGuidance"
                      placeholder="引导 AI，例如：让主角发现旧码头火光，语气保持沉静"
                      clearable
                    />
                  </section>
                  <template v-if="shelfAiResult">
                    <el-input
                      v-model="shelfAiResult"
                      type="textarea"
                      :rows="8"
                      class="shelf-ai-result"
                      placeholder="AI 结果预览"
                    />
                    <div class="shelf-ai-actions">
                      <el-button type="primary" size="small" @click="applyShelfAiResult">
                        应用到本章
                      </el-button>
                      <el-button size="small" @click="shelfAiResult = ''">丢弃</el-button>
                    </div>
                  </template>
                  <div class="shelf-save-row">
                    <el-button size="small" :loading="shelfSaving" @click="saveShelfChapter">
                      保存本章
                    </el-button>
                    <small>AI 结果应用后需要保存才会写入磁盘。</small>
                  </div>
                  <button
                    v-if="shelfBranches.length"
                    type="button"
                    class="shelf-branch-tree-entry"
                    @click="openShelfBranchTree"
                  >
                    <span class="shelf-branch-tree-icon"><GameIcon name="route" :size="18" /></span>
                    <span>
                      <strong>查看本章故事树</strong>
                      <small>{{ shelfBranches.length }} 个故事节点 · {{ shelfBranchEndingCount }} 条开放结局</small>
                    </span>
                    <GameIcon name="chevron-right" :size="16" />
                  </button>
                </div>
              </template>

              <el-drawer
                v-model="shelfVersionsVisible"
                title="版本历史"
                direction="rtl"
                size="min(420px, 92vw)"
              >
                <div class="version-panel">
                  <div class="version-commit-row">
                    <el-input
                      v-model="shelfVersionMessage"
                      placeholder="提交说明，例如：校对前快照"
                      size="small"
                    />
                    <el-button
                      size="small"
                      type="primary"
                      :loading="versionBusy === '提交版本'"
                      @click="commitShelfVersion"
                    >
                      提交
                    </el-button>
                  </div>
                  <p class="version-hint">AI 写操作会自动备份；恢复前也会先备份当前状态。</p>
                  <div class="version-list">
                    <div
                      v-for="record in shelfVersions"
                      :key="record.snapshot_id"
                      class="version-item"
                    >
                      <div class="version-item-copy">
                        <strong>{{ record.message }}</strong>
                        <small>{{ record.created_at }} · {{ record.char_count.toLocaleString() }} 字</small>
                      </div>
                      <el-button
                        size="small"
                        :type="pendingRestoreVersion?.snapshot_id === record.snapshot_id ? 'danger' : 'default'"
                        @click="requestShelfRestore(record)"
                      >
                        {{ pendingRestoreVersion?.snapshot_id === record.snapshot_id ? "确认恢复" : "恢复" }}
                      </el-button>
                    </div>
                    <div v-if="shelfVersions.length === 0" class="product-empty-state compact">
                      还没有版本记录
                    </div>
                  </div>
                </div>
              </el-drawer>

            </template>
          </section>

          <section v-else-if="activity === 'settings'" class="activity-panel settings-panel">
            <el-tabs v-model="settingsTab" class="settings-tabs">
              <el-tab-pane label="常用设置" name="basic">
                <el-card shadow="never" class="feature-map-card">
                  <template #header>
                    <div class="card-header">
                      <span>功能地图</span>
                      <small>每个功能是干什么的，点一下直达</small>
                    </div>
                  </template>
                  <div class="feature-map-grid">
                    <button
                      v-for="item in activities"
                      :key="item.id"
                      type="button"
                      class="feature-map-item"
                      @click="activity = item.id"
                    >
                      <span class="feature-map-icon"><GameIcon :name="item.icon" :size="18" /></span>
                      <span class="feature-map-copy">
                        <strong>{{ item.label }}</strong>
                        <small>{{ item.description }}</small>
                      </span>
                      <i aria-hidden="true"><GameIcon name="chevron-right" :size="16" /></i>
                    </button>
                  </div>
                </el-card>
                <el-row :gutter="14">
                  <el-col :xs="24" :lg="12">
                    <el-card shadow="never">
                      <template #header>当前状态</template>
                      <el-descriptions :column="1" border>
                        <el-descriptions-item label="故事">{{ activeProject.name }}</el-descriptions-item>
                        <el-descriptions-item label="本地草稿">已保存到本机服务端 data/</el-descriptions-item>
                        <el-descriptions-item label="资料库">{{ selectedWorkspaceId }}</el-descriptions-item>
                        <el-descriptions-item label="状态">{{ notice }}</el-descriptions-item>
                        <el-descriptions-item label="局域网访问">
                          {{ lanInfo?.lan_urls?.[0] || "未检测到局域网地址" }}
                        </el-descriptions-item>
                      </el-descriptions>
                    </el-card>
                  </el-col>
                  <el-col :xs="24" :lg="12">
                    <el-card shadow="never">
                      <template #header>资料库连接</template>
                      <div class="vault-status-card">
                        <strong>{{ backendStatusLabel }} · {{ vaultModeLabel }}</strong>
                        <span>{{ vaultRuntimeLabel }}</span>
                        <small>{{ vaultStatus?.manager.base_url || 'http://127.0.0.1:8795' }}</small>
                        <small>{{ vaultWebLabel }}</small>
                        <el-space wrap class="vault-status-actions">
                          <el-button
                            type="primary"
                            :loading="busyAction === '启动默认资料库'"
                            @click="startDefaultVault"
                          >
                            启动默认资料库
                          </el-button>
                          <el-button @click="testBackend">检查连接</el-button>
                          <el-button :disabled="!vaultWebStatus?.installed && !vaultStatus?.connected" @click="openVaultWeb">
                            打开 Vault Web
                          </el-button>
                          <el-button @click="settingsTab = 'advanced'">部署 / 高级</el-button>
                        </el-space>
                      </div>
                    </el-card>
                  </el-col>
                </el-row>

                <el-card shadow="never" class="server-connect-card">
                  <template #header>
                    <div class="card-header">
                      <span>服务器连接</span>
                      <small>内置服务器仅本机可用；局域网模式让手机直接连电脑上的数据</small>
                    </div>
                  </template>
                  <div class="server-connect-grid">
                    <div class="vault-status-card">
                      <strong>当前模式：{{ serverBaseCurrent ? "局域网服务器" : "内置服务器（本机）" }}</strong>
                      <span>{{ serverBaseCurrent || "数据与本页面同机（Android 内嵌 / 本机 8786）" }}</span>
                      <small v-if="serverBaseMessage">{{ serverBaseMessage }}</small>
                    </div>
                    <el-form label-position="top" class="vault-deploy-form">
                      <el-form-item label="局域网服务器地址">
                        <el-input
                          v-model="serverBaseInput"
                          placeholder="http://192.168.2.18:8786"
                          @keydown.enter.prevent="applyServerBase"
                        />
                      </el-form-item>
                      <el-space wrap>
                        <el-button :loading="serverBaseBusy" @click="testServerBaseConnection">
                          测试连接
                        </el-button>
                        <el-button type="primary" :loading="serverBaseBusy" @click="applyServerBase">
                          应用并加载
                        </el-button>
                        <el-button :disabled="!serverBaseCurrent" @click="serverBaseInput = ''; applyServerBase()">
                          恢复内置
                        </el-button>
                      </el-space>
                      <small class="chat-key-hint">
                        手机与电脑需在同一网络；电脑端以 --host 0.0.0.0 启动，并放行 Windows 防火墙。
                      </small>
                    </el-form>
                  </div>
                </el-card>

                <el-card shadow="never" class="theme-card">
                  <template #header>
                    <div class="card-header">
                      <span>外观主题</span>
                      <small>浅色、深色或跟随系统</small>
                    </div>
                  </template>
                  <el-radio-group v-model="themeMode" @change="setThemeMode">
                    <el-radio-button value="light">浅色</el-radio-button>
                    <el-radio-button value="dark">深色</el-radio-button>
                    <el-radio-button value="system">跟随系统</el-radio-button>
                  </el-radio-group>
                  <small class="chat-key-hint">深色模式会同步应用到阅读页与全部卡片，随设置持久保存。</small>
                </el-card>

                <el-card shadow="never" class="backup-card">
                  <template #header>
                    <div class="card-header">
                      <span>备份与迁移</span>
                      <small>ZIP 一键打包项目、书与版本，导入后自动合并</small>
                    </div>
                  </template>
                  <div class="server-connect-grid">
                    <div class="vault-status-card">
                      <strong>数据备份</strong>
                      <span>包含：故事项目、演化存档、TXT 书库、版本历史</span>
                      <small>为保护密钥安全，AI 配置不随备份导出。</small>
                      <small v-if="backupMessage">{{ backupMessage }}</small>
                    </div>
                    <el-form label-position="top" class="vault-deploy-form">
                      <el-space wrap>
                        <el-button type="primary" :loading="backupBusy" @click="exportBackup">
                          导出 ZIP 备份
                        </el-button>
                        <el-button :loading="backupBusy" @click="backupImportInput?.click()">
                          导入 ZIP 备份
                        </el-button>
                        <input
                          ref="backupImportInput"
                          class="sr-only"
                          type="file"
                          accept=".zip,application/zip"
                          @change="handleBackupImport"
                        />
                      </el-space>
                      <small class="chat-key-hint">
                        导入会覆盖同名项目/书并保留新文件；建议导入前先导出当前数据。
                      </small>
                    </el-form>
                  </div>
                </el-card>
              </el-tab-pane>

              <el-tab-pane label="高级设置" name="advanced">
                <el-card shadow="never" class="vault-deploy-card">
                  <template #header>
                    <div class="card-header">
                      <span>Rhine-Vault</span>
                      <el-space wrap>
                        <el-button size="small" @click="refreshVaultRuntime">刷新状态</el-button>
                        <el-button size="small" @click="openVaultWeb">打开 Vault Web</el-button>
                      </el-space>
                    </div>
                  </template>
                  <div class="vault-deploy-grid">
                    <div class="vault-status-card">
                      <strong>{{ backendStatusLabel }} · {{ vaultModeLabel }}</strong>
                      <span>{{ vaultRuntimeLabel }}</span>
                      <small>{{ vaultStatus?.manager.base_url || 'http://127.0.0.1:8795' }}</small>
                      <small>默认路径：{{ vaultStatus?.config.vault_path || vaultPath }}</small>
                      <small>默认数据库：{{ vaultStatus?.config.database_path || vaultDatabasePath }}</small>
                      <small v-if="vaultStatus?.error">{{ vaultStatus.error }}</small>
                      <small v-if="vaultStatus?.manager.auto_start.error">
                        启动错误：{{ vaultStatus.manager.auto_start.error }}
                      </small>
                      <el-space wrap class="vault-status-actions">
                        <el-button
                          type="primary"
                          :loading="busyAction === '启动默认资料库'"
                          @click="startDefaultVault"
                        >
                          启动默认 Core
                        </el-button>
                        <el-button :disabled="!vaultStatus?.manager.running" @click="stopVault">停止 Core</el-button>
                      </el-space>
                    </div>
                    <div class="vault-setup-stack">
                      <div class="vault-web-card">
                        <div>
                          <strong>{{ vaultWebLabel }}</strong>
                          <small>{{ vaultWebStatus?.web_root || '等待检测 Vault Web' }}</small>
                        </div>
                        <el-space wrap>
                          <el-button
                            :disabled="!vaultWebStatus?.installable"
                            :loading="busyAction === '安装 Vault Web'"
                            @click="installVaultWebUI"
                          >
                            安装 Vault Web
                          </el-button>
                          <el-button :disabled="!vaultStatus?.connected" @click="openVaultWeb">
                            跳转
                          </el-button>
                        </el-space>
                        <small v-if="vaultWebStatus?.error">{{ vaultWebStatus.error }}</small>
                      </div>

                      <el-form label-position="top" class="vault-deploy-form">
                        <el-form-item label="外部 Vault Web / API 链接">
                          <el-input v-model="externalVaultUrl" placeholder="http://127.0.0.1:8795" />
                        </el-form-item>
                        <el-row :gutter="10">
                          <el-col :xs="24" :sm="12">
                            <el-form-item label="主机">
                              <el-input v-model="vaultHost" />
                            </el-form-item>
                          </el-col>
                          <el-col :xs="24" :sm="12">
                            <el-form-item label="端口">
                              <el-input-number v-model="vaultPort" :min="1" :max="65535" />
                            </el-form-item>
                          </el-col>
                        </el-row>
                        <el-form-item label="Rhine-Vault 项目路径">
                          <el-input v-model="vaultPath" placeholder="E:\\Project\\Python\\Rhine-Vault" />
                        </el-form-item>
                        <el-form-item label="数据库路径">
                          <el-input v-model="vaultDatabasePath" placeholder="E:\\Project\\Python\\Rhine-Lore\\data\\rhine-vault-core.db" />
                        </el-form-item>
                        <el-form-item label="Python 解释器">
                          <el-input v-model="vaultPythonPath" placeholder="留空则优先使用 Vault 的 .venv" />
                        </el-form-item>
                        <el-space wrap>
                          <el-button type="primary" @click="connectVault">连接其他 Vault</el-button>
                          <el-button :loading="busyAction === '启动自定义资料库'" @click="startVault">
                            按当前设置启动
                          </el-button>
                        </el-space>
                      </el-form>
                    </div>
                  </div>
                </el-card>

                <el-card shadow="never" class="llm-config-card">
                  <template #header>
                    <div class="card-header">
                      <span>AI 正文扩写（OpenAI 兼容）</span>
                      <el-space wrap>
                        <el-button size="small" :loading="busyAction === '测试模型连接'" @click="testLlmConnection">
                          测试连接
                        </el-button>
                        <el-button size="small" type="primary" @click="saveLlmConfig">保存设置</el-button>
                      </el-space>
                    </div>
                  </template>
                  <el-form label-position="top" class="vault-deploy-form">
                    <el-row :gutter="10">
                      <el-col :xs="24" :sm="8">
                        <el-form-item label="通道预设">
                          <el-select v-model="llmPreset" @change="applyLlmProvider">
                            <el-option label="DeepSeek" value="deepseek" />
                            <el-option label="OpenAI" value="openai" />
                            <el-option label="自定义" value="custom" />
                          </el-select>
                        </el-form-item>
                      </el-col>
                      <el-col :xs="24" :sm="8">
                        <el-form-item label="API 地址">
                          <el-input v-model="llmBaseUrl" placeholder="https://api.deepseek.com/v1" />
                        </el-form-item>
                      </el-col>
                      <el-col :xs="24" :sm="8">
                        <el-form-item label="模型名称">
                          <el-input v-model="llmModel" placeholder="deepseek-chat" />
                        </el-form-item>
                      </el-col>
                      <el-col :xs="24" :sm="8">
                        <el-form-item label="API Key">
                          <el-input
                            v-model="llmApiKey"
                            type="password"
                            show-password
                            placeholder="已配置则留空保持不变"
                          />
                        </el-form-item>
                      </el-col>
                    </el-row>
                    <p class="knowledge-flow-note">
                      配置保存在服务端磁盘（data/llm-config.json），所有设备（含局域网手机）共用同一份；
                      生成请求经本机 Rhine-Vault 转发，浏览器不再持有密钥。
                      演化引擎本身仍离线可用，配置模型后只是把“场景简报”扩写成更完整的正文。
                    </p>
                    <el-space wrap>
                      <el-button size="small" type="danger" plain :disabled="!llmConfigured" @click="clearLlmKey">
                        清除 API Key
                      </el-button>
                    </el-space>
                  </el-form>
                </el-card>

                <el-row :gutter="14">
                  <el-col :xs="24" :lg="12">
                    <el-card shadow="never">
                      <template #header>
                        <div class="card-header">
                          <span>资料库工作区</span>
                          <el-button size="small" @click="refreshWorkspaces">刷新</el-button>
                        </div>
                      </template>
                      <el-form label-position="top">
                        <el-form-item label="当前资料库">
                          <el-select v-model="selectedWorkspaceId" @change="switchWorkspace">
                            <el-option
                              v-for="workspace in workspaces"
                              :key="workspace.workspace_id"
                              :label="workspace.display_name || workspace.workspace_id"
                              :value="workspace.workspace_id"
                            />
                          </el-select>
                        </el-form-item>
                        <el-form-item label="新资料库 ID">
                          <el-input v-model="newWorkspaceId" />
                        </el-form-item>
                        <el-form-item label="显示名称">
                          <el-input v-model="newWorkspaceDisplayName" />
                        </el-form-item>
                        <el-form-item label="检索配置">
                          <el-input v-model="profileId" />
                        </el-form-item>
                        <el-button type="primary" @click="createWorkspace">创建资料库</el-button>
                      </el-form>
                    </el-card>
                  </el-col>
                  <el-col :xs="24" :lg="12">
                    <el-card shadow="never">
                      <template #header>
                        <div class="card-header">
                          <span>资料入库</span>
                          <el-button size="small" @click="refreshKnowledgeCenter">刷新</el-button>
                        </div>
                      </template>
                      <div class="knowledge-pipeline compact">
                        <div v-for="stat in knowledgePipelineStats" :key="stat.label" class="stat-card" :class="stat.tone">
                          <b>{{ stat.value }}</b>
                          <span>{{ stat.label }}</span>
                        </div>
                      </div>
                      <p class="knowledge-flow-note">资料草稿不会直接影响创作，送去确认并入库后才会出现在对话写作参考里。</p>
                      <el-table :data="knowledgeDraftItems" height="220" class="knowledge-table">
                        <el-table-column prop="title" label="资料草稿" min-width="160" />
                        <el-table-column label="内容预览" min-width="220">
                          <template #default="{row}">
                            <span class="knowledge-preview">{{ preview(knowledgeEditableBody(row), 110) }}</span>
                          </template>
                        </el-table-column>
                        <el-table-column label="下一步" width="120">
                          <template #default="{row}">
                            <el-button size="small" @click="openKnowledgeReview(row)">审核</el-button>
                          </template>
                        </el-table-column>
                      </el-table>
                      <el-table :data="knowledgeReadyItems" height="220" class="advanced-table knowledge-table">
                        <el-table-column prop="title" label="待入库" min-width="160" />
                        <el-table-column label="内容预览" min-width="220">
                          <template #default="{row}">
                            <span class="knowledge-preview">{{ preview(knowledgeEditableBody(row), 110) }}</span>
                          </template>
                        </el-table-column>
                        <el-table-column label="下一步" width="110">
                          <template #default="{row}">
                            <el-button size="small" type="primary" @click="openKnowledgeReview(row)">确认</el-button>
                          </template>
                        </el-table-column>
                      </el-table>
                    </el-card>
                  </el-col>
                </el-row>
              </el-tab-pane>
            </el-tabs>
          </section>
        </main>
      </el-scrollbar>

    </section>

    <el-dialog
      v-model="shelfImportVisible"
      class="txt-import-dialog"
      title="导入 TXT"
      width="min(680px, calc(100vw - 24px))"
      append-to-body
      destroy-on-close
      @closed="resetShelfImportDialog"
    >
      <div class="txt-import-shell">
        <div class="txt-import-file">
          <span class="txt-import-file-icon"><GameIcon name="file-text" :size="20" /></span>
          <div>
            <strong>{{ shelfImportFileName }}</strong>
            <small>{{ shelfImportFileSize }}</small>
          </div>
          <span class="txt-import-encoding" :class="{attention: shelfImportNeedsAttention}">
            <GameIcon :name="shelfImportNeedsAttention ? 'alert' : 'check'" :size="14" />
            {{ shelfImportDecoded?.label }} · {{ shelfImportConfidenceLabel }}
          </span>
        </div>

        <label class="txt-import-field">
          <span>书名</span>
          <el-input v-model="shelfImportName" maxlength="120" />
        </label>

        <section class="txt-import-preview" :class="{attention: shelfImportNeedsAttention}">
          <header>
            <div>
              <strong>文字预览</strong>
              <small v-if="shelfImportNeedsAttention">编码识别结果需要确认</small>
            </div>
            <el-button link type="primary" @click="shelfImportAdvanced = !shelfImportAdvanced">
              {{ shelfImportAdvanced ? '收起编码' : '更换编码' }}
            </el-button>
          </header>
          <div v-if="shelfImportAdvanced" class="txt-import-encoding-control">
            <span>文件编码</span>
            <el-select v-model="shelfImportEncoding" @change="updateShelfImportDecoding">
              <el-option
                v-for="option in textEncodingOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </div>
          <pre>{{ shelfImportPreview }}</pre>
        </section>

        <p v-if="shelfImportError" class="txt-import-error">{{ shelfImportError }}</p>
      </div>
      <template #footer>
        <div class="txt-import-actions">
          <el-button @click="shelfImportVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="shelfImportBusy"
            :disabled="Boolean(shelfImportError) || !shelfImportDecoded?.text.trim()"
            @click="confirmShelfTxtImport"
          >
            导入并打开
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="createDialogVisible"
      class="create-story-dialog"
      title="开始一个新故事"
      width="min(560px, calc(100vw - 24px))"
    >
      <div class="create-story-intro">
        <strong>{{ selectedStoryTemplate.label }}</strong>
        <span>{{ selectedStoryTemplate.description }}</span>
      </div>
      <el-form label-position="top">
        <el-form-item label="故事起点">
          <el-radio-group v-model="newProjectTemplate" class="story-template-switch">
            <el-radio-button
              v-for="template in storyTemplates"
              :key="template.id"
              :value="template.id"
            >
              {{ template.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
        <div v-if="newProjectTemplate === 'gothic-fantasy'" class="story-template-summary">
          <span v-for="item in selectedStoryTemplate.contents" :key="item">{{ item }}</span>
        </div>
        <el-form-item label="故事名称">
          <el-input
            v-model="newProjectName"
            autofocus
            :placeholder="selectedStoryTemplate.name"
          />
        </el-form-item>
        <el-form-item label="故事类型">
          <el-select
            v-model="newProjectGenre"
            allow-create
            default-first-option
            filterable
            :placeholder="selectedStoryTemplate.genre"
          >
            <el-option v-for="genre in genreOptions" :key="genre" :label="genre" :value="genre" />
          </el-select>
        </el-form-item>
        <el-form-item label="一句话灵感">
          <el-input
            v-model="newProjectIdea"
            type="textarea"
            :rows="4"
            :placeholder="selectedStoryTemplate.summary || '例如：一个只在雨夜送信的人，收到了一封写给自己的信。'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="create-story-actions">
          <el-button @click="createDialogVisible = false">取消</el-button>
          <el-button @click="confirmCreateProject('chat')">创建并聊想法</el-button>
          <el-button type="primary" @click="confirmCreateProject('novel')">创建并写第一章</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="evolutionCharacterDialogVisible"
      class="evolution-character-dialog"
      title="为演化添加新角色"
      width="min(520px, calc(100vw - 24px))"
    >
      <el-form label-position="top">
        <el-form-item label="姓名">
          <el-input v-model="evolutionNewCharacter.name" placeholder="例如：阿岚" autofocus />
        </el-form-item>
        <el-form-item label="角色定位">
          <el-select v-model="evolutionNewCharacter.role" style="width: 100%">
            <el-option v-for="role in characterRoles" :key="role" :label="role" :value="role" />
          </el-select>
        </el-form-item>
        <el-form-item label="欲望 / 目标">
          <el-input v-model="evolutionNewCharacter.drive" placeholder="例如：寻找自己在故事中的位置" />
        </el-form-item>
        <el-form-item label="秘密（可选，会成为演化伏笔）">
          <el-input v-model="evolutionNewCharacter.secret" placeholder="例如：她见过陈栩的角" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="create-story-actions">
          <el-button @click="evolutionCharacterDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="busyAction === '添加角色'" @click="confirmAddEvolutionCharacter">
            添加并进入演化
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="restoreDialogVisible"
      title="从磁盘恢复项目"
      width="min(560px, calc(100vw - 24px))"
    >
      <div v-if="diskBackups.length === 0" class="product-empty-state compact">
        磁盘上没有项目备份
      </div>
      <div v-for="row in diskBackups" :key="row.project_id" class="backup-row">
        <div>
          <strong>{{ row.name }}</strong>
          <small>{{ row.project_id }} · {{ row.updated_at }}</small>
        </div>
        <el-button
          size="small"
          type="primary"
          :loading="restoreBusy === row.project_id"
          @click="confirmRestore(row)"
        >
          恢复
        </el-button>
      </div>
    </el-dialog>

    <el-drawer
      v-model="knowledgeReviewVisible"
      class="knowledge-review-drawer"
      :title="activeKnowledgeReviewItem?.stage === 'ready' ? '确认资料入库' : '审核资料草稿'"
      direction="rtl"
      size="min(720px, 96vw)"
      append-to-body
    >
      <div v-if="activeKnowledgeReviewItem" class="knowledge-review-shell">
        <section class="knowledge-review-status" :class="activeKnowledgeReviewItem.stage">
          <span class="knowledge-review-status-icon">
            <GameIcon :name="activeKnowledgeReviewItem.stage === 'ready' ? 'database' : 'file-text'" :size="19" />
          </span>
          <div>
            <strong>
              {{ activeKnowledgeReviewItem.stage === 'ready'
                ? activeKnowledgeRevisionTarget
                  ? `将更新“${activeKnowledgeRevisionTarget.title}”`
                  : '将新增一条正式资料'
                : '检查内容、来源和相似资料' }}
            </strong>
            <small>
              {{ activeKnowledgeReviewItem.stage === 'ready'
                ? activeKnowledgeRevisionTarget
                  ? `确认后生成 rev ${(activeKnowledgeReviewItem.baseRevision ?? activeKnowledgeRevisionTarget.revision ?? 1) + 1}，旧版本仍可回滚。`
                  : '确认后将成为对话可引用的正式资料。'
                : '保存修改不会直接入库；送审后还需要一次最终确认。' }}
            </small>
          </div>
          <span class="knowledge-review-type">{{ knowledgeTypeLabel(activeKnowledgeReviewItem.nodeType) }}</span>
        </section>

        <section class="knowledge-review-editor">
          <div class="knowledge-review-section-heading">
            <div><GameIcon name="edit" :size="17" /><strong>资料内容</strong></div>
            <small v-if="activeKnowledgeReviewItem.stage === 'ready'">只读</small>
          </div>
          <template v-if="activeKnowledgeReviewItem.stage === 'draft'">
            <div class="knowledge-review-fields two-column">
              <label>
                <span>资料类型</span>
                <el-select v-model="knowledgeReviewForm.nodeType">
                  <el-option v-for="option in knowledgeTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
                </el-select>
              </label>
              <label>
                <span>可信级别</span>
                <el-select v-model="knowledgeReviewForm.authority">
                  <el-option label="创作候选" value="experimental" />
                  <el-option label="项目事实" value="approved" />
                  <el-option label="参考资料" value="reference" />
                </el-select>
              </label>
            </div>
            <label class="knowledge-review-field">
              <span>标题</span>
              <el-input v-model="knowledgeReviewForm.title" maxlength="80" show-word-limit />
            </label>
            <label class="knowledge-review-field">
              <span>内容</span>
              <el-input v-model="knowledgeReviewForm.body" type="textarea" :rows="8" maxlength="8000" />
            </label>
            <label class="knowledge-review-field">
              <span>标签</span>
              <el-input v-model="knowledgeReviewForm.tagsText" placeholder="setting, character, clue" />
            </label>
          </template>
          <div v-else class="knowledge-review-readonly">
            <header>
              <strong>{{ activeKnowledgeReviewItem.title }}</strong>
              <span>{{ knowledgeTypeLabel(activeKnowledgeReviewItem.nodeType) }}</span>
            </header>
            <p>{{ knowledgeEditableBody(activeKnowledgeReviewItem) }}</p>
            <footer>
              <span v-for="tag in activeKnowledgeReviewItem.tags" :key="tag">{{ tag }}</span>
            </footer>
          </div>
        </section>

        <section class="knowledge-review-source">
          <div class="knowledge-review-section-heading">
            <div><GameIcon name="message" :size="17" /><strong>来源记录</strong></div>
            <small>{{ activeKnowledgeSource.messageIds.length > 0 ? `${activeKnowledgeSource.messageIds.length} 条消息` : '手动资料' }}</small>
          </div>
          <div v-if="activeKnowledgeSource.metadata" class="knowledge-source-grid">
            <div><span>来源</span><strong>{{ activeKnowledgeSource.kind || 'Rhine-Lore' }}</strong></div>
            <div><span>项目</span><strong>{{ activeKnowledgeSource.project || '未记录' }}</strong></div>
            <div><span>章节</span><strong>{{ activeKnowledgeSource.chapter || '未选择' }}</strong></div>
          </div>
          <div v-if="activeKnowledgeSource.excerpts.length > 0" class="knowledge-source-excerpts">
            <p v-for="(excerpt, index) in activeKnowledgeSource.excerpts" :key="index">{{ excerpt }}</p>
          </div>
          <p v-else class="knowledge-source-empty">这条资料由手动输入或旧版本创建，没有可回看的对话摘录。</p>
          <div v-if="activeKnowledgeSource.metadata" class="knowledge-source-actions">
            <el-button
              size="small"
              :disabled="!activeKnowledgeSourceTarget.messageId"
              @click="jumpToKnowledgeSource('chat')"
            >
              <GameIcon name="message" :size="15" />
              打开原对话
            </el-button>
            <el-button
              size="small"
              :disabled="!activeKnowledgeSourceTarget.chapter"
              @click="jumpToKnowledgeSource('chapter')"
            >
              <GameIcon name="book-open" :size="15" />
              打开章节
            </el-button>
            <small v-if="!activeKnowledgeSourceTarget.project">原项目不在当前设备，来源摘录仍可正常阅读。</small>
            <small v-else-if="!activeKnowledgeSourceTarget.messageId">原对话已被清理，来源摘录仍可正常阅读。</small>
          </div>
        </section>

        <section class="knowledge-review-similarity">
          <div class="knowledge-review-section-heading">
            <div><GameIcon name="search" :size="17" /><strong>相似资料</strong></div>
            <small>{{ activeKnowledgeSimilarities.length > 0 ? '入库前请确认是否重复或冲突' : '未发现明显相似项' }}</small>
          </div>
          <div v-if="activeKnowledgeSimilarities.length > 0" class="knowledge-similarity-list">
            <article
              v-for="match in activeKnowledgeSimilarities"
              :key="match.item.key"
              :class="{
                selectable: activeKnowledgeReviewItem.stage === 'draft' && match.item.stage === 'library',
                selected: knowledgeConflictTargetKey === match.item.key,
              }"
              :role="match.item.stage === 'library' ? 'button' : undefined"
              :tabindex="match.item.stage === 'library' ? 0 : undefined"
              @click="selectKnowledgeConflictTarget(match.item)"
              @keydown.enter="selectKnowledgeConflictTarget(match.item)"
            >
              <span
                class="knowledge-target-radio"
                :class="{hidden: match.item.stage !== 'library'}"
                aria-hidden="true"
              >
                <i />
              </span>
              <div>
                <strong>{{ match.item.title }}</strong>
                <p>{{ preview(knowledgeEditableBody(match.item), 150) }}</p>
                <small>
                  {{ match.reason }} · {{ knowledgeTypeLabel(match.item.nodeType) }}
                  <template v-if="match.item.revision"> · rev {{ match.item.revision }}</template>
                </small>
              </div>
              <span class="knowledge-similarity-score" :class="{high: match.score >= 0.5}">{{ Math.round(match.score * 100) }}%</span>
            </article>
          </div>
          <div v-else class="knowledge-similarity-clear">
            <GameIcon name="check" :size="18" />
            <span>标题、正文和标签中没有发现明显重复。</span>
          </div>
          <div v-if="activeKnowledgeReviewItem.stage === 'draft'" class="knowledge-conflict-decision">
            <div class="knowledge-conflict-mode" role="group" aria-label="相似资料处理方式">
              <button
                type="button"
                :class="{active: knowledgeConflictMode === 'coexist'}"
                @click="selectKnowledgeConflictMode('coexist')"
              >
                <GameIcon name="copy" :size="16" />
                <span><strong>并存</strong><small>保留为两条资料</small></span>
              </button>
              <button
                type="button"
                :disabled="!activeKnowledgeConflictTarget"
                :class="{active: knowledgeConflictMode === 'merge'}"
                @click="selectKnowledgeConflictMode('merge')"
              >
                <GameIcon name="git-merge" :size="16" />
                <span><strong>合并</strong><small>补充到已有资料</small></span>
              </button>
              <button
                type="button"
                :disabled="!activeKnowledgeConflictTarget"
                :class="{active: knowledgeConflictMode === 'replace'}"
                @click="selectKnowledgeConflictMode('replace')"
              >
                <GameIcon name="refresh" :size="16" />
                <span><strong>覆盖</strong><small>用草稿替换内容</small></span>
              </button>
            </div>
            <p v-if="knowledgeConflictMode === 'coexist'">
              当前草稿会以新资料入库，不改动任何已有内容。
            </p>
            <p v-else-if="activeKnowledgeConflictTarget">
              将更新“{{ activeKnowledgeConflictTarget.title }}”并生成 rev {{ (activeKnowledgeConflictTarget.revision ?? 1) + 1 }}，旧版本仍可回滚。
            </p>
            <p v-else>选择一条已入库的相似资料后，可以合并或覆盖。</p>
          </div>
        </section>
      </div>

      <template #footer>
        <div v-if="activeKnowledgeReviewItem" class="knowledge-review-footer">
          <template v-if="activeKnowledgeReviewItem.stage === 'draft'">
            <el-button type="danger" plain @click="rejectActiveKnowledgeReview">驳回</el-button>
            <span />
            <el-button :loading="busyAction === '保存资料修改'" @click="saveActiveKnowledgeReview()">保存修改</el-button>
            <el-button type="primary" :loading="busyAction === '保存并送审'" @click="stageActiveKnowledgeReview">
              保存并送审
              <GameIcon name="arrow-right" :size="15" />
            </el-button>
          </template>
          <template v-else>
            <el-button @click="knowledgeReviewVisible = false">返回</el-button>
            <span />
            <el-button type="primary" :loading="busyAction === '批量确认入库'" @click="approveActiveKnowledgeReady">
              确认入库
              <GameIcon name="check" :size="15" />
            </el-button>
          </template>
        </div>
      </template>
    </el-drawer>

    <el-drawer
      v-model="knowledgeExtractVisible"
      class="knowledge-extract-drawer"
      title="从对话提炼资料"
      direction="rtl"
      size="min(680px, 96vw)"
      append-to-body
    >
      <div class="knowledge-extract-shell">
        <div class="knowledge-extract-progress" aria-label="资料提炼步骤">
          <span :class="{active: knowledgeExtractStep === 'select', complete: knowledgeExtractStep === 'review'}">
            <b>1</b>
            选择对话
          </span>
          <i />
          <span :class="{active: knowledgeExtractStep === 'review'}">
            <b>2</b>
            审核资料
          </span>
        </div>

        <template v-if="knowledgeExtractStep === 'select'">
          <section class="knowledge-extract-intro">
            <span class="knowledge-extract-icon"><GameIcon name="message" :size="20" /></span>
            <div>
              <strong>选择真正包含设定的消息</strong>
              <small>最多 24 条。提炼只生成候选，不会自动进入知识库。</small>
            </div>
          </section>
          <div class="knowledge-message-tools">
            <span>已选择 {{ knowledgeSelectedMessageIds.length }} 条</span>
            <el-space wrap>
              <el-button size="small" @click="selectRecentKnowledgeMessages">最近 8 条</el-button>
              <el-button size="small" @click="selectAllKnowledgeMessages">最近 24 条</el-button>
              <el-button size="small" text @click="knowledgeSelectedMessageIds = []">清空</el-button>
            </el-space>
          </div>
          <div class="knowledge-message-list">
            <button
              v-for="message in knowledgeExtractMessages"
              :key="message.id"
              type="button"
              class="knowledge-message-row"
              :class="{selected: knowledgeSelectedMessageIds.includes(message.id)}"
              :disabled="knowledgeSelectedMessageIds.length >= 24 && !knowledgeSelectedMessageIds.includes(message.id)"
              @click="toggleKnowledgeExtractMessage(message.id)"
            >
              <span class="knowledge-message-check" aria-hidden="true">
                <GameIcon v-if="knowledgeSelectedMessageIds.includes(message.id)" name="check" :size="15" />
              </span>
              <span class="knowledge-message-copy">
                <span>
                  <strong>{{ message.role === 'user' ? '我' : 'Rhine-Lore' }}</strong>
                  <time>{{ chatTime(message.created_at) }}</time>
                </span>
                <small>{{ preview(message.content, 220) }}</small>
              </span>
            </button>
          </div>
        </template>

        <template v-else>
          <div class="knowledge-extract-result" :class="{offline: knowledgeExtractOffline}">
            <GameIcon :name="knowledgeExtractOffline ? 'database' : 'sparkles'" :size="18" />
            <span>
              <strong>{{ knowledgeExtractOffline ? '本地规则提炼' : 'AI 结构化提炼' }}</strong>
              <small>{{ knowledgeExtractNote }}</small>
            </span>
          </div>
          <div class="knowledge-candidate-summary">
            <span>找到 {{ knowledgeCandidates.length }} 条候选</span>
            <span>已选择 {{ knowledgeSelectedCandidateCount }} 条</span>
          </div>
          <div class="knowledge-candidate-list">
            <article
              v-for="candidate in knowledgeCandidates"
              :key="candidate.candidate_id"
              class="knowledge-candidate"
              :class="{selected: candidate.selected}"
            >
              <header>
                <button
                  type="button"
                  class="knowledge-candidate-toggle"
                  :aria-pressed="candidate.selected"
                  :aria-label="candidate.selected ? '取消选择资料' : '选择资料'"
                  @click="candidate.selected = !candidate.selected"
                >
                  <GameIcon v-if="candidate.selected" name="check" :size="15" />
                </button>
                <el-select v-model="candidate.node_type" size="small" aria-label="资料类型">
                  <el-option
                    v-for="option in knowledgeTypeOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
                <span class="knowledge-confidence">可信度 {{ Math.round(candidate.confidence * 100) }}%</span>
              </header>
              <label>
                <span>标题</span>
                <el-input v-model="candidate.title" maxlength="80" show-word-limit />
              </label>
              <label>
                <span>内容</span>
                <el-input v-model="candidate.content" type="textarea" :rows="4" maxlength="4000" />
              </label>
              <label>
                <span>标签</span>
                <el-input v-model="candidate.tagsText" placeholder="character, setting, clue" />
              </label>
              <footer>
                <span><GameIcon name="message" :size="15" /> 来源 {{ knowledgeCandidateSource(candidate).length }} 条消息</span>
                <small>{{ candidate.rationale }}</small>
              </footer>
            </article>
            <EmptyState
              v-if="knowledgeCandidates.length === 0"
              icon="database"
              title="没有可审核的候选"
              description="返回重新选择包含角色、规则、事件或伏笔的对话。"
              compact
            />
          </div>
        </template>
      </div>

      <template #footer>
        <div class="knowledge-extract-actions">
          <template v-if="knowledgeExtractStep === 'select'">
            <el-button @click="knowledgeExtractVisible = false">取消</el-button>
            <el-button
              type="primary"
              :disabled="knowledgeSelectedMessageIds.length === 0"
              :loading="busyAction === '提炼对话资料'"
              @click="runKnowledgeExtraction"
            >
              <GameIcon name="sparkles" :size="16" />
              提炼候选
            </el-button>
          </template>
          <template v-else>
            <el-button @click="knowledgeExtractStep = 'select'">
              <GameIcon name="chevron-left" :size="16" />
              返回选择
            </el-button>
            <el-button @click="knowledgeExtractVisible = false">暂不保存</el-button>
            <el-button
              type="primary"
              :disabled="knowledgeSelectedCandidateCount === 0"
              :loading="busyAction === '保存资料草稿'"
              @click="saveKnowledgeCandidates"
            >
              保存 {{ knowledgeSelectedCandidateCount }} 条草稿
            </el-button>
          </template>
        </div>
      </template>
    </el-drawer>

    <el-drawer
      v-model="aiPanelOpen"
      title="AI 生成通道"
      direction="rtl"
      size="min(380px, 88vw)"
    >
      <div class="ai-drawer-body">
        <div class="ai-status-row" :class="aiStatusTone">
          <strong>状态 · {{ aiStatusLabel }}</strong>
          <span>{{ aiStatusDetail || "点击「测试连接」检查通道状态" }}</span>
        </div>
        <div class="ai-drawer-section">
          <label>通道预设</label>
          <el-select v-model="llmPreset" style="width: 100%" @change="applyLlmProvider">
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="OpenAI" value="openai" />
            <el-option label="自定义" value="custom" />
          </el-select>
          <label>API 地址</label>
          <el-input v-model="llmBaseUrl" placeholder="API 地址" />
          <label>模型</label>
          <el-input v-model="llmModel" placeholder="模型" />
          <label>API Key</label>
          <el-input
            v-model="llmApiKey"
            type="password"
            show-password
            placeholder="已配置则留空保持不变"
          />
        </div>
        <div class="ai-status-actions">
          <el-button :loading="aiStatus === 'checking'" @click="runAiCheck">测试连接</el-button>
          <el-button type="primary" @click="saveLlmConfig">保存并检查</el-button>
          <el-button @click="openDeepSeekKeyAssistant">DeepSeek 登录取 Key</el-button>
          <el-button @click="pasteDeepSeekKey">从剪贴板读取</el-button>
          <small>配置后对话创作与演化正文都走此通道；未配置时使用离线模板。</small>
        </div>
      </div>
    </el-drawer>

    <el-drawer
      v-model="readerNavigatorVisible"
      class="reader-drawer"
      direction="ltr"
      size="min(420px, 92vw)"
      :with-header="false"
      append-to-body
    >
      <ReaderNavigator
        v-model:active-tab="readerNavigatorTab"
        :title="readerWorkTitle"
        :toc="readerTocItems"
        :current-chapter-id="readerCurrentChapterId"
        :query="readerSearchQuery"
        :results="readerSearchResults"
        :searching="readerSearching"
        :bookmarks="readerCurrentBookmarks"
        @update:query="readerSearchQuery = $event"
        @search="runReaderSearch"
        @select-chapter="selectReaderChapter"
        @open-result="openReaderSearchResult"
        @open-bookmark="openReaderBookmark"
        @remove-bookmark="removeReaderBookmark"
      />
    </el-drawer>

    <el-dialog
      v-model="branchTreeVisible"
      class="branch-tree-dialog"
      width="min(1180px, calc(100vw - 24px))"
      append-to-body
      destroy-on-close
    >
      <template #header>
        <div class="branch-tree-dialog-title">
          <span class="section-icon"><GameIcon name="route" :size="19" /></span>
          <div>
            <strong>故事分支树</strong>
            <small>选择一条故事线，阅读它，或让它继续生长</small>
          </div>
          <el-button size="small" @click="createBranchFromTree">
            <GameIcon name="sparkles" :size="15" />
            从当前阅读位置分支
          </el-button>
        </div>
      </template>

      <div class="branch-tree-workspace">
        <BranchTree
          :branches="shelfBranches"
          :selected-id="selectedShelfBranchId"
          :chapter-title="shelfChapter?.title || '当前章节'"
          @select="selectShelfBranch"
          @create="createBranchFromTree"
        />

        <aside v-if="selectedShelfBranch" class="branch-tree-inspector">
          <div class="branch-inspector-heading">
            <span :class="`branch-kind-mark tone-${selectedShelfBranch.kind || 'free'}`" />
            <div>
              <small>{{ branchKindLabels[selectedShelfBranch.kind || "free"] }} · 第 {{ selectedShelfBranch.depth + 1 }} 层</small>
              <strong>{{ selectedShelfBranch.title || selectedShelfBranch.guidance || "未命名分支" }}</strong>
            </div>
          </div>

          <div v-if="branchPathBusy" class="branch-inspector-loading">
            <GameIcon name="refresh" :size="18" />
            <span>正在还原这条故事线</span>
          </div>
          <template v-else>
            <section class="branch-lineage-section">
              <div class="branch-inspector-label">
                <strong>当前路径</strong>
                <span>{{ selectedBranchPath?.lineage.length || 1 }} 个选择</span>
              </div>
              <div class="branch-lineage-list">
                <span class="branch-lineage-origin"><GameIcon name="book-open" :size="14" />原作主线</span>
                <button
                  v-for="(item, index) in selectedBranchPath?.lineage || []"
                  :key="item.branch_id"
                  type="button"
                  :class="{active: item.branch_id === selectedShelfBranchId}"
                  @click="selectShelfBranch(item)"
                >
                  <b>{{ index + 1 }}</b>
                  <span>{{ item.title || item.guidance || "自然续写" }}</span>
                </button>
              </div>
            </section>

            <section class="branch-inspector-copy">
              <div class="branch-inspector-label">
                <strong>节点正文</strong>
                <span>{{ selectedShelfBranch.text.length.toLocaleString() }} 字</span>
              </div>
              <div>
                <p v-for="(paragraph, index) in splitReaderParagraphs(selectedShelfBranch.text).slice(0, 5)" :key="index">
                  {{ paragraph }}
                </p>
              </div>
            </section>

            <p v-if="selectedShelfBranch.offline" class="branch-inspector-offline">
              这个节点只保存了分支点。连接 AI 后可重新生成正文。
            </p>

            <div class="branch-inspector-actions">
              <el-button :disabled="selectedShelfBranch.offline" @click="openSelectedBranchPath">
                <GameIcon name="book-open" :size="15" />
                阅读此线
              </el-button>
              <el-button type="primary" :disabled="selectedShelfBranch.offline" @click="continueShelfBranch()">
                <GameIcon name="git-fork" :size="15" />
                沿此线继续
              </el-button>
              <el-button
                :loading="branchProjectBusy"
                :disabled="selectedShelfBranch.offline"
                @click="materializeShelfProject(selectedShelfBranch.branch_id)"
              >
                <GameIcon name="pen" :size="15" />
                进入工作台
              </el-button>
              <el-button class="branch-delete-action" @click="removeSelectedShelfBranch">
                <GameIcon name="trash" :size="15" />
                删除分支
              </el-button>
            </div>
          </template>
        </aside>

        <aside v-else class="branch-tree-inspector branch-tree-inspector-empty">
          <GameIcon name="git-fork" :size="24" />
          <strong>从一个不同的选择开始</strong>
          <p>故事树会保留原作，让每条新路线独立生长。</p>
        </aside>
      </div>
    </el-dialog>

    <el-dialog
      v-model="branchPathVisible"
      class="branch-path-dialog"
      width="min(820px, calc(100vw - 20px))"
      append-to-body
      destroy-on-close
    >
      <template #header>
        <div class="branch-path-title">
          <span class="section-icon"><GameIcon name="book-open" :size="19" /></span>
          <div>
            <strong>{{ selectedShelfBranch?.title || "分支故事" }}</strong>
            <small>
              {{ selectedBranchPath?.chapter.title }} · {{ selectedBranchPath?.lineage.length || 1 }} 层故事线
            </small>
          </div>
        </div>
      </template>
      <article
        v-if="selectedBranchPath"
        class="branch-path-reader"
        :class="readerThemeClass()"
        :style="readerContentStyle()"
      >
        <div class="branch-path-breadcrumb">
          <span>原作</span>
          <template v-for="item in selectedBranchPath.lineage" :key="item.branch_id">
            <GameIcon name="chevron-right" :size="13" />
            <span>{{ item.title || item.guidance || "自然续写" }}</span>
          </template>
        </div>
        <h2>{{ selectedBranchPath.chapter.title }} · 分支</h2>
        <p v-for="(paragraph, index) in splitReaderParagraphs(selectedBranchPath.text)" :key="index">
          {{ paragraph }}
        </p>
        <div class="branch-path-end">
          <span><GameIcon name="git-fork" :size="17" /></span>
          <strong>这条故事线仍可继续</strong>
        </div>
      </article>
      <template #footer>
        <div class="branch-path-actions">
          <el-button @click="branchPathVisible = false">返回故事树</el-button>
          <el-button :loading="branchProjectBusy" @click="materializeShelfProject(selectedShelfBranch?.branch_id || '')">
            进入工作台
          </el-button>
          <el-button type="primary" @click="continueShelfBranch()">
            <GameIcon name="git-fork" :size="15" />
            从结尾继续分支
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="branchDialogVisible"
      class="branch-creative-dialog"
      width="min(760px, calc(100vw - 24px))"
      append-to-body
      destroy-on-close
      :close-on-click-modal="false"
    >
      <template #header>
        <div class="branch-dialog-title">
          <span class="section-icon"><GameIcon name="git-merge" :size="19" /></span>
          <div>
            <strong>分支续写</strong>
            <small>{{ branchPositionLabel() }}</small>
          </div>
          <span class="branch-source-badge">
            {{ branchContext?.source === "shelf" ? "导入小说" : "工作台正文" }}
          </span>
        </div>
      </template>

      <div v-if="branchContext" class="branch-dialog-body">
        <section class="branch-anchor-card">
          <div class="branch-section-head">
            <strong>分支点之前</strong>
            <span>原文保持不变</span>
          </div>
          <blockquote>{{ branchContext.anchor || "章节开头" }}<i aria-hidden="true" /></blockquote>
          <p v-if="branchContext.selectedText" class="branch-selection-note">
            已从选中文字末尾开始：{{ branchContext.selectedText.slice(0, 90) }}
          </p>
        </section>

        <section class="branch-guidance-section">
          <div class="branch-section-head">
            <strong>这条分支往哪里走</strong>
            <span>{{ branchKindLabels[branchKind] }} · 可留空自然续写</span>
          </div>
          <el-input
            v-model="branchGuidance"
            type="textarea"
            :rows="3"
            maxlength="600"
            show-word-limit
            placeholder="例如：让主角没有交出钥匙，并从这一决定开始改变后续关系"
            :disabled="branchBusy"
          />
          <div class="branch-guidance-presets">
            <button type="button" :class="{active: branchKind === 'choice'}" @click="applyBranchPreset('choice', '制造一个与原作不同的关键选择')">关键选择</button>
            <button type="button" :class="{active: branchKind === 'relationship'}" @click="applyBranchPreset('relationship', '改变两名角色在这一刻的关系走向')">关系变化</button>
            <button type="button" :class="{active: branchKind === 'clue'}" @click="applyBranchPreset('clue', '揭示一条新的线索，但保持原有设定一致')">新线索</button>
            <button type="button" :class="{active: branchKind === 'free'}" @click="applyBranchPreset('free', '')">自由续写</button>
          </div>
        </section>

        <section v-if="branchBusy" class="branch-generating-state" aria-live="polite">
          <span class="branch-generating-icon"><GameIcon name="sparkles" :size="20" /></span>
          <div>
            <strong>正在沿这条支线写下去</strong>
            <small>会参考前文、人物卡和世界设定，不会改动原稿。</small>
          </div>
        </section>

        <section v-else-if="branchResult" class="branch-result-panel">
          <div class="branch-section-head">
            <strong>{{ branchRecord?.offline ? "分支点已保存" : "分支草稿" }}</strong>
            <span v-if="branchRecord">{{ Math.round(branchRecord.progress) }}% · {{ branchRecord.created_at }}</span>
          </div>
          <div class="branch-result-copy" :class="{offline: branchRecord?.offline}">
            <p v-for="(paragraph, index) in splitReaderParagraphs(branchResult)" :key="index">
              {{ paragraph }}
            </p>
          </div>
          <div v-if="branchRecord?.offline" class="branch-offline-note">
            <GameIcon name="alert" :size="17" />
            <span>当前没有可用的 AI 通道。这个位置已经保存，连接 AI 后可重新生成。</span>
            <el-button size="small" @click="branchDialogVisible = false; aiPanelOpen = true">连接 AI</el-button>
          </div>
        </section>

        <section v-if="branchContext.source === 'shelf'" class="branch-workbench-preview">
          <div>
            <strong>作为创作项目继续</strong>
            <small>
              {{ shelfAnalysis
                ? `${shelfAnalysis.characters.length} 个角色、${shelfAnalysis.settings.length} 项设定会进入工作台`
                : "创建时会先分析全书，再导入角色、势力、地点与关系" }}
            </small>
          </div>
          <GameIcon name="arrow-right" :size="18" />
        </section>
      </div>

      <template #footer>
        <div class="branch-dialog-actions">
          <el-button @click="branchDialogVisible = false">{{ branchResult ? "保留并关闭" : "取消" }}</el-button>
          <el-button
            v-if="branchResult"
            :loading="branchBusy"
            :disabled="Boolean(branchRecord?.offline) && !llmConfigured"
            @click="generateBranchDraft"
          >
            {{ branchRecord?.offline ? "重新生成" : "再生成一版" }}
          </el-button>
          <el-button
            v-if="branchResult && branchContext?.source === 'shelf'"
            type="primary"
            :loading="branchProjectBusy"
            :disabled="!branchRecord || branchRecord.offline"
            @click="materializeShelfProject(branchRecord?.branch_id || '')"
          >
            创建工作台项目
          </el-button>
          <el-button
            v-else-if="branchResult && branchContext?.source === 'project'"
            type="primary"
            @click="materializeProjectBranch"
          >
            创建独立分支项目
          </el-button>
          <el-button v-else type="primary" :loading="branchBusy" @click="generateBranchDraft">
            <GameIcon name="sparkles" :size="16" />
            生成分支
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-drawer
      v-model="readerSettingsVisible"
      class="reader-settings-drawer"
      title="阅读设置"
      direction="rtl"
      size="min(430px, 94vw)"
      append-to-body
    >
      <ReaderSettingsPanel
        v-model:page-mode="readerPageMode"
        v-model:theme="readerTheme"
        v-model:font-family="readerFontFamily"
        v-model:font-size="readerFontSize"
        v-model:line-height="readerLineHeight"
        v-model:paragraph-spacing="readerParagraphSpacing"
        v-model:measure="readerMeasure"
        v-model:brightness="readerBrightness"
        v-model:justify="readerJustify"
        v-model:indent="readerIndent"
        v-model:auto-advance="readerAutoAdvance"
        @change="persistReaderSettings"
        @reset="resetReaderSettings"
      />
    </el-drawer>

    <div
      v-if="readerOverlayOpen && readerCurrentChapterId"
      class="reader-overlay"
      :class="[
        readerThemeClass(),
        {'reader-overlay-paged': readerPageMode === 'page', 'reader-chrome-hidden': !readerChromeVisible},
      ]"
      :style="readerContentStyle()"
      role="application"
      aria-label="沉浸阅读器"
    >
      <header class="reader-overlay-header">
        <button type="button" class="reader-icon-button" title="退出阅读" aria-label="退出阅读" @click="exitReaderMode">
          <GameIcon name="close" :size="19" />
        </button>
        <div class="reader-overlay-title">
          <strong>{{ readerWorkTitle }}</strong>
          <span>{{ readerCurrentTitle }}<template v-if="readerEstimatedMinutes > 0"> · 约 {{ readerEstimatedMinutes }} 分钟</template></span>
        </div>
        <nav class="reader-overlay-actions" aria-label="阅读工具">
          <button type="button" class="reader-icon-button" title="目录" aria-label="目录" @click="openReaderNavigator('toc')">
            <GameIcon name="list" :size="19" />
          </button>
          <button type="button" class="reader-icon-button" title="全书搜索" aria-label="全书搜索" @click="openReaderNavigator('search')">
            <GameIcon name="search" :size="19" />
          </button>
          <button
            type="button"
            class="reader-icon-button"
            :class="{active: readerCurrentBookmark}"
            :title="readerCurrentBookmark ? '移除书签' : '添加书签'"
            :aria-label="readerCurrentBookmark ? '移除书签' : '添加书签'"
            @click="toggleReaderBookmark"
          >
            <GameIcon name="bookmark" :size="19" />
          </button>
          <button
            v-if="readerSource === 'shelf' || readerSource === 'novel'"
            type="button"
            class="reader-icon-button"
            :class="{active: capturedBranchSelection?.chapterId === readerCurrentChapterId}"
            title="从选中内容或当前页分支续写"
            aria-label="分支续写"
            @click="openReaderBranch"
          >
            <GameIcon name="git-merge" :size="19" />
          </button>
          <button type="button" class="reader-icon-button" title="阅读设置" aria-label="阅读设置" @click="readerSettingsVisible = true">
            <GameIcon name="type" :size="19" />
          </button>
          <button type="button" class="reader-icon-button desktop-reader-control" title="全屏" aria-label="切换全屏" @click="toggleReaderFullscreen">
            <GameIcon :name="readerFullscreenActive ? 'fullscreen-exit' : 'fullscreen'" :size="19" />
          </button>
          <button
            v-if="readerSource === 'novel'"
            type="button"
            class="reader-icon-button"
            title="返回编辑"
            aria-label="返回编辑"
            @click="exitReaderMode"
          >
            <GameIcon name="edit" :size="19" />
          </button>
        </nav>
      </header>

      <div class="reader-overlay-scroll">
        <article
          class="reader-overlay-content"
          @mouseup="captureBranchSelection"
          @touchend="captureBranchSelection"
        >
          <template v-if="readerPageMode === 'page'">
            <div
              ref="readerOverlayPageAreaRef"
              class="reader-page-area"
              :class="{'is-title-page': currentReaderPageIsTitle()}"
            >
              <section
                v-if="currentReaderPageIsTitle()"
                class="reader-title-page"
                :class="{'is-volume': readerCurrentTitleIsVolume}"
              >
                <p class="reader-title-page-work">{{ readerWorkTitle }}</p>
                <h1>{{ readerCurrentTitle }}</h1>
                <p class="reader-title-page-meta">{{ readerTitlePageMeta }}</p>
              </section>
              <template v-else>
                <p
                  v-for="(paragraph, index) in currentReaderPage()"
                  :key="`ov-${readerPageIndex}-${index}`"
                  :class="{'reader-paragraph-continuation': paragraph.continuation}"
                >
                  {{ paragraph.text }}
                </p>
              </template>
            </div>
            <div class="reader-page-meta">{{ readerPageIndex + 1 }} / {{ Math.max(1, readerPages.length) }} 页</div>
          </template>
          <template v-else>
            <p class="reader-overlay-kicker">{{ readerWorkTitle }}</p>
            <h1>{{ readerCurrentTitle }}</h1>
            <p v-for="(paragraph, index) in readerCurrentParagraphs" :key="`ov-${index}`">
              {{ paragraph }}
            </p>
            <p v-if="readerCurrentParagraphs.length === 0" class="empty-paragraph">这一章还没有正文。</p>
          </template>
        </article>
      </div>

      <div class="reader-tap-zones">
        <button
          type="button"
          class="reader-tap-zone left"
          :disabled="readerPageMode === 'page' ? (readerPageIndex <= 0 && readerCurrentChapterIndex <= 0) : readerCurrentChapterIndex <= 0"
          aria-label="上一章或上一页"
          @click="readerPagePrev"
        />
        <button
          type="button"
          class="reader-tap-zone center"
          aria-label="显示或隐藏阅读工具"
          @click="readerChromeVisible = !readerChromeVisible"
        />
        <button
          type="button"
          class="reader-tap-zone right"
          :disabled="readerPageMode === 'page' ? (readerPageIndex >= readerPages.length - 1 && readerCurrentChapterIndex >= readerTocItems.length - 1) : readerCurrentChapterIndex >= readerTocItems.length - 1"
          aria-label="下一章或下一页"
          @click="readerPageNext"
        />
      </div>

      <footer class="reader-overlay-footer">
        <button type="button" class="reader-icon-button" :disabled="readerCurrentChapterIndex <= 0" title="上一章" @click="openReaderAdjacentChapter(-1)">
          <GameIcon name="chevron-left" :size="20" />
        </button>
        <div class="reader-progress-control">
          <span>{{ readerCurrentChapterIndex + 1 }} / {{ readerTocItems.length }}</span>
          <input
            :value="readerOverallProgress"
            type="range"
            min="0"
            max="100"
            step="0.1"
            aria-label="全书阅读进度"
            @change="seekReaderOverallProgress(Number(($event.target as HTMLInputElement).value))"
          />
          <b>{{ Math.round(readerOverallProgress) }}%</b>
        </div>
        <button type="button" class="reader-icon-button" :disabled="readerCurrentChapterIndex >= readerTocItems.length - 1" title="下一章" @click="openReaderAdjacentChapter(1)">
          <GameIcon name="chevron-right" :size="20" />
        </button>
      </footer>
    </div>
  </div>
</template>








