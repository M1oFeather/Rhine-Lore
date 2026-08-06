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

