export type ApiRecord = Record<string, any>;

export type WorkspaceRecord = {
  workspace_id: string;
  workspace_type: "project" | "library";
  display_name: string;
};

export type StoryProject = {
  id: string;
  name: string;
  genre: string;
  summary: string;
  source_book_id?: string;
  source_branch_id?: string;
  global_guidance: string;
  chapter_turns: number;
  writing_style: string;
  polish_writing: boolean;
  style_example: string;
  style_notes: string;
  style_avoid: string;
  world: WorldCard[];
  characters: CharacterCard[];
  map: StoryMap;
  chapters: Chapter[];
  chat: CreativeMessage[];
  issues: ManuscriptIssue[];
};

export type LoreItem = {
  id: string;
  title: string;
  content: string;
};

export type CharacterRelationship = {
  name: string;
  relation: string;
};

export type ManuscriptIssue = {
  id: string;
  kind: "冲突" | "误区" | "不一致" | "提醒";
  item: string;
  reason: string;
  suggestion: string;
  status: "待处理" | "已处理" | "忽略";
  created_at: string;
};

export type CharacterCard = {
  id: string;
  name: string;
  identity: string;
  role: string;
  age: string;
  stance: string;
  drive: string;
  fear: string;
  traits: string;
  abilities: string;
  weakness: string;
  secret: string;
  speech: string;
  appearance: string;
  background: string;
  relationships: CharacterRelationship[];
  status: string;
  notes: string;
};

export type WorldCard = {
  id: string;
  name: string;
  type: string;
  summary: string;
  details: string;
  significance: string;
  tags: string;
};

export type StoryMapNode = {
  id: string;
  name: string;
  x: number;
  y: number;
  description: string;
};

export type StoryMapEdge = {
  id: string;
  from: string;
  to: string;
};

export type StoryMap = {
  nodes: StoryMapNode[];
  edges: StoryMapEdge[];
};

export type Chapter = {
  id: string;
  title: string;
  content: string;
};

export type CreativeRole = "user" | "assistant";

export type AgentToolAction = {
  tool: string;
  args: Record<string, unknown>;
  result?: ApiRecord | null;
  pending?: boolean;
};

export type CreativeMessage = {
  id: string;
  role: CreativeRole;
  content: string;
  created_at: string;
  actions?: AgentToolAction[];
};

export type KnowledgeExtractCandidate = {
  candidate_id: string;
  title: string;
  node_type: "Character" | "Location" | "Rule" | "Event" | "Fact" | "Foreshadowing" | "Note";
  content: string;
  authority: string;
  tags: string[];
  source_message_ids: string[];
  confidence: number;
  rationale: string;
};

export type KnowledgeExtractResult = {
  candidates: KnowledgeExtractCandidate[];
  offline: boolean;
  note: string;
};

export type VaultRuntimeConfig = {
  vault_path: string;
  host: string;
  port: number;
  database_path: string;
  python_path: string;
  base_url: string;
};

export type VaultRuntimeStatus = {
  config: VaultRuntimeConfig;
  connected: boolean;
  error?: string;
  health?: ApiRecord;
  manager: {
    managed: boolean;
    running: boolean;
    pid: number | null;
    returncode: number | null;
    base_url: string;
    vault_path: string;
    command: string[];
    mode: "default-core" | "external";
    auto_start: {
      enabled: boolean;
      attempted: boolean;
      error: string;
    };
  };
};

export type VaultWebStatus = {
  vault_path: string;
  installed: boolean;
  installable: boolean;
  url: string;
  web_root: string;
  package_dir: string;
  install_command: string[];
  error?: string;
  install?: ApiRecord;
};

export type EvolutionSettings = {
  chaos: number;
  branch_frequency: number;
  events_per_turn: number;
  auto_resolve: boolean;
};

export type EvolutionCastMember = {
  id: string;
  name: string;
  role: string;
  drive: string;
  fear: string;
  stance: string;
  alive: boolean;
  relations: Record<string, number>;
  identity: string;
  traits: string[];
  background: string;
  location: string;
  secret: string;
  abilities: string[];
  weakness: string;
};

export type EvolutionFaction = {
  id: string;
  name: string;
  attitude: number;
};

export type EvolutionWorld = {
  locations: string[];
  factions: EvolutionFaction[];
  facts: string[];
  tension: number;
};

export type EvolutionThread = {
  id: string;
  title: string;
  kind: string;
  status: string;
  seed_turn: number;
  resolve_turn: number | null;
  participants: string[];
  secret: string;
};

export type EvolutionBranchOption = {
  id: string;
  label: string;
  hint: string;
  effects: ApiRecord;
};

export type EvolutionBranch = {
  question: string;
  options: EvolutionBranchOption[];
};

export type EvolutionEvent = {
  id: string;
  turn: number;
  kind: string;
  title: string;
  summary: string;
  participants: string[];
  witnesses: string[];
  location: string;
  effects: ApiRecord;
  branch: EvolutionBranch | null;
  chosen_option_id: string | null;
  chosen_option_label: string | null;
};

export type EvolutionState = {
  project_id: string;
  project_name: string;
  genre: string;
  seed: number;
  turn: number;
  clock: number;
  cast: EvolutionCastMember[];
  world: EvolutionWorld;
  threads: EvolutionThread[];
  history: EvolutionEvent[];
  pending_branch: EvolutionBranch | null;
  ending: string;
  settings: EvolutionSettings;
  updated_at: string;
  ai_prose: Record<string, string>;
  guidance: string;
  arc: EvolutionArc;
};

export type EvolutionNovelChapter = {
  turn: number;
  title: string;
  paragraphs: string[];
};

export type EvolutionNovel = {
  viewpoint_id: string;
  viewpoint_name: string;
  chapters: EvolutionNovelChapter[];
  hidden_events: number;
};

export type EvolutionPlanBeat = {
  id: string;
  title: string;
  kind: string;
  status: string;
  due_turn: number;
  event_id: string;
};

export type EvolutionArc = {
  act_index: number;
  act_name: string;
  tension_range: number[];
  ending_kind: string;
  beats: EvolutionPlanBeat[];
};

export type EvolutionResult = {
  turn: number;
  advanced: boolean;
  awaiting_branch: boolean;
  branch: EvolutionBranch | null;
  events: EvolutionEvent[];
  prose: string;
  message: string;
  ending: string;
};

export type EvolutionView = {
  state: EvolutionState;
  sandbox: string;
  novel: EvolutionNovel;
  viewpoints: {id: string; name: string}[];
  result: EvolutionResult | null;
  message: string;
  needs_character: boolean;
  suggested_character: {role: string; drive: string} | null;
};

export type ProjectBackupRow = {
  project_id: string;
  name: string;
  updated_at: string;
};

export type LanInfo = {
  addresses: string[];
  port: number;
  local_url: string;
  lan_urls: string[];
};

export type LlmServerConfig = {
  configured: boolean;
  base_url: string;
  model: string;
  preset: string;
  level: "fast" | "balanced" | "deep";
  thinking_enabled: boolean;
  reasoning_effort: "high" | "max" | "";
  masked_key: string;
};

export const workspaceIdKey = "rhine-lore-workspace-id";

export let workspaceId = localStorage.getItem(workspaceIdKey) || "story-workspace";

export function setWorkspaceId(nextWorkspaceId: string): void {
  workspaceId = nextWorkspaceId;
  localStorage.setItem(workspaceIdKey, nextWorkspaceId);
}

const serverBaseKey = "rhine-lore-server-base";
let serverBase = localStorage.getItem(serverBaseKey) || "";

export function setServerBase(next: string): void {
  serverBase = next.trim().replace(/\/+$/, "");
  if (serverBase) {
    localStorage.setItem(serverBaseKey, serverBase);
  } else {
    localStorage.removeItem(serverBaseKey);
  }
}

export function getServerBase(): string {
  return serverBase;
}

export async function pingServerBase(base: string): Promise<{ok: boolean; detail: string}> {
  const clean = base.trim().replace(/\/+$/, "");
  if (!clean) {
    return {ok: false, detail: "服务器地址为空"};
  }
  try {
    const response = await fetch(`${clean}/api/health`, {signal: AbortSignal.timeout(4000)});
    if (!response.ok) {
      return {ok: false, detail: `HTTP ${response.status}`};
    }
    return {ok: true, detail: "连接正常"};
  } catch (error) {
    return {ok: false, detail: error instanceof Error ? error.message : String(error)};
  }
}

export function apiUrl(path: string): string {
  if (!serverBase) {
    return path;
  }
  return `${serverBase}${path}`;
}

export async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(apiUrl(url));
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(apiUrl(url), {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export async function patchJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(apiUrl(url), {
    method: "PATCH",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export function health(): Promise<ApiRecord> {
  return getJson("/api/health");
}

export function listWorkspaces(): Promise<WorkspaceRecord[]> {
  return getJson("/api/workspaces");
}

export function registerWorkspace(body: {
  workspace_id: string;
  workspace_type: "project" | "library";
  display_name?: string;
}): Promise<WorkspaceRecord> {
  return postJson("/api/workspaces", body);
}

export function createManualProposal(body: {
  title: string;
  node_type: string;
  content: string;
  authority: string;
  tags: string[];
}): Promise<ApiRecord> {
  return postJson("/api/manual", {workspace_id: workspaceId, ...body});
}

export function extractConversationKnowledge(body: {
  project: {id: string; name: string; genre: string};
  chapter?: {id: string; title: string} | null;
  messages: Pick<CreativeMessage, "id" | "role" | "content" | "created_at">[];
}): Promise<KnowledgeExtractResult> {
  return postJson("/lore-api/knowledge/extract", body);
}

export function buildContextBundle(body: {
  query: string;
  profile_id?: string;
  result_limit: number;
  tags: string[];
}): Promise<ApiRecord> {
  return postJson("/api/context", {workspace_id: workspaceId, ...body});
}

export function listNodes(): Promise<ApiRecord[]> {
  return getJson(`/api/nodes?workspace_id=${encodeURIComponent(workspaceId)}`);
}

export function listProposals(): Promise<ApiRecord[]> {
  return getJson(`/api/proposals?workspace_id=${encodeURIComponent(workspaceId)}`);
}

export function stageProposal(proposalId: string, temporaryIds: string[]): Promise<ApiRecord[]> {
  return postJson(`/api/proposals/${encodeURIComponent(proposalId)}/stage`, {
    workspace_id: workspaceId,
    temporary_ids: temporaryIds,
  });
}

export function updateProposalNode(
  proposalId: string,
  temporaryId: string,
  patch: {
    node_id?: string;
    title: string;
    node_type: string;
    content: string;
    authority: string;
    tags: string[];
  },
): Promise<ApiRecord> {
  return patchJson(
    `/api/proposals/${encodeURIComponent(proposalId)}/nodes/${encodeURIComponent(temporaryId)}`,
    {workspace_id: workspaceId, patch},
  );
}

export function rejectProposal(proposalId: string): Promise<ApiRecord> {
  return postJson(`/api/proposals/${encodeURIComponent(proposalId)}/reject`, {
    workspace_id: workspaceId,
  });
}

export function listStaging(status = "pending"): Promise<ApiRecord[]> {
  return getJson(
    `/api/staging?workspace_id=${encodeURIComponent(workspaceId)}&status=${encodeURIComponent(status)}`,
  );
}

export function approveStaging(entryIds: string[]): Promise<ApiRecord[]> {
  return postJson("/api/staging/approve", {
    workspace_id: workspaceId,
    entry_ids: entryIds,
  });
}

export function generateKnowledgeDocument(body: {
  query: string;
  profile_id?: string;
  result_limit: number;
  title: string;
  audience: string;
  tags: string[];
}): Promise<ApiRecord> {
  return postJson("/api/documents/generate", {workspace_id: workspaceId, ...body});
}

export function fakeCreativeAnswer(body: {
  query: string;
  profile_id?: string;
  result_limit: number;
  tags: string[];
}): Promise<ApiRecord> {
  return postJson("/api/llm/fake", {workspace_id: workspaceId, ...body});
}
export function getVaultRuntimeStatus(): Promise<VaultRuntimeStatus> {
  return getJson("/lore-api/vault/status");
}

export function connectVaultRuntime(body: {base_url?: string; host?: string; port?: number | string}): Promise<VaultRuntimeStatus> {
  return postJson("/lore-api/vault/connect", body);
}

export function startVaultRuntime(body: Partial<VaultRuntimeConfig>): Promise<VaultRuntimeStatus> {
  return postJson("/lore-api/vault/start", body);
}

export function stopVaultRuntime(): Promise<VaultRuntimeStatus> {
  return postJson("/lore-api/vault/stop", {});
}

export function getVaultWebStatus(): Promise<VaultWebStatus> {
  return getJson("/lore-api/vault/web/status");
}

export function installVaultWeb(body: {vault_path?: string} = {}): Promise<VaultWebStatus> {
  return postJson("/lore-api/vault/web/install", body);
}

export function getEvolutionState(projectId: string, viewpointId = ""): Promise<EvolutionView> {
  const params = new URLSearchParams({project_id: projectId});
  if (viewpointId) {
    params.set("viewpoint_id", viewpointId);
  }
  return getJson(`/lore-api/evolution/state?${params.toString()}`);
}

export function startEvolutionRun(body: {
  project_id: string;
  project_name: string;
  genre: string;
  characters: ApiRecord[];
  world: ApiRecord[];
  map?: StoryMap;
  seed?: number | null;
  settings: Partial<EvolutionSettings>;
}): Promise<EvolutionView> {
  return postJson("/lore-api/evolution/start", body);
}

export function advanceEvolution(body: {
  project_id: string;
  choice_id?: string | null;
  viewpoint_id?: string;
}): Promise<EvolutionView> {
  return postJson("/lore-api/evolution/advance", body);
}

export function resetEvolutionRun(projectId: string): Promise<{ok: boolean}> {
  return postJson("/lore-api/evolution/reset", {project_id: projectId});
}

export function generateEvolutionProseApi(body: {
  project_id: string;
  viewpoint_id?: string;
  global_guidance?: string;
  variation?: string;
  writing_style?: string;
  style_card?: string;
  quality_pass?: boolean;
  llm?: {
    base_url?: string;
    api_key?: string;
    model?: string;
  };
}): Promise<EvolutionView> {
  return postJson("/lore-api/evolution/ai-prose", body);
}

export function guideEvolution(body: {
  project_id: string;
  guidance: string;
  viewpoint_id?: string;
}): Promise<EvolutionView> {
  return postJson("/lore-api/evolution/guide", body);
}

export function addEvolutionCharacter(body: {
  project_id: string;
  viewpoint_id?: string;
  character: ApiRecord;
}): Promise<EvolutionView> {
  return postJson("/lore-api/evolution/add-character", body);
}

export function advanceEvolutionChapter(body: {
  project_id: string;
  viewpoint_id?: string;
  turns?: number;
  global_guidance?: string;
  writing_style?: string;
  style_card?: string;
  quality_pass?: boolean;
  llm?: {
    base_url?: string;
    api_key?: string;
    model?: string;
  };
}): Promise<EvolutionView> {
  return postJson("/lore-api/evolution/advance-chapter", body);
}

export function regenerateEvolutionChapter(body: {
  project_id: string;
  viewpoint_id?: string;
  start_turn: number;
  end_turn: number;
  global_guidance?: string;
  writing_style?: string;
  style_card?: string;
  quality_pass?: boolean;
  llm?: {
    base_url?: string;
    api_key?: string;
    model?: string;
  };
}): Promise<EvolutionView> {
  return postJson("/lore-api/evolution/regenerate-chapter", body);
}

export function backupProject(project: StoryProject): Promise<{ok: boolean}> {
  return postJson("/lore-api/projects/backup", {
    project: {...project, updated_at: new Date().toISOString()},
  });
}

export function listProjectBackups(): Promise<{backups: ProjectBackupRow[]}> {
  return getJson("/lore-api/projects/backups");
}

export function restoreProjectBackup(projectId: string): Promise<{project: StoryProject}> {
  return postJson("/lore-api/projects/restore", {project_id: projectId});
}

export function getLanInfo(): Promise<LanInfo> {
  return getJson("/lore-api/lan");
}

export function getLlmServerConfig(): Promise<LlmServerConfig> {
  return getJson("/lore-api/llm/config");
}

export function saveLlmServerConfig(body: {
  base_url?: string;
  api_key?: string;
  model?: string;
  preset?: string;
  level?: "fast" | "balanced" | "deep";
  clear_key?: boolean;
}): Promise<LlmServerConfig> {
  return postJson("/lore-api/llm/config", body);
}

export function llmServerPing(message = "你好"): Promise<ApiRecord> {
  return postJson("/lore-api/llm/ping", {message});
}

export type ChatAttachment = {
  name: string;
  kind: "txt" | "project" | "knowledge";
  text: string;
};

export type AiChatResult = {
  answer: string;
  model?: string;
  provider?: string;
  actions?: AgentToolAction[];
};

export function llmServerChat(
  messages: LlmChatMessage[],
  attachments: ChatAttachment[] = [],
): Promise<AiChatResult> {
  return postJson("/lore-api/llm/chat", {messages, attachments});
}

export type LlmStreamEvent =
  | {type: "start"; model?: string}
  | {type: "delta"; text: string}
  | {type: "done"; answer: string; actions?: AgentToolAction[]}
  | {type: "error"; message: string};

export async function llmServerChatStream(
  messages: LlmChatMessage[],
  attachments: ChatAttachment[] = [],
  onEvent: (event: LlmStreamEvent) => void,
  signal?: AbortSignal,
): Promise<{answer: string; actions: AgentToolAction[]}> {
  const response = await fetch(apiUrl("/lore-api/llm/chat/stream"), {
    method: "POST",
    headers: {"Content-Type": "application/json", Accept: "text/event-stream"},
    body: JSON.stringify({messages, attachments}),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(await response.text());
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let answer = "";
  let actions: AgentToolAction[] = [];
  for (;;) {
    const {done, value} = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, {stream: true});
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) {
        continue;
      }
      const payload = trimmed.slice(5).trim();
      if (!payload) {
        continue;
      }
      let event: LlmStreamEvent;
      try {
        event = JSON.parse(payload) as LlmStreamEvent;
      } catch {
        continue;
      }
      if (event.type === "delta" && typeof event.text === "string") {
        answer += event.text;
        onEvent(event);
      } else if (event.type === "done") {
        answer = event.answer ?? answer;
        actions = event.actions ?? [];
        onEvent(event);
      } else {
        onEvent(event);
      }
    }
  }
  return {answer, actions};
}

export type LlmChatMessage = {
  role: string;
  content: string;
};

export function llmPing(body: {
  base_url?: string;
  api_key?: string;
  model?: string;
  message?: string;
}): Promise<ApiRecord> {
  return postJson("/api/llm/openai-compatible/ping", {workspace_id: workspaceId, ...body});
}

export function llmChat(body: {
  base_url?: string;
  api_key?: string;
  model?: string;
  messages: LlmChatMessage[];
}): Promise<ApiRecord> {
  return postJson("/api/llm/openai-compatible/chat", {workspace_id: workspaceId, ...body});
}

export type BookMeta = {
  book_id: string;
  name: string;
  genre: string;
  summary: string;
  source_encoding?: string;
  chapter_count: number;
  total_chars: number;
  updated_at: string;
};

export type BookChapterMeta = {
  id: string;
  title: string;
  order: number;
  char_count: number;
};

export type BookDetail = BookMeta & {
  chapters: BookChapterMeta[];
  analysis?: BookAnalysis | null;
};

export type BookChapter = {
  id: string;
  title: string;
  order: number;
  content: string;
  char_count: number;
};

export type AiWriteResult = {
  text: string;
  offline: boolean;
};

export type BookAnalysisCharacter = {
  name: string;
  aliases: string[];
  role: string;
  first_chapter: number;
  last_chapter?: number;
  notes: string;
  source_chapters?: number[];
};

export type BookAnalysisSetting = {
  name: string;
  type: string;
  notes: string;
  source_chapters?: number[];
};

export type BookAnalysisRelation = {
  from: string;
  to: string;
  relation: string;
  kind: string;
  source_chapters?: number[];
};

export type BookAnalysisNote = {
  text: string;
  source_chapters: number[];
};

export type BookAnalysisTimelineItem = {
  title: string;
  summary: string;
  participants: string[];
  source_chapters: number[];
};

export type BookAnalysis = {
  schema_version?: number;
  summary?: string;
  characters: BookAnalysisCharacter[];
  settings: BookAnalysisSetting[];
  relations: BookAnalysisRelation[];
  timeline: BookAnalysisTimelineItem[];
  key_facts: BookAnalysisNote[];
  unresolved_threads: BookAnalysisNote[];
  resolved_threads: BookAnalysisNote[];
  offline?: boolean;
  stale?: boolean;
  updated_at?: string;
  coverage?: {
    chapters_analyzed: number;
    chapters_total: number;
    characters_analyzed: number;
    characters_total: number;
    percent: number;
  };
  analysis_meta?: {
    mode: string;
    fragments: number;
    model_requests: number;
    cache_hits: number;
    schema_version: number;
  };
};

export type BookAnalysisMode = "quick" | "smart" | "deep";

export type BookAnalysisPlan = {
  mode: BookAnalysisMode;
  mode_label: string;
  chapter_count: number;
  total_chars: number;
  fragment_count: number;
  long_chapters: number;
  max_fragment_chars: number;
  merge_calls: number;
  estimated_requests: number;
};

export type BookAnalysisStatus = {
  job_id?: string;
  book_id: string;
  state: "idle" | "queued" | "running" | "paused" | "cancelled" | "failed" | "completed";
  stage: "idle" | "preparing" | "extracting" | "merging" | "finalizing" | "paused" | "completed";
  message: string;
  mode?: BookAnalysisMode;
  offline?: boolean;
  progress: number;
  completed_steps?: number;
  total_steps?: number;
  cached_steps?: number;
  processed_fragments?: number;
  total_fragments?: number;
  current_chapter?: string;
  current_order?: number;
  can_resume: boolean;
  cancel_requested?: boolean;
  error?: string;
  plan?: BookAnalysisPlan;
  result_summary?: {
    characters: number;
    settings: number;
    relations: number;
    timeline: number;
    unresolved_threads: number;
  };
  started_at?: string;
  updated_at?: string;
  completed_at?: string;
};

export function listBooks(): Promise<{books: BookMeta[]}> {
  return getJson("/lore-api/books");
}

export function importBook(body: {
  name: string;
  genre?: string;
  summary?: string;
  text: string;
  source_encoding?: string;
}): Promise<BookDetail> {
  return postJson("/lore-api/books/import", body);
}

export function getBook(bookId: string): Promise<{book: BookDetail}> {
  return getJson(`/lore-api/books/${encodeURIComponent(bookId)}`);
}

export function deleteBook(bookId: string): Promise<{ok: boolean}> {
  return fetch(apiUrl(`/lore-api/books/${encodeURIComponent(bookId)}`), {method: "DELETE"}).then((response) => {
    if (!response.ok) {
      return response.text().then((text) => {
        throw new Error(text);
      });
    }
    return response.json() as Promise<{ok: boolean}>;
  });
}

export async function exportBackupZip(): Promise<{blob: Blob; filename: string}> {
  const response = await fetch(apiUrl("/lore-api/backup/export"), {method: "POST"});
  if (!response.ok) {
    throw new Error(await response.text());
  }
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename =
    match?.[1] || `rhine-lore-backup-${new Date().toISOString().slice(0, 10)}.zip`;
  return {blob: await response.blob(), filename};
}

export async function importBackupZip(file: Blob): Promise<{
  ok: boolean;
  projects: number;
  books: number;
  versions: number;
  knowledge: number;
}> {
  const response = await fetch(apiUrl("/lore-api/backup/import"), {
    method: "POST",
    headers: {"Content-Type": "application/zip"},
    body: file,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<{
    ok: boolean;
    projects: number;
    books: number;
    versions: number;
    knowledge: number;
  }>;
}

export function getBookChapter(bookId: string, chapterId: string): Promise<{chapter: BookChapter}> {
  return getJson(
    `/lore-api/books/${encodeURIComponent(bookId)}/chapters/${encodeURIComponent(chapterId)}`,
  );
}

export function saveBookChapter(
  bookId: string,
  chapterId: string,
  body: {title: string; content: string},
): Promise<{chapter: BookChapter}> {
  return postJson(
    `/lore-api/books/${encodeURIComponent(bookId)}/chapters/${encodeURIComponent(chapterId)}`,
    body,
  );
}

export function aiWriteBook(body: {
  book_id: string;
  chapter_id: string;
  mode: "continue" | "rewrite" | "expand";
  guidance?: string;
  text?: string;
}): Promise<AiWriteResult> {
  return postJson(`/lore-api/books/${encodeURIComponent(body.book_id)}/ai/write`, body);
}

export type VersionRecord = {
  snapshot_id: string;
  kind: "project" | "book";
  entity_id: string;
  message: string;
  created_at: string;
  char_count: number;
};

export type ServerProjectMeta = {
  project_id: string;
  name: string;
  genre: string;
  summary: string;
  chapter_count: number;
  world_count: number;
  character_count: number;
  total_chars: number;
  updated_at: string;
};

export function listServerProjects(): Promise<{projects: ServerProjectMeta[]}> {
  return getJson("/lore-api/projects");
}

export function getServerProject(projectId: string): Promise<{project: StoryProject}> {
  return getJson(`/lore-api/projects/${encodeURIComponent(projectId)}`);
}

export function saveServerProject(project: StoryProject): Promise<{ok: boolean; project_id: string}> {
  return postJson(`/lore-api/projects/${encodeURIComponent(project.id)}`, project);
}

export function executeAgentTool(
  tool: string,
  args: Record<string, unknown>,
): Promise<{ok: boolean; tool: string; result: ApiRecord; snapshot?: VersionRecord | null}> {
  return postJson("/lore-api/agent/execute", {tool, args});
}

export function listVersions(
  kind: "project" | "book",
  entityId: string,
): Promise<{versions: VersionRecord[]}> {
  return getJson(
    `/lore-api/versions?kind=${encodeURIComponent(kind)}&entity_id=${encodeURIComponent(entityId)}`,
  );
}

export function commitVersion(
  kind: "project" | "book",
  entityId: string,
  message: string,
  payload?: unknown,
): Promise<{snapshot: VersionRecord}> {
  return postJson("/lore-api/versions/commit", {
    kind,
    entity_id: entityId,
    message,
    payload,
  });
}

export function restoreVersion(
  kind: "project" | "book",
  entityId: string,
  snapshotId: string,
): Promise<{payload: ApiRecord; snapshot?: VersionRecord | null}> {
  return postJson("/lore-api/versions/restore", {
    kind,
    entity_id: entityId,
    snapshot_id: snapshotId,
  });
}

export function previewBookAnalysis(
  bookId: string,
  mode: BookAnalysisMode,
): Promise<{plan: BookAnalysisPlan}> {
  return getJson(`/lore-api/books/${encodeURIComponent(bookId)}/analysis/preview?mode=${encodeURIComponent(mode)}`);
}

export function getBookAnalysisStatus(bookId: string): Promise<{status: BookAnalysisStatus}> {
  return getJson(`/lore-api/books/${encodeURIComponent(bookId)}/analysis/status`);
}

export function startBookAnalysis(
  bookId: string,
  body: {mode: BookAnalysisMode; force?: boolean},
): Promise<{status: BookAnalysisStatus}> {
  return postJson(`/lore-api/books/${encodeURIComponent(bookId)}/analysis/jobs`, body);
}

export function cancelBookAnalysis(bookId: string): Promise<{status: BookAnalysisStatus}> {
  return postJson(`/lore-api/books/${encodeURIComponent(bookId)}/analysis/cancel`, {});
}

export type BookBranch = {
  branch_id: string;
  book_id: string;
  chapter_id: string;
  chapter_title: string;
  chapter_order: number;
  parent_branch_id: string;
  root_branch_id: string;
  root_offset: number;
  depth: number;
  offset: number;
  progress: number;
  anchor: string;
  title: string;
  kind: "choice" | "relationship" | "clue" | "free";
  guidance: string;
  text: string;
  offline: boolean;
  children_count?: number;
  is_leaf?: boolean;
  created_at: string;
  updated_at: string;
};

export type BookBranchPath = {
  branch: BookBranch;
  lineage: BookBranch[];
  chapter: {id: string; title: string; order: number};
  text: string;
};

export function listBookBranches(
  bookId: string,
  chapterId = "",
): Promise<{branches: BookBranch[]}> {
  const query = chapterId ? `?chapter_id=${encodeURIComponent(chapterId)}` : "";
  return getJson(`/lore-api/books/${encodeURIComponent(bookId)}/branches${query}`);
}

export function createBookBranch(body: {
  book_id: string;
  chapter_id: string;
  offset: number;
  anchor?: string;
  guidance?: string;
  parent_branch_id?: string;
  kind?: BookBranch["kind"];
  title?: string;
}): Promise<{branch: BookBranch; offline: boolean}> {
  return postJson(`/lore-api/books/${encodeURIComponent(body.book_id)}/branches`, body);
}

export function getBookBranchPath(
  bookId: string,
  branchId: string,
): Promise<{path: BookBranchPath}> {
  return getJson(
    `/lore-api/books/${encodeURIComponent(bookId)}/branches/${encodeURIComponent(branchId)}/path`,
  );
}

export function deleteBookBranch(
  bookId: string,
  branchId: string,
): Promise<{ok: boolean; deleted: {branch_id: string; deleted_ids: string[]; count: number}}> {
  return fetch(
    apiUrl(`/lore-api/books/${encodeURIComponent(bookId)}/branches/${encodeURIComponent(branchId)}`),
    {method: "DELETE"},
  ).then(async (response) => {
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  });
}

export function convertBookToProject(
  bookId: string,
  branchId = "",
): Promise<{
  project: StoryProject;
  imported: {chapters: number; characters: number; world: number; map_nodes: number};
}> {
  return postJson(`/lore-api/books/${encodeURIComponent(bookId)}/workbench`, {
    branch_id: branchId,
  });
}

