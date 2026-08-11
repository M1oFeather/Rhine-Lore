<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";

import {
  type ApiRecord,
  type AgentToolAction,
  type BookAnalysis,
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
  type ManuscriptIssue,
  type ProjectBackupRow,
  type StoryMap,
  type StoryMapEdge,
  type StoryMapNode,
  type StoryProject,
  type VaultRuntimeStatus,
  type VaultWebStatus,
  type WorkspaceRecord,
  type WorldCard,
  advanceEvolution,
  advanceEvolutionChapter,
  addEvolutionCharacter,
  approveStaging,
  aiWriteBook,
  analyzeBook,
  backupProject,
  buildContextBundle,
  connectVaultRuntime,
  createManualProposal,
  fakeCreativeAnswer,
  generateEvolutionProseApi,
  generateKnowledgeDocument,
  getEvolutionState,
  getLanInfo,
  getLlmServerConfig,
  getBook,
  getBookChapter,
  getVaultRuntimeStatus,
  getVaultWebStatus,
  guideEvolution,
  health,
  installVaultWeb,
  importBook,
  deleteBook,
  listBooks,
  llmServerChat,
  llmServerPing,
  listNodes,
  listProposals,
  listStaging,
  listWorkspaces,
  listProjectBackups,
  registerWorkspace,
  regenerateEvolutionChapter,
  resetEvolutionRun,
  restoreProjectBackup,
  saveBookChapter,
  saveLlmServerConfig,
  setWorkspaceId,
  stageProposal,
  startEvolutionRun,
  startVaultRuntime,
  stopVaultRuntime,
  workspaceId,
} from "./api";
import GameIcon from "./components/GameIcon.vue";
import type { GameIconName } from "./icons/gameIconPack";

type Activity = "studio" | "story" | "world" | "characters" | "chat" | "novel" | "context" | "evolution" | "read" | "shelf" | "map" | "settings";
type WorkMode = "write" | "advanced";
type BackendStatus = "checking" | "online" | "offline";
type CreateDestination = "novel" | "chat";
type EvolutionChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
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
  {id: "studio", label: "工作台", icon: "home", description: "选择故事和开始写作"},
  {id: "story", label: "故事档案", icon: "file-text", description: "名称、类型和概要"},
  {id: "world", label: "世界观", icon: "globe", description: "规则、地点和历史"},
  {id: "characters", label: "角色", icon: "users", description: "人物、动机和关系"},
  {id: "chat", label: "对话创作", icon: "message", description: "聊剧情，生成草稿"},
  {id: "novel", label: "正文", icon: "pen", description: "阅读和编辑章节"},
  {id: "context", label: "资料库", icon: "database", description: "查找设定和参考资料"},
  {id: "evolution", label: "演化", icon: "sparkles", description: "沙盘观演与有限视角小说"},
  {id: "read", label: "小说阅读", icon: "book-open", description: "像追更一样读演化正文"},
  {id: "shelf", label: "书架", icon: "library", description: "导入并阅读 TXT 长篇小说"},
  {id: "map", label: "地图", icon: "map", description: "故事空间与地点连接"},
  {id: "settings", label: "设置", icon: "settings", description: "连接、高级和维护"},
];

const activity = ref<Activity>("studio");
const sidebarCollapsed = ref(localStorage.getItem("rhine-lore-sidebar-collapsed") === "1");
const mobileNavOpen = ref(false);
const showAllProjects = ref(false);
const novelTocVisible = ref(false);
const novelSettingsVisible = ref(false);
const readTocVisible = ref(false);
const readSettingsVisible = ref(false);
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
const newProjectName = ref("");
const newProjectGenre = ref("未分类");
const newProjectIdea = ref("");
const projects = ref<StoryProject[]>(loadProjects());
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
const chatInput = ref("");
const chatThinking = ref(false);
const chatThreadRef = ref<HTMLElement | null>(null);
const chatSidebarOpen = ref(true);
const chatSideSections = ref({chapter: true, refs: true, issues: true});
const chatAttachment = ref<{name: string; kind: "txt" | "project" | "knowledge"; text: string} | null>(null);
const chatAttachInput = ref<HTMLInputElement | null>(null);
const chatMode = ref<"chat" | "adjust">("chat");
const adjustInput = ref("");
const revisionBusy = ref(false);
const revisionPreview = ref<RevisionResult | null>(null);
const readerMode = ref<"read" | "edit">("read");
const readerFontSize = ref(18);
const readerLineHeight = ref(Number(localStorage.getItem("rhine-lore-reader-line-height") || "1.9"));
const readerTheme = ref<"day" | "sepia" | "night">(
  (localStorage.getItem("rhine-lore-reader-theme") as "day" | "sepia" | "night") || "day",
);
const shelfBooks = ref<BookMeta[]>([]);
const shelfBookId = ref("");
const shelfBook = ref<BookDetail | null>(null);
const shelfChapter = ref<BookChapter | null>(null);
const shelfChapterIndex = ref(-1);
const shelfTocVisible = ref(false);
const shelfSettingsVisible = ref(false);
const shelfGuidance = ref("");
const shelfAiMode = ref<"continue" | "rewrite" | "expand">("continue");
const shelfAiResult = ref("");
const shelfAiBusy = ref(false);
const shelfAnalysis = ref<BookAnalysis | null>(null);
const shelfAnalyzeBusy = ref(false);
const shelfSaving = ref(false);
const shelfImportInput = ref<HTMLInputElement | null>(null);
const settingsTab = ref("basic");
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
const evolutionCharacterDialogVisible = ref(false);
const evolutionNewCharacter = ref({name: "", role: "配角", drive: "", secret: ""});
const ignoredCharacterPromptProjects = ref<string[]>([]);
const evolutionTimelineLimit = ref(30);
const characterEditorMode = ref<"simple" | "full">(
  localStorage.getItem("rhine-lore-character-mode") === "full" ? "full" : "simple",
);
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
let projectBackupTimer: number | undefined;
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
  return projects.value.find((project) => project.id === activeProjectId.value) ?? projects.value[0];
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

const knowledgePipelineStats = computed(() => [
  {label: "资料草稿", value: proposals.value.length, tone: "amber"},
  {label: "待入库", value: stagingEntries.value.length, tone: "blue"},
  {label: "已入库", value: nodes.value.length, tone: "green"},
]);

const knowledgePipelineHint = computed(() => {
  if (proposals.value.length > 0) {
    return `${proposals.value.length} 条资料草稿等待整理`;
  }
  if (stagingEntries.value.length > 0) {
    return `${stagingEntries.value.length} 条待确认资料可以入库`;
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
  return content
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
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

onMounted(async () => {
  await perform("初始化", async () => {
    await Promise.allSettled([updateBackendStatus(), refreshWorkspaces(), refreshNodes(), refreshReview()]);
    return {ready: true};
  }, {collapseOutput: true});
  void runAiCheck();
  void loadDiskBackups();
  void loadLanInfo();
  void loadLlmServerConfig();
});

function loadProjects(): StoryProject[] {
  const raw = localStorage.getItem(projectKey);
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as Partial<StoryProject>[];
      return parsed.map(normalizeProject);
    } catch {
      localStorage.removeItem(projectKey);
    }
  }
  return [
    {
      id: `project-${Date.now()}`,
      name: "我的故事",
      genre: "未分类",
      summary: "",
      global_guidance: "",
      chapter_turns: 4,
      writing_style: "",
      polish_writing: true,
      style_example: "",
      style_notes: "",
      style_avoid: "",
      world: [],
      characters: [],
      map: {nodes: [], edges: []},
      chapters: [],
      chat: [],
      issues: [],
    },
  ];
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
  localStorage.setItem(projectKey, JSON.stringify(projects.value));
  localStorage.setItem(activeProjectKey, activeProjectId.value);
  localStorage.setItem(activeChapterKey, activeChapterId.value);
  lastSavedAt.value = new Date().toLocaleTimeString("zh-CN", {hour: "2-digit", minute: "2-digit"});
  if (projectBackupTimer) {
    window.clearTimeout(projectBackupTimer);
  }
  projectBackupTimer = window.setTimeout(() => {
    void backupActiveProject();
  }, 900);
}

async function backupActiveProject(): Promise<void> {
  const project = activeProject.value;
  if (!project?.id) {
    return;
  }
  try {
    await backupProject(project);
  } catch {
    // 磁盘备份失败不打断写作
  }
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
    if (result !== undefined) {
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
    if (evolutionNovelChapters.value.length > 0) {
      evolutionChapterIndex.value = evolutionNovelChapters.value.length - 1;
    }
    requestAnimationFrame(() => window.scrollTo({top: 0, behavior: "auto"}));
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
}

function toggleSidebar(): void {
  sidebarCollapsed.value = !sidebarCollapsed.value;
  localStorage.setItem("rhine-lore-sidebar-collapsed", sidebarCollapsed.value ? "1" : "0");
}

function persistReaderSettings(): void {
  localStorage.setItem("rhine-lore-reader-line-height", String(readerLineHeight.value));
  localStorage.setItem("rhine-lore-reader-theme", readerTheme.value);
}

function readerThemeClass(): string {
  return `theme-${readerTheme.value}`;
}

async function loadShelfBooks(): Promise<void> {
  try {
    const result = await listBooks();
    shelfBooks.value = result.books;
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  }
}

function handleShelfTxtImport(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    return;
  }
  const reader = new FileReader();
  reader.onload = async () => {
    const text = String(reader.result ?? "");
    if (!text.trim()) {
      runState.value = {error: "文件内容为空"};
      return;
    }
    await perform("导入 TXT", async () => {
      const book = await importBook({
        name: file.name.replace(/\.(txt|text)$/i, ""),
        genre: "TXT 导入",
        text,
      });
      shelfBooks.value = (await listBooks()).books;
      await openShelfBook(book.book_id);
      return {book_id: book.book_id, chapters: book.chapter_count, chars: book.total_chars};
    });
  };
  reader.readAsText(file, "utf-8");
  input.value = "";
}

async function openShelfBook(bookId: string): Promise<void> {
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
  const saved = localStorage.getItem(`rhine-shelf-pos-${bookId}`);
  const targetId =
    saved && result.book.chapters.some((item) => item.id === saved)
      ? saved
      : (result.book.chapters[0]?.id ?? "");
  if (targetId) {
    await loadShelfChapter(targetId);
  }
  requestAnimationFrame(() => window.scrollTo({top: 0, behavior: "auto"}));
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
  requestAnimationFrame(() => window.scrollTo({top: 0, behavior: "auto"}));
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
  if (!shelfBookId.value || shelfAnalyzeBusy.value) {
    return;
  }
  shelfAnalyzeBusy.value = true;
  try {
    const result = await analyzeBook(shelfBookId.value);
    shelfAnalysis.value = result.analysis;
    markSaved(
      result.offline
        ? "离线分析完成（高频角色提取，配置 AI 后可获得完整档案）"
        : "全书分析完成：角色 / 设定 / 事实 / 伏笔已建立",
    );
  } catch (error) {
    runState.value = {error: error instanceof Error ? error.message : String(error)};
  } finally {
    shelfAnalyzeBusy.value = false;
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

async function removeShelfBook(bookId: string): Promise<void> {
  await perform("删除书", () => deleteBook(bookId));
  localStorage.removeItem(`rhine-shelf-pos-${bookId}`);
  if (shelfBookId.value === bookId) {
    shelfBook.value = null;
    shelfBookId.value = "";
    shelfChapter.value = null;
  }
  await loadShelfBooks();
}

function shelfChapterParagraphs(chapter: BookChapter): string[] {
  return (chapter.content ?? "")
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
}

function shelfProgressLabel(): string {
  const total = shelfBook.value?.chapters.length ?? 0;
  return total > 0 ? `第 ${Math.max(0, shelfChapterIndex.value + 1)} / ${total} 章` : "无章节";
}

async function openKnowledgeIntake(): Promise<void> {
  await openActivity("context");
}

function createProject(): void {
  newProjectName.value = "";
  newProjectGenre.value = "未分类";
  newProjectIdea.value = "";
  createDialogVisible.value = true;
}

function confirmCreateProject(destination: CreateDestination): void {
  const projectName = newProjectName.value.trim() || "我的故事";
  const project: StoryProject = {
    id: uid("project"),
    name: projectName,
    genre: newProjectGenre.value.trim() || "未分类",
    summary: newProjectIdea.value.trim(),
    global_guidance: "",
    chapter_turns: 4,
    writing_style: "",
    polish_writing: true,
    style_example: "",
    style_notes: "",
    style_avoid: "",
    world: [],
    characters: [],
    map: {nodes: [], edges: []},
    chapters: [{id: uid("chapter"), title: "第一章", content: ""}],
    chat: [],
    issues: [],
  };
  projects.value.push(project);
  activeProjectId.value = project.id;
  activeChapterId.value = project.chapters[0].id;
  createDialogVisible.value = false;
  saveProjects();
  markSaved("故事已创建");
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
  const project = activeProject.value;
  const item: WorldCard = {
    id: uid("world"),
    name: "新设定",
    type: "地点",
    summary: "",
    details: "",
    significance: "",
    tags: "",
  };
  project.world.push(item);
  saveProjects();
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
  const project = activeProject.value;
  const card: CharacterCard = {
    id: uid("character"),
    name: "新角色",
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
  project.characters.push(card);
  saveProjects();
}

function setCharacterEditorMode(mode: "simple" | "full"): void {
  characterEditorMode.value = mode;
  localStorage.setItem("rhine-lore-character-mode", mode);
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
  try {
    result = await perform("对话创作", () => {
      if (llmConfigured.value) {
        return llmServerChat(
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
        );
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
    await applyAgentActions(result.actions);
  }
  chatAttachment.value = null;
  saveProjects();
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
    add_world_card: "添加设定",
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
  return preview(record.content ?? record.summary ?? record.text ?? record.markdown ?? "", length);
}

function draftPreview(record: ApiRecord, length = 96): string {
  const proposedNodes = Array.isArray(record.proposed_nodes) ? record.proposed_nodes : [];
  const firstNode = proposedNodes[0] as ApiRecord | undefined;
  return recordPreview(firstNode ?? record, length) || "暂无预览";
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

async function saveMessageAsKnowledge(message: CreativeMessage): Promise<void> {
  const result = await perform("保存资料", () =>
    createManualProposal({
      title: `创作资料：${activeProject.value.name}`,
      node_type: "Note",
      content: [
        `# ${activeProject.value.name} 创作资料`,
        "",
        `来源：对话创作 / ${message.role === "user" ? "用户输入" : "助手回复"}`,
        activeChapter.value ? `当前章节：${activeChapter.value.title}` : "",
        "",
        message.content,
      ].filter(Boolean).join("\n"),
      authority: "experimental",
      tags: ["lore", "chat-extract", activeProject.value.id],
    }),
  );
  if (result) {
    markSaved("已保存为资料草稿，可在资料入库面板确认")
    await refreshReview();
  }
}

async function saveChatAsKnowledge(): Promise<void> {
  if (activeProject.value.chat.length === 0) {
    runState.value = {error: "还没有可保存的对话"};
    return;
  }
  const content = activeProject.value.chat
    .slice(-8)
    .map((message) => `${message.role === "user" ? "我" : "Rhine-Lore"}：\n${message.content}`)
    .join("\n\n");
  const result = await perform("保存对话资料", () =>
    createManualProposal({
      title: `对话资料：${activeProject.value.name}`,
      node_type: "Note",
      content: [
        `# ${activeProject.value.name} 对话资料`,
        "",
        activeChapter.value ? `当前章节：${activeChapter.value.title}` : "",
        "",
        content,
      ].filter(Boolean).join("\n"),
      authority: "experimental",
      tags: ["lore", "conversation", activeProject.value.id],
    }),
  );
  if (result) {
    markSaved("最近对话已保存为资料草稿")
    await refreshReview();
  }
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
}

function proposalTemporaryIds(proposal: ApiRecord): string[] {
  return ((proposal.proposed_nodes ?? []) as ApiRecord[])
    .map((node) => String(node.temporary_id ?? ""))
    .filter(Boolean);
}

async function stageAll(proposal: ApiRecord): Promise<void> {
  const proposalId = String(proposal.proposal_id);
  const temporaryIds = proposalTemporaryIds(proposal);
  if (temporaryIds.length === 0) {
    runState.value = {error: "Proposal 没有可保存的候选节点"};
    return;
  }
  const result = await perform("送去确认", () => stageProposal(proposalId, temporaryIds));
  if (result) {
    markSaved("资料已送去确认");
    await refreshReview();
  }
}

async function approveEntry(entry: ApiRecord): Promise<void> {
  const result = await perform("确认入库", () => approveStaging([String(entry.entry_id)]));
  if (result) {
    markSaved("资料已入库");
    await Promise.allSettled([refreshReview(), refreshNodes()]);
  }
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
  const result = await perform("与故事对话", () =>
    llmServerChat(buildEvolutionChatMessages(text)),
  );
  evolutionChatBusy.value = false;
  const reply = result ? String(result.answer ?? "").trim() : "";
  evolutionChat.value.push({
    id: uid("chat-message"),
    role: "assistant",
    content: reply || "（没有收到回复，请重试或简化问题）",
  });
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
  window.scrollTo({top: 0, behavior: "smooth"});
}

function selectReadingChapter(index: number): void {
  evolutionChapterIndex.value = index;
  window.scrollTo({top: 0, behavior: "smooth"});
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
      <button class="sidebar-close mobile-only" type="button" @click="mobileNavOpen = false">
        ×
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
      <nav class="sidebar-nav">
        <el-button
          v-for="item in activities"
          :key="item.id"
          class="nav-item"
          :class="{
            active: activity === item.id,
            'nav-item-secondary': !isPrimaryActivity(item.id),
            'mobile-parent-active': isStudioChildActivity(item.id),
          }"
          @click="openActivity(item.id); mobileNavOpen = false"
          :title="sidebarCollapsed ? item.label : ''"
        >
          <span class="nav-icon-dot"><GameIcon :name="item.icon" :label="item.label" /></span>
          <span class="nav-label">
            <strong>{{ item.label }}</strong>
            <small>{{ item.description }}</small>
          </span>
        </el-button>
      </nav>
      <div class="sidebar-footer">
        <span class="sidebar-footer-status">
          <span class="status-dot" :class="backendStatusTone" />
          {{ backendStatusLabel }}
        </span>
        <span class="sidebar-footer-meta">
          <i class="sidebar-footer-brand">RL</i>
          v0.1.0
        </span>
      </div>
      <el-button class="collapse-button" title="折叠/展开侧边栏" aria-label="折叠/展开侧边栏" @click="toggleSidebar">
        {{ sidebarCollapsed ? "»" : "«" }}
      </el-button>
    </aside>

    <div v-if="mobileNavOpen" class="sidebar-backdrop" @click="mobileNavOpen = false" />

    <section class="workspace">
      <header class="workspace-topbar">
        <el-button
          class="mobile-menu-button"
          aria-label="打开菜单"
          @click="mobileNavOpen = true"
        >
          ☰
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

      <el-scrollbar class="workspace-main">
        <main class="content-grid">
          <section v-if="activity === 'studio'" class="activity-panel">
            <el-card shadow="never" class="home-hero">
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
            </el-card>

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
              <div class="project-grid" :class="{'project-grid-collapsed': !showAllProjects}">
                <button
                  v-for="(project, index) in projects"
                  :key="project.id"
                  v-show="showAllProjects || index < 3"
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
              <div v-if="projects.length > 3" class="project-fold-toggle">
                <el-button size="small" text @click="showAllProjects = !showAllProjects">
                  {{ showAllProjects ? "收起" : `展开全部（${projects.length} 个故事）` }}
                </el-button>
              </div>
            </el-card>

            <div class="workbench-continuity">
              <div>
                <span>当前进度</span>
                <strong>{{ latestChapter?.title || "还没有章节" }}</strong>
                <small>{{ projectCharacterCount }} 字正文 · {{ activeProject.chat.length }} 条创作对话</small>
              </div>
              <el-space wrap>
                <el-button type="primary" @click="startWriting">继续写</el-button>
                <el-button @click="activity = 'chat'">聊一聊</el-button>
                <el-button @click="activity = 'story'">故事档案</el-button>
              </el-space>
            </div>

            <div class="section-heading">
              <div>
                <span>按需完善</span>
                <small>这些内容不需要一次写完，创作过程中随时补充即可。</small>
              </div>
            </div>
            <div class="guide-grid">
              <button class="guide-card" type="button" @click="activity = 'story'">
                <span>故事档案</span>
                <strong>名称、类型和一句话概要</strong>
                <small>{{ activeProject.summary ? "已填写概要" : "还可以补充概要" }}</small>
              </button>
              <button class="guide-card" type="button" @click="activity = 'world'">
                <span>世界观</span>
                <strong>地点、规则和重要背景</strong>
                <small>{{ activeProject.world.length }} 条设定</small>
              </button>
              <button class="guide-card" type="button" @click="activity = 'characters'">
                <span>角色</span>
                <strong>人物、动机和关系</strong>
                <small>{{ activeProject.characters.length }} 个角色</small>
              </button>
              <button class="guide-card" type="button" @click="activity = 'context'">
                <span>资料库</span>
                <strong>保存和查找创作资料</strong>
                <small>{{ nodes.length }} 条资料</small>
              </button>
              <button class="guide-card" type="button" @click="activity = 'evolution'">
                <span>演化沙盘</span>
                <strong>让小说自己演下去</strong>
                <small>{{ evolutionState ? `已进行 ${evolutionState.turn} 回合` : "回合制沙盘与有限视角小说" }}</small>
              </button>
              <button class="guide-card" type="button" @click="activity = 'map'">
                <span>故事地图</span>
                <strong>摆放地点，画出路线</strong>
                <small>{{ activeProject.map.nodes.length }} 个地点 · {{ activeProject.map.edges.length }} 条连接</small>
              </button>
            </div>

            <div class="knowledge-home-strip">
              <div class="knowledge-home-copy">
                <span>资料流程</span>
                <strong>{{ knowledgePipelineHint }}</strong>
                <small>对话和正文会先变成资料草稿，确认后才会进入可检索知识库。</small>
              </div>
              <div class="knowledge-pipeline compact">
                <div v-for="stat in knowledgePipelineStats" :key="stat.label" class="stat-card" :class="stat.tone">
                  <b>{{ stat.value }}</b>
                  <span>{{ stat.label }}</span>
                </div>
              </div>
              <el-button @click="openKnowledgeIntake">处理资料</el-button>
            </div>

            <div class="ai-channel-strip">
              <div class="ai-channel-copy">
                <span>AI 生成通道</span>
                <strong>{{ llmStatusLabel }}</strong>
                <small>用于演化扩写与对话创作；配置保存在服务端，局域网手机等所有设备共用。</small>
              </div>
              <div class="ai-channel-fields">
                <el-select v-model="llmPreset" size="small" @change="applyLlmProvider">
                  <el-option label="DeepSeek" value="deepseek" />
                  <el-option label="OpenAI" value="openai" />
                  <el-option label="自定义" value="custom" />
                </el-select>
                <el-input v-model="llmModel" size="small" placeholder="模型名称" />
                <el-input
                  v-model="llmApiKey"
                  type="password"
                  show-password
                  size="small"
                  placeholder="已配置则留空保持不变"
                />
              </div>
              <el-space wrap>
                <el-button
                  size="small"
                  :loading="busyAction === '测试模型连接'"
                  @click="testLlmConnection"
                >
                  测试连接
                </el-button>
                <el-button size="small" type="primary" @click="saveLlmConfig">保存</el-button>
              </el-space>
            </div>

          </section>

          <section v-else-if="activity === 'story'" class="activity-panel">
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

          <section v-else-if="activity === 'world'" class="activity-panel">
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
              <div v-if="activeProject.world.length === 0" class="product-empty-state">
                <strong>还没有世界观设定</strong>
                <p>先写地点、势力或规则；地点可以一键放置到地图。</p>
                <el-button type="primary" @click="addLoreItem()">添加第一条设定</el-button>
              </div>
              <div class="world-card-grid">
                <div v-for="item in activeProject.world" :key="item.id" class="character-card world-card">
                  <div class="character-card-head">
                    <div class="character-card-avatar">{{ (item.name || "?").slice(0, 1) }}</div>
                    <div class="character-card-title">
                      <el-input v-model="item.name" class="character-name-input" placeholder="名称，如：雾港" @input="saveProjects" />
                      <el-select v-model="item.type" size="small" style="width: 140px" @change="saveProjects">
                        <el-option v-for="type in worldTypes" :key="type" :label="type" :value="type" />
                      </el-select>
                    </div>
                    <el-button size="small" type="danger" plain @click="removeWorldItem(item)">删除</el-button>
                  </div>
                  <div class="character-card-section">
                    <label>一句话概述</label>
                    <el-input v-model="item.summary" placeholder="这里是什么？它为什么存在？" @input="saveProjects" />
                  </div>
                  <div class="character-card-section">
                    <label>详细描述</label>
                    <el-input v-model="item.details" type="textarea" :rows="4" placeholder="环境、氛围、规则细节……" @input="saveProjects" />
                  </div>
                  <div class="character-card-section">
                    <label>对故事的意义</label>
                    <el-input v-model="item.significance" type="textarea" :rows="2" placeholder="它如何影响角色和剧情？" @input="saveProjects" />
                  </div>
                  <div class="character-card-section">
                    <label>标签</label>
                    <el-input v-model="item.tags" placeholder="例如：港口、海雾、禁行（逗号分隔）" @input="saveProjects" />
                    <div class="preset-chips">
                      <button
                        v-for="tag in worldTagPresets[item.type] || worldTagPresets['其他']"
                        :key="tag"
                        type="button"
                        class="preset-chip"
                        :class="{used: hasTag(item.tags, tag)}"
                        @click="fillWorldTags(item, tag)"
                      >
                        {{ tag }}
                      </button>
                    </div>
                  </div>
                  <div class="character-card-actions">
                    <el-button size="small" @click="submitLoreItem('world', item)">同步到资料库</el-button>
                    <el-button size="small" type="primary" @click="placeWorldOnMap(item)">放置到地图</el-button>
                  </div>
                </div>
              </div>
            </el-card>
          </section>

          <section v-else-if="activity === 'map'" class="activity-panel map-panel">
            <el-card shadow="never" class="map-card">
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
              <div v-if="activeProject.map.nodes.length === 0" class="product-empty-state">
                <strong>地图还是空的</strong>
                <p>点击“添加地点”，或从世界观设定里一键放置地点，然后用“连接”画出路线。</p>
                <el-button type="primary" @click="addMapNode">添加第一个地点</el-button>
              </div>
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
                    <el-radio-group v-model="characterEditorMode" size="small" @change="setCharacterEditorMode">
                      <el-radio-button value="simple">简版</el-radio-button>
                      <el-radio-button value="full">详版</el-radio-button>
                    </el-radio-group>
                    <el-button size="small" type="primary" @click="addCharacter">添加角色</el-button>
                    <el-button size="small" @click="activity = 'evolution'">去演化沙盘</el-button>
                  </el-space>
                </div>
              </template>
              <div v-if="activeProject.characters.length === 0" class="product-empty-state">
                <strong>还没有角色卡</strong>
                <p>从主角开始：写下名字、身份，以及他此刻最想要和最怕失去的东西。</p>
                <el-button type="primary" @click="addCharacter">添加第一张角色卡</el-button>
              </div>
              <div class="character-card-grid">
                <div v-for="card in activeProject.characters" :key="card.id" class="character-card">
                  <div class="character-card-head">
                    <div class="character-card-avatar">{{ (card.name || "?").slice(0, 1) }}</div>
                    <div class="character-card-title">
                      <el-input v-model="card.name" class="character-name-input" placeholder="姓名" @input="saveProjects" />
                      <div class="character-identity-row">
                        <el-input v-model="card.identity" placeholder="身份 / 称号，如：雾港送信人" @input="saveProjects" />
                        <el-select v-model="card.role" size="small" style="width: 130px" @change="saveProjects">
                          <el-option v-for="role in characterRoles" :key="role" :label="role" :value="role" />
                        </el-select>
                      </div>
                    </div>
                    <el-button size="small" type="danger" plain @click="removeCharacter(card)">删除</el-button>
                  </div>

                  <div v-if="characterEditorMode === 'full'" class="character-card-section character-extra-row">
                    <div>
                      <label>年龄</label>
                      <el-input v-model="card.age" placeholder="例如：19 岁" @input="saveProjects" />
                    </div>
                    <div>
                      <label>立场 / 阵营</label>
                      <el-input v-model="card.stance" placeholder="例如：中立、偏向主角、亦正亦邪" @input="saveProjects" />
                    </div>
                  </div>

                  <div class="character-card-section">
                    <label>欲望 / 目标</label>
                    <el-input v-model="card.drive" placeholder="他最想要什么？" @input="saveProjects" />
                    <label>恐惧</label>
                    <el-input v-model="card.fear" placeholder="他最怕失去什么？" @input="saveProjects" />
                  </div>

                  <div class="character-card-section">
                    <label>性格标签</label>
                    <el-input v-model="card.traits" placeholder="例如：谨慎、毒舌、重情义（用逗号分隔）" @input="saveProjects" />
                    <div class="preset-chips">
                      <button
                        v-for="tag in characterTraitPresets"
                        :key="tag"
                        type="button"
                        class="preset-chip"
                        :class="{used: hasTag(card.traits, tag)}"
                        @click="fillCharacterTraits(card, tag)"
                      >
                        {{ tag }}
                      </button>
                    </div>
                  </div>

                  <div v-if="characterEditorMode === 'full'" class="character-card-section character-detail-grid">
                    <div>
                      <label>能力 / 特长</label>
                      <el-input v-model="card.abilities" placeholder="例如：认路、谈判（逗号分隔）" @input="saveProjects" />
                    </div>
                    <div>
                      <label>弱点</label>
                      <el-input v-model="card.weakness" placeholder="例如：怕水、易心软" @input="saveProjects" />
                    </div>
                  </div>

                  <div v-if="characterEditorMode === 'full'" class="character-card-section">
                    <label>秘密（会成为演化伏笔）</label>
                    <el-input v-model="card.secret" placeholder="只有这个角色知道的真相……" @input="saveProjects" />
                  </div>

                  <div v-if="characterEditorMode === 'full'" class="character-card-section">
                    <label>说话风格 / 口头禅</label>
                    <el-input v-model="card.speech" placeholder="例如：总是把话说到一半" @input="saveProjects" />
                  </div>

                  <div class="character-card-section">
                    <label>关系</label>
                    <div v-for="(relation, index) in card.relationships" :key="index" class="relationship-row">
                      <el-input v-model="relation.name" placeholder="对方姓名" size="small" @input="saveProjects" />
                      <el-input v-model="relation.relation" placeholder="关系，如：恋人 / 死敌" size="small" @input="saveProjects" />
                      <el-button size="small" @click="removeRelationship(card, index)">×</el-button>
                    </div>
                    <el-button size="small" @click="addRelationship(card)">添加关系</el-button>
                  </div>

                  <div v-if="characterEditorMode === 'full'" class="character-card-section character-detail-grid">
                    <div>
                      <label>外貌特征</label>
                      <el-input v-model="card.appearance" type="textarea" :rows="3" placeholder="衣着、气质、标志性细节" @input="saveProjects" />
                    </div>
                    <div>
                      <label>背景故事</label>
                      <el-input v-model="card.background" type="textarea" :rows="3" placeholder="他来自哪里，经历过什么" @input="saveProjects" />
                    </div>
                  </div>

                  <div class="character-card-section character-status-row">
                    <div>
                      <label>当前状态</label>
                      <el-select v-model="card.status" size="small" @change="saveProjects">
                        <el-option v-for="status in characterStatusOptions" :key="status" :label="status" :value="status" />
                      </el-select>
                    </div>
                    <div class="character-notes-field">
                      <label>备注</label>
                      <el-input v-model="card.notes" type="textarea" :rows="2" placeholder="其他想记住的事" @input="saveProjects" />
                    </div>
                  </div>

                  <div class="character-card-actions">
                    <el-button size="small" @click="submitLoreItem('characters', card)">同步到资料库</el-button>
                  </div>
                </div>
              </div>
            </el-card>
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
                <div class="ai-chat-title">
                  <span class="ai-chat-logo">RL</span>
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
                    上下文
                    <span v-if="selectedKnowledgeNodes.length + pendingIssueCount > 0" class="ai-chat-badge">
                      {{ selectedKnowledgeNodes.length + pendingIssueCount }}
                    </span>
                  </el-button>
                  <el-radio-group v-model="chatMode" size="small">
                    <el-radio-button value="chat">对话</el-radio-button>
                    <el-radio-button value="adjust">调整正文</el-radio-button>
                  </el-radio-group>
                  <el-button size="small" text @click="saveChatAsKnowledge">存为资料</el-button>
                  <el-button size="small" text @click="clearProjectChat">清空</el-button>
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

              <div ref="chatThreadRef" class="chat-thread ai-chat-thread">
                <div v-if="activeProject.chat.length === 0 && !chatThinking" class="chat-welcome">
                  <span>开始一段创作对话</span>
                  <strong>先说说你想写什么</strong>
                  <p>续写、讨论、修订、导入——都可以直接说，或点下方快捷提示。</p>
                </div>
                <article
                  v-for="message in activeProject.chat"
                  :key="message.id"
                  class="chat-message"
                  :class="message.role"
                >
                  <span class="chat-avatar" :class="message.role">
                    {{ message.role === "assistant" ? "RL" : "我" }}
                  </span>
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
                  <span class="chat-avatar assistant">RL</span>
                  <div class="chat-bubble chat-thinking">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              </div>

              <div class="ai-chat-composer">
                <div v-if="chatMode === 'chat'" class="chat-composer ai-composer">
                  <div class="chat-composer-main">
                    <div v-if="chatAttachment" class="chat-attachment-chip">
                      <span>{{ chatAttachment.name }}</span>
                      <button type="button" @click="removeChatAttachment">×</button>
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
                      发送
                    </el-button>
                    <el-button title="附加文件（TXT / 项目 JSON）" @click="chatAttachInput?.click()">
                      📎
                    </el-button>
                  </div>
                  <div class="chat-starter-row">
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
                      @click="chatSidebarOpen = false"
                    >
                      关闭
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

          <section v-else-if="activity === 'novel'" class="activity-panel novel-panel">
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

            <el-card shadow="never" class="novel-reader-card">
              <template #header>
                <div class="card-header">
                  <span>正文</span>
                  <el-space wrap>
                    <el-button size="small" @click="novelTocVisible = true">目录</el-button>
                    <el-button size="small" @click="novelSettingsVisible = true">阅读设置</el-button>
                    <span class="chapter-meter desktop-only-control">
                      {{ chapterNavigationLabel }} · {{ chapterCharacterCount }} 字
                    </span>
                    <el-button
                      size="small"
                      class="desktop-only-control"
                      :disabled="activeChapterIndex <= 0"
                      @click="openAdjacentChapter(-1)"
                    >
                      上一章
                    </el-button>
                    <el-button
                      size="small"
                      class="desktop-only-control"
                      :disabled="activeChapterIndex < 0 || activeChapterIndex >= activeProject.chapters.length - 1"
                      @click="openAdjacentChapter(1)"
                    >
                      下一章
                    </el-button>
                    <el-button :type="readerMode === 'read' ? 'primary' : 'default'" @click="readerMode = 'read'">
                      阅读
                    </el-button>
                    <el-button :type="readerMode === 'edit' ? 'primary' : 'default'" @click="readerMode = 'edit'">
                      编辑
                    </el-button>
                    <el-input-number
                      v-model="readerFontSize"
                      :min="15"
                      :max="26"
                      size="small"
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
                    <el-button class="desktop-only-control" @click="submitChapterExtract">
                      保存为资料
                    </el-button>
                  </el-space>
                </div>
              </template>

              <div v-if="!activeChapter" class="product-empty-state reader-empty-state">
                <strong>正文还没有开始</strong>
                <p>我们会自动创建“第一章”，你可以直接写，也可以先去对话创作找灵感。</p>
                <el-space wrap>
                  <el-button type="primary" @click="startWriting">创建第一章</el-button>
                  <el-button @click="activity = 'chat'">先聊聊想法</el-button>
                </el-space>
              </div>
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
                  :class="readerThemeClass()"
                  :style="{fontSize: `${readerFontSize}px`, lineHeight: String(readerLineHeight)}"
                >
                  <h2>{{ activeChapter.title }}</h2>
                  <p v-for="(paragraph, index) in activeChapterParagraphs" :key="index">
                    {{ paragraph }}
                  </p>
                  <p v-if="activeChapterParagraphs.length === 0" class="empty-paragraph">这一章还没有正文。</p>
                </div>
                <el-input
                  v-else
                  v-model="activeChapter.content"
                  class="novel-editor"
                  type="textarea"
                  :rows="24"
                  @input="saveProjects"
                />
              </div>
            </el-card>

            <div v-if="activeChapter" class="mobile-chapter-bar">
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

            <el-drawer v-model="novelTocVisible" title="章节目录" size="82%">
              <div class="shelf-toc-list">
                <button
                  v-for="chapter in activeProject.chapters"
                  :key="chapter.id"
                  type="button"
                  class="shelf-toc-item"
                  :class="{active: activeChapter?.id === chapter.id}"
                  @click="novelTocVisible = false; selectChapter(chapter.id)"
                >
                  <strong>{{ chapter.title }}</strong>
                  <small>{{ chapterLength(chapter) }} 字</small>
                </button>
                <div v-if="activeProject.chapters.length === 0" class="product-empty-state compact">
                  <strong>从第一章开始</strong>
                  <el-button type="primary" @click="startWriting">创建并编辑</el-button>
                </div>
              </div>
            </el-drawer>

            <el-drawer
              v-model="novelSettingsVisible"
              title="阅读设置"
              direction="btt"
              size="70%"
            >
              <div class="shelf-settings">
                <label>字号</label>
                <el-slider
                  v-model="readerFontSize"
                  :min="15"
                  :max="28"
                  :step="1"
                  show-input
                  @change="persistReaderSettings"
                />
                <label>行距</label>
                <el-slider
                  v-model="readerLineHeight"
                  :min="1.4"
                  :max="2.6"
                  :step="0.1"
                  show-input
                  @change="persistReaderSettings"
                />
                <label>主题</label>
                <el-radio-group v-model="readerTheme" @change="persistReaderSettings">
                  <el-radio-button value="day">白</el-radio-button>
                  <el-radio-button value="sepia">米黄</el-radio-button>
                  <el-radio-button value="night">夜间</el-radio-button>
                </el-radio-group>
              </div>
            </el-drawer>
          </section>

          <section v-else-if="activity === 'context'" class="activity-panel">
            <div class="knowledge-pipeline">
              <div v-for="stat in knowledgePipelineStats" :key="stat.label" class="stat-card" :class="stat.tone">
                <b>{{ stat.value }}</b>
                <span>{{ stat.label }}</span>
              </div>
            </div>
            <el-row :gutter="14">
              <el-col :xs="24" :lg="8">
                <el-card shadow="never" class="knowledge-create-card">
                  <template #header>
                    <div class="card-header">
                      <span>新增资料草稿</span>
                      <el-button size="small" :disabled="!activeChapter" @click="prefillKnowledgeFromChapter">
                        取当前章节
                      </el-button>
                    </div>
                  </template>
                  <el-form label-position="top">
                    <el-form-item label="标题">
                      <el-input v-model="manualKnowledgeTitle" placeholder="例如：城邦禁令、角色秘密、重要伏笔" />
                    </el-form-item>
                    <el-form-item label="内容">
                      <el-input
                        v-model="manualKnowledgeContent"
                        type="textarea"
                        :rows="9"
                        placeholder="写下需要被记住的设定、事实、约束或素材。"
                      />
                    </el-form-item>
                    <el-form-item label="标签">
                      <el-input v-model="manualKnowledgeTags" placeholder="lore, character, chapter" />
                    </el-form-item>
                    <el-button
                      type="primary"
                      :loading="busyAction === '保存资料草稿'"
                      @click="submitManualKnowledgeDraft"
                    >
                      保存为资料草稿
                    </el-button>
                  </el-form>
                </el-card>
              </el-col>

              <el-col :xs="24" :lg="8">
                <el-card shadow="never" class="knowledge-search-card">
                  <template #header>
                    <div class="card-header">
                      <span>查找资料</span>
                      <el-space>
                        <el-button @click="buildContext">查找</el-button>
                        <el-button @click="generateStoryBible">生成设定文档</el-button>
                      </el-space>
                    </div>
                  </template>
                  <el-form label-position="top">
                    <el-form-item label="想查什么">
                      <el-input v-model="contextQuery" type="textarea" :rows="8" />
                    </el-form-item>
                    <el-form-item label="最多显示几条">
                      <el-input-number v-model="resultLimit" :min="1" :max="30" />
                    </el-form-item>
                  </el-form>
                </el-card>
              </el-col>

              <el-col :xs="24" :lg="8">
                <el-card shadow="never" class="knowledge-review-card">
                  <template #header>
                    <div class="card-header">
                      <span>资料入库</span>
                      <el-button size="small" @click="refreshReview">刷新</el-button>
                    </div>
                  </template>
                  <p class="knowledge-flow-note">草稿需要先送去确认，再入库成为对话可引用的资料。</p>
                  <el-table :data="proposals" height="180" class="knowledge-table">
                    <el-table-column prop="title" label="资料草稿" min-width="140" />
                    <el-table-column label="下一步" width="110">
                      <template #default="{row}">
                        <el-button size="small" @click="stageAll(row)">送去确认</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                  <el-table :data="stagingEntries" height="180" class="advanced-table knowledge-table">
                    <el-table-column prop="title" label="待入库" min-width="140" />
                    <el-table-column label="下一步" width="96">
                      <template #default="{row}">
                        <el-button size="small" type="primary" @click="approveEntry(row)">入库</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-card>
              </el-col>
            </el-row>

            <el-card shadow="never" class="knowledge-library-card">
              <template #header>
                <div class="card-header">
                  <span>已入库资料</span>
                  <el-space wrap>
                    <el-button size="small" @click="refreshNodes">刷新</el-button>
                    <el-button size="small" :disabled="selectedKnowledgeNodes.length === 0" @click="activity = 'chat'">
                      去对话使用
                    </el-button>
                  </el-space>
                </div>
              </template>
              <el-table :data="nodes" height="360" class="knowledge-table">
                <el-table-column label="资料" min-width="220">
                  <template #default="{row}">
                    <div class="node-title-cell">
                      <strong>{{ recordTitle(row) }}</strong>
                      <span>{{ recordPreview(row, 120) }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="node_type" label="类型" width="120" />
                <el-table-column label="对话参考" width="130">
                  <template #default="{row}">
                    <el-button size="small" :type="isKnowledgeSelected(row) ? 'primary' : 'default'" @click="addKnowledgeToChat(row)">
                      {{ isKnowledgeSelected(row) ? "已加入" : "加入" }}
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
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
                  <span class="section-icon"><GameIcon name="book" /></span>
                  <div>
                    <strong>演化小说</strong>
                    <small>{{ evolutionView?.novel.viewpoint_name || "主角" }} 的视角</small>
                  </div>
                </div>
                <div class="reading-toolbar-controls">
                  <el-button size="small" @click="readTocVisible = true">目录</el-button>
                  <el-button size="small" @click="readSettingsVisible = true">阅读设置</el-button>
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
                    :style="{fontSize: `${readerFontSize}px`, lineHeight: String(readerLineHeight)}"
                  >
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

            <el-drawer v-model="readTocVisible" title="章节目录" size="82%">
              <div class="shelf-toc-list">
                <button
                  v-for="chapter in evolutionNovelChapters"
                  :key="chapter.index"
                  type="button"
                  class="shelf-toc-item"
                  :class="{active: evolutionActiveChapter?.index === chapter.index}"
                  @click="readTocVisible = false; selectReadingChapter(chapter.index)"
                >
                  <strong>{{ chapter.title }}</strong>
                  <small>
                    {{
                      chapter.startTurn === chapter.endTurn
                        ? `第${chapter.startTurn}回合`
                        : `第${chapter.startTurn}–${chapter.endTurn}回合`
                    }}
                  </small>
                </button>
              </div>
            </el-drawer>

            <el-drawer
              v-model="readSettingsVisible"
              title="阅读设置"
              direction="btt"
              size="70%"
            >
              <div class="shelf-settings">
                <label>字号</label>
                <el-slider
                  v-model="readerFontSize"
                  :min="15"
                  :max="28"
                  :step="1"
                  show-input
                  @change="persistReaderSettings"
                />
                <label>行距</label>
                <el-slider
                  v-model="readerLineHeight"
                  :min="1.4"
                  :max="2.6"
                  :step="0.1"
                  show-input
                  @change="persistReaderSettings"
                />
                <label>主题</label>
                <el-radio-group v-model="readerTheme" @change="persistReaderSettings">
                  <el-radio-button value="day">白</el-radio-button>
                  <el-radio-button value="sepia">米黄</el-radio-button>
                  <el-radio-button value="night">夜间</el-radio-button>
                </el-radio-group>
              </div>
            </el-drawer>
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
              <div v-if="shelfBooks.length === 0" class="product-empty-state">
                <strong>书架还是空的</strong>
                <p>
                  导入一个 .txt 文件，系统会自动按“第X章 / Chapter”拆分章节；
                  没有章节标题的长文也会自动分节，百万字级小说按章存储、按章加载。
                </p>
                <el-button type="primary" @click="shelfImportInput?.click()">选择 TXT 文件</el-button>
              </div>
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
                  <p class="shelf-card-summary">{{ book.summary || "暂无简介" }}</p>
                  <div class="shelf-card-meta">
                    <span>{{ book.chapter_count }} 章</span>
                    <span>{{ book.total_chars.toLocaleString() }} 字</span>
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
                  <span class="section-icon"><GameIcon name="book" /></span>
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
                    @click="shelfBook = null; shelfBookId = ''; shelfChapter = null; shelfChapterIndex = -1"
                  >
                    返回书架
                  </el-button>
                  <el-button size="small" @click="shelfTocVisible = true">目录</el-button>
                  <el-button size="small" @click="shelfSettingsVisible = true">阅读设置</el-button>
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
                  :style="{fontSize: `${readerFontSize}px`, lineHeight: String(readerLineHeight)}"
                >
                  <h2>{{ shelfChapter.title }}</h2>
                  <p v-for="(paragraph, index) in shelfChapterParagraphs(shelfChapter)" :key="index">
                    {{ paragraph }}
                  </p>
                </article>

                <div class="shelf-ai-panel">
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
                    <el-button size="small" :loading="shelfAnalyzeBusy" @click="runShelfAnalysis">
                      分析全书
                    </el-button>
                  </div>
                  <el-input
                    v-model="shelfGuidance"
                    placeholder="引导 AI，例如：让主角发现旧码头火光，语气保持沉静"
                    clearable
                  />
                  <div v-if="shelfAnalysis" class="shelf-analysis">
                    <div class="shelf-analysis-head">
                      <strong>全书档案</strong>
                      <small v-if="shelfAnalysis.offline">离线提取 · 配置 AI 后可升级</small>
                      <span v-else>AI 分析</span>
                      <span>
                        {{ shelfAnalysis.characters.length }} 角色 ·
                        {{ shelfAnalysis.settings.length }} 设定 ·
                        {{ shelfAnalysis.key_facts.length }} 事实 ·
                        {{ shelfAnalysis.unresolved_threads.length }} 伏笔
                      </span>
                    </div>
                    <template v-if="shelfAnalysis.characters.length">
                      <label>角色</label>
                      <div class="shelf-tags">
                        <span
                          v-for="item in shelfAnalysis.characters.slice(0, 16)"
                          :key="item.name"
                          class="shelf-tag"
                          :title="`${item.role} · ${item.notes}`"
                        >
                          {{ item.name }}
                        </span>
                      </div>
                    </template>
                    <template v-if="shelfAnalysis.settings.length">
                      <label>设定</label>
                      <div class="shelf-tags">
                        <span
                          v-for="item in shelfAnalysis.settings.slice(0, 10)"
                          :key="item.name"
                          class="shelf-tag shelf-tag-blue"
                          :title="`${item.type} · ${item.notes}`"
                        >
                          {{ item.name }}
                        </span>
                      </div>
                    </template>
                    <template v-if="shelfAnalysis.key_facts.length">
                      <label>关键事实</label>
                      <ul>
                        <li v-for="(fact, index) in shelfAnalysis.key_facts.slice(0, 6)" :key="index">
                          {{ fact }}
                        </li>
                      </ul>
                    </template>
                    <template v-if="shelfAnalysis.unresolved_threads.length">
                      <label>待回收伏笔</label>
                      <ul>
                        <li v-for="(thread, index) in shelfAnalysis.unresolved_threads.slice(0, 6)" :key="index">
                          {{ thread }}
                        </li>
                      </ul>
                    </template>
                  </div>
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
                </div>
              </template>

              <el-drawer v-model="shelfTocVisible" title="章节目录" size="82%">
                <div class="shelf-toc-list">
                  <button
                    v-for="chapter in shelfBook.chapters"
                    :key="chapter.id"
                    type="button"
                    class="shelf-toc-item"
                    :class="{active: shelfChapter?.id === chapter.id}"
                    @click="shelfTocVisible = false; loadShelfChapter(chapter.id)"
                  >
                    <strong>{{ chapter.title }}</strong>
                    <small>{{ chapter.char_count.toLocaleString() }} 字</small>
                  </button>
                </div>
              </el-drawer>

              <el-drawer
                v-model="shelfSettingsVisible"
                title="阅读设置"
                direction="btt"
                size="70%"
              >
                <div class="shelf-settings">
                  <label>字号</label>
                  <el-slider
                    v-model="readerFontSize"
                    :min="15"
                    :max="28"
                    :step="1"
                    show-input
                    @change="persistReaderSettings"
                  />
                  <label>行距</label>
                  <el-slider
                    v-model="readerLineHeight"
                    :min="1.4"
                    :max="2.6"
                    :step="0.1"
                    show-input
                    @change="persistReaderSettings"
                  />
                  <label>主题</label>
                  <el-radio-group v-model="readerTheme" @change="persistReaderSettings">
                    <el-radio-button value="day">白</el-radio-button>
                    <el-radio-button value="sepia">米黄</el-radio-button>
                    <el-radio-button value="night">夜间</el-radio-button>
                  </el-radio-group>
                </div>
              </el-drawer>
            </template>
          </section>

          <section v-else-if="activity === 'settings'" class="activity-panel">
            <el-tabs v-model="settingsTab" class="settings-tabs">
              <el-tab-pane label="常用设置" name="basic">
                <el-row :gutter="14">
                  <el-col :xs="24" :lg="12">
                    <el-card shadow="never">
                      <template #header>当前状态</template>
                      <el-descriptions :column="1" border>
                        <el-descriptions-item label="故事">{{ activeProject.name }}</el-descriptions-item>
                        <el-descriptions-item label="本地草稿">已保存在浏览器</el-descriptions-item>
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
                          <el-button size="small" @click="refreshReview">刷新</el-button>
                        </div>
                      </template>
                      <div class="knowledge-pipeline compact">
                        <div v-for="stat in knowledgePipelineStats" :key="stat.label" class="stat-card" :class="stat.tone">
                          <b>{{ stat.value }}</b>
                          <span>{{ stat.label }}</span>
                        </div>
                      </div>
                      <p class="knowledge-flow-note">资料草稿不会直接影响创作，送去确认并入库后才会出现在对话写作参考里。</p>
                      <el-table :data="proposals" height="220" class="knowledge-table">
                        <el-table-column prop="title" label="资料草稿" min-width="160" />
                        <el-table-column label="内容预览" min-width="220">
                          <template #default="{row}">
                            <span class="knowledge-preview">{{ draftPreview(row, 110) }}</span>
                          </template>
                        </el-table-column>
                        <el-table-column label="下一步" width="120">
                          <template #default="{row}">
                            <el-button size="small" @click="stageAll(row)">送去确认</el-button>
                          </template>
                        </el-table-column>
                      </el-table>
                      <el-table :data="stagingEntries" height="220" class="advanced-table knowledge-table">
                        <el-table-column prop="title" label="待入库" min-width="160" />
                        <el-table-column label="内容预览" min-width="220">
                          <template #default="{row}">
                            <span class="knowledge-preview">{{ draftPreview(row, 110) }}</span>
                          </template>
                        </el-table-column>
                        <el-table-column label="下一步" width="110">
                          <template #default="{row}">
                            <el-button size="small" type="primary" @click="approveEntry(row)">入库</el-button>
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
      v-model="createDialogVisible"
      class="create-story-dialog"
      title="开始一个新故事"
      width="min(520px, calc(100vw - 24px))"
    >
      <div class="create-story-intro">
        <strong>先写最确定的部分</strong>
        <span>名称之外都可以稍后再改，创建后会自动准备好第一章。</span>
      </div>
      <el-form label-position="top">
        <el-form-item label="故事名称">
          <el-input v-model="newProjectName" autofocus placeholder="例如：雾港来信" />
        </el-form-item>
        <el-form-item label="故事类型">
          <el-select
            v-model="newProjectGenre"
            allow-create
            default-first-option
            filterable
            placeholder="选择或输入类型"
          >
            <el-option v-for="genre in genreOptions" :key="genre" :label="genre" :value="genre" />
          </el-select>
        </el-form-item>
        <el-form-item label="一句话灵感">
          <el-input
            v-model="newProjectIdea"
            type="textarea"
            :rows="4"
            placeholder="例如：一个只在雨夜送信的人，收到了一封写给自己的信。"
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
  </div>
</template>








