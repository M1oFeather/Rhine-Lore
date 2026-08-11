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
  masked_key: string;
};

export const workspaceIdKey = "rhine-lore-workspace-id";

export let workspaceId = localStorage.getItem(workspaceIdKey) || "story-workspace";

export function setWorkspaceId(nextWorkspaceId: string): void {
  workspaceId = nextWorkspaceId;
  localStorage.setItem(workspaceIdKey, nextWorkspaceId);
}

export async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
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
  notes: string;
};

export type BookAnalysisSetting = {
  name: string;
  type: string;
  notes: string;
};

export type BookAnalysis = {
  characters: BookAnalysisCharacter[];
  settings: BookAnalysisSetting[];
  key_facts: string[];
  unresolved_threads: string[];
  offline?: boolean;
  updated_at?: string;
};

export function listBooks(): Promise<{books: BookMeta[]}> {
  return getJson("/lore-api/books");
}

export function importBook(body: {
  name: string;
  genre?: string;
  summary?: string;
  text: string;
}): Promise<BookDetail> {
  return postJson("/lore-api/books/import", body);
}

export function getBook(bookId: string): Promise<{book: BookDetail}> {
  return getJson(`/lore-api/books/${encodeURIComponent(bookId)}`);
}

export function deleteBook(bookId: string): Promise<{ok: boolean}> {
  return fetch(`/lore-api/books/${encodeURIComponent(bookId)}`, {method: "DELETE"}).then((response) => {
    if (!response.ok) {
      return response.text().then((text) => {
        throw new Error(text);
      });
    }
    return response.json() as Promise<{ok: boolean}>;
  });
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

export function analyzeBook(bookId: string): Promise<{analysis: BookAnalysis; offline: boolean}> {
  return postJson(`/lore-api/books/${encodeURIComponent(bookId)}/analyze`, {});
}

