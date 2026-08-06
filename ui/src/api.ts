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
  world: LoreItem[];
  characters: LoreItem[];
  chapters: Chapter[];
  chat: CreativeMessage[];
};

export type LoreItem = {
  id: string;
  title: string;
  content: string;
};

export type Chapter = {
  id: string;
  title: string;
  content: string;
};

export type CreativeRole = "user" | "assistant";

export type CreativeMessage = {
  id: string;
  role: CreativeRole;
  content: string;
  created_at: string;
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

