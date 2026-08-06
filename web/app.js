const SETTINGS_KEY = "rhine-lore.settings";
const PROJECTS_KEY = "rhine-lore.projects";

const defaultSettings = {
  baseUrl: "http://127.0.0.1:8765",
  workspaceId: "story-workspace",
  displayName: "Story Workspace",
  profileId: "semantic-knowledge-base",
  resultLimit: 8,
};

const starterProject = {
  id: "project-" + Date.now(),
  name: "Untitled Lore",
  genre: "Speculative fiction",
  summary: "",
  updatedAt: new Date().toISOString(),
  world: [],
  characters: [],
  timeline: [],
  outline: [],
  cues: [],
  chapters: [],
  selectedChapterId: null,
};

const state = {
  settings: loadJson(SETTINGS_KEY, defaultSettings),
  projects: loadJson(PROJECTS_KEY, [starterProject]),
  selectedProjectId: null,
  view: "projects",
};

state.selectedProjectId = state.projects[0]?.id ?? null;

const $ = (id) => document.getElementById(id);

function loadJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : structuredClone(fallback);
  } catch {
    return structuredClone(fallback);
  }
}

function saveState() {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(state.settings));
  localStorage.setItem(PROJECTS_KEY, JSON.stringify(state.projects));
}

function selectedProject() {
  return state.projects.find((project) => project.id === state.selectedProjectId) ?? state.projects[0];
}

function selectedChapter(project) {
  if (!project) return null;
  return (
    project.chapters.find((chapter) => chapter.id === project.selectedChapterId) ??
    project.chapters[0] ??
    null
  );
}

function touch(project) {
  project.updatedAt = new Date().toISOString();
}

function uid(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

function output(payload) {
  $("run-output").textContent =
    typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
}

function setStatus(text, kind = "") {
  const badge = $("vault-status");
  badge.textContent = text;
  badge.className = `status-pill ${kind}`.trim();
}

function proxyPath(path) {
  const query = new URLSearchParams({ base_url: state.settings.baseUrl, path });
  return `/vault-proxy?${query.toString()}`;
}

async function vaultFetch(path, options = {}) {
  const init = {
    method: options.method ?? "GET",
    headers: { Accept: "application/json" },
  };
  if (options.body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }

  const response = await fetch(proxyPath(path), init);
  const text = await response.text();
  let payload = text;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = text;
  }
  if (!response.ok) {
    const detail = payload?.detail ?? payload?.error ?? response.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return payload;
}

function bindNavigation() {
  document.querySelectorAll(".activity").forEach((button) => {
    button.addEventListener("click", () => {
      state.view = button.dataset.view;
      document.querySelectorAll(".activity").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
      $(`view-${state.view}`).classList.add("active");
      if (state.view === "review") refreshReview();
      if (state.view === "vault") refreshNodes();
    });
  });
}

function render() {
  const project = selectedProject();
  if (!project) return;

  $("workspace-title").textContent = project.name || "Rhine-Lore";
  $("project-name").value = project.name;
  $("project-genre").value = project.genre;
  $("project-summary").value = project.summary;
  $("metric-world").textContent = project.world.length;
  $("metric-character").textContent = project.characters.length;
  $("metric-chapter").textContent = project.chapters.length;
  $("metric-cue").textContent = project.cues.length;

  $("setting-base-url").value = state.settings.baseUrl;
  $("setting-workspace").value = state.settings.workspaceId;
  $("setting-display-name").value = state.settings.displayName;
  $("setting-profile").value = state.settings.profileId;
  $("setting-limit").value = state.settings.resultLimit;

  renderProjectList();
  renderSimpleList("timeline-list", project.timeline, "time");
  renderSimpleList("outline-list", project.outline, "beat");
  renderSimpleList("cue-list", project.cues, "cue");
  renderEditorList("world-list", project.world, "world", "设定");
  renderEditorList("character-list", project.characters, "character", "角色");
  renderChapters(project);
}

function renderProjectList() {
  const list = $("project-list");
  list.innerHTML = "";
  state.projects.forEach((project) => {
    const button = document.createElement("button");
    button.className = `project-item ${project.id === state.selectedProjectId ? "active" : ""}`;
    button.innerHTML = `<strong>${escapeHtml(project.name)}</strong><small>${escapeHtml(project.genre || "story")}</small>`;
    button.addEventListener("click", () => {
      state.selectedProjectId = project.id;
      render();
    });
    list.appendChild(button);
  });
}

function renderSimpleList(targetId, items, type) {
  const list = $(targetId);
  list.innerHTML = "";
  if (!items.length) {
    list.innerHTML = `<div class="list-item muted">暂无条目</div>`;
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item";
    row.innerHTML = `<strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.text)}</small>`;
    row.addEventListener("dblclick", () => editSimpleItem(type, item.id));
    list.appendChild(row);
  });
}

function renderEditorList(targetId, items, type, label) {
  const list = $(targetId);
  list.innerHTML = "";
  if (!items.length) {
    list.innerHTML = `<div class="list-item muted">暂无${label}</div>`;
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "editor-item";
    row.innerHTML = `
      <input value="${escapeAttr(item.title)}" data-field="title" aria-label="${label}标题">
      <textarea rows="7" data-field="text" aria-label="${label}内容">${escapeHtml(item.text)}</textarea>
      <div class="editor-actions">
        <button class="ghost-button" data-action="submit">提交候选</button>
        <button class="ghost-button" data-action="delete">删除</button>
      </div>
    `;
    row.querySelectorAll("[data-field]").forEach((field) => {
      field.addEventListener("input", () => {
        item[field.dataset.field] = field.value;
        touch(selectedProject());
        saveState();
      });
    });
    row.querySelector('[data-action="submit"]').addEventListener("click", () => submitItem(type, item));
    row.querySelector('[data-action="delete"]').addEventListener("click", () => deleteItem(type, item.id));
    list.appendChild(row);
  });
}

function renderChapters(project) {
  const list = $("chapter-list");
  list.innerHTML = "";
  if (!project.chapters.length) {
    list.innerHTML = `<button class="project-item muted">暂无章节</button>`;
  }
  project.chapters.forEach((chapter) => {
    const button = document.createElement("button");
    button.className = `project-item ${chapter.id === project.selectedChapterId ? "active" : ""}`;
    button.innerHTML = `<strong>${escapeHtml(chapter.title)}</strong><small>${chapter.content.length} chars</small>`;
    button.addEventListener("click", () => {
      project.selectedChapterId = chapter.id;
      saveState();
      renderChapters(project);
    });
    list.appendChild(button);
  });

  const chapter = selectedChapter(project);
  $("chapter-title").value = chapter?.title ?? "";
  $("chapter-content").value = chapter?.content ?? "";
}

function bindProjectInputs() {
  ["project-name", "project-genre", "project-summary"].forEach((id) => {
    $(id).addEventListener("input", () => {
      const project = selectedProject();
      project.name = $("project-name").value;
      project.genre = $("project-genre").value;
      project.summary = $("project-summary").value;
      touch(project);
      saveState();
      renderProjectList();
      $("workspace-title").textContent = project.name || "Rhine-Lore";
    });
  });

  $("new-project").addEventListener("click", () => {
    const project = structuredClone(starterProject);
    project.id = uid("project");
    project.name = "New Lore Project";
    project.updatedAt = new Date().toISOString();
    state.projects.push(project);
    state.selectedProjectId = project.id;
    saveState();
    render();
  });

  $("duplicate-project").addEventListener("click", () => {
    const current = selectedProject();
    const copy = structuredClone(current);
    copy.id = uid("project");
    copy.name = `${copy.name} Copy`;
    copy.updatedAt = new Date().toISOString();
    state.projects.push(copy);
    state.selectedProjectId = copy.id;
    saveState();
    render();
  });

  $("save-all").addEventListener("click", () => {
    saveCurrentChapter();
    saveState();
    output("Saved.");
  });
}

function bindAddButtons() {
  $("add-timeline").addEventListener("click", () => addSimpleItem("time"));
  $("add-outline").addEventListener("click", () => addSimpleItem("beat"));
  $("add-cue").addEventListener("click", () => addSimpleItem("cue"));
  $("add-world").addEventListener("click", () => addEditorItem("world", "New World Note"));
  $("add-character").addEventListener("click", () => addEditorItem("character", "New Character"));
  $("add-chapter").addEventListener("click", addChapter);
}

function addSimpleItem(type) {
  const project = selectedProject();
  const map = { time: "timeline", beat: "outline", cue: "cues" };
  project[map[type]].push({ id: uid(type), title: "New Item", text: "" });
  touch(project);
  saveState();
  render();
}

function editSimpleItem(type, id) {
  const project = selectedProject();
  const map = { time: "timeline", beat: "outline", cue: "cues" };
  const item = project[map[type]].find((entry) => entry.id === id);
  if (!item) return;
  const title = prompt("标题", item.title);
  if (title === null) return;
  const text = prompt("内容", item.text);
  if (text === null) return;
  item.title = title;
  item.text = text;
  touch(project);
  saveState();
  render();
}

function addEditorItem(type, title) {
  const project = selectedProject();
  const collection = type === "world" ? project.world : project.characters;
  collection.push({ id: uid(type), title, text: "" });
  touch(project);
  saveState();
  render();
}

function deleteItem(type, id) {
  const project = selectedProject();
  const collection = type === "world" ? project.world : project.characters;
  const index = collection.findIndex((item) => item.id === id);
  if (index >= 0) collection.splice(index, 1);
  touch(project);
  saveState();
  render();
}

function addChapter() {
  const project = selectedProject();
  const chapter = { id: uid("chapter"), title: "New Chapter", content: "" };
  project.chapters.push(chapter);
  project.selectedChapterId = chapter.id;
  touch(project);
  saveState();
  render();
}

function saveCurrentChapter() {
  const project = selectedProject();
  const chapter = selectedChapter(project);
  if (!chapter) return;
  chapter.title = $("chapter-title").value;
  chapter.content = $("chapter-content").value;
  touch(project);
}

function bindChapterEditor() {
  ["chapter-title", "chapter-content"].forEach((id) => {
    $(id).addEventListener("input", () => {
      saveCurrentChapter();
      saveState();
      renderProjectList();
    });
  });

  $("chapter-context").addEventListener("click", async () => {
    saveCurrentChapter();
    const project = selectedProject();
    const chapter = selectedChapter(project);
    const query = [project.name, chapter?.title, chapter?.content.slice(0, 600)].filter(Boolean).join("\n");
    $("context-query").value = query;
    await buildContext(query);
  });

  $("submit-selection").addEventListener("click", async () => {
    const textarea = $("chapter-content");
    const selected = textarea.value.slice(textarea.selectionStart, textarea.selectionEnd).trim();
    const text = selected || textarea.value.trim();
    const chapter = selectedChapter(selectedProject());
    if (!text) {
      output("No chapter text to submit.");
      return;
    }
    await createManualProposal({
      title: `Chapter Extract: ${chapter?.title || "Untitled"}`,
      node_type: "Note",
      content: text,
      tags: ["lore", "chapter-extract", selectedProject().id],
    });
  });
}

async function submitItem(type, item) {
  const project = selectedProject();
  const markdown = [
    `# ${item.title}`,
    "",
    `Project: ${project.name}`,
    `Type: ${type}`,
    "",
    item.text,
  ].join("\n");
  await createManualProposal({
    title: `${type === "world" ? "World" : "Character"}: ${item.title}`,
    node_type: "Note",
    content: markdown,
    tags: ["lore", type, project.id],
  });
}

async function createManualProposal({ title, node_type, content, tags }) {
  try {
    const payload = await vaultFetch("/api/manual", {
      method: "POST",
      body: {
        workspace_id: state.settings.workspaceId,
        title,
        node_type,
        content,
        authority: "experimental",
        tags,
      },
    });
    setStatus("Proposal 已提交", "ok");
    output(payload);
    await refreshReview();
  } catch (error) {
    setStatus("Proposal 失败", "bad");
    output(error.message);
  }
}

function bindSettings() {
  $("save-settings").addEventListener("click", () => {
    state.settings = readSettingsForm();
    saveState();
    output({ saved: state.settings });
  });

  $("test-vault").addEventListener("click", async () => {
    state.settings = readSettingsForm();
    saveState();
    try {
      const health = await vaultFetch("/api/health");
      setStatus("Vault 已连接", "ok");
      output(health);
    } catch (error) {
      setStatus("Vault 连接失败", "bad");
      output(error.message);
    }
  });

  $("create-workspace").addEventListener("click", async () => {
    state.settings = readSettingsForm();
    saveState();
    try {
      const payload = await vaultFetch("/api/workspaces", {
        method: "POST",
        body: {
          workspace_id: state.settings.workspaceId,
          workspace_type: "project",
          display_name: state.settings.displayName,
        },
      });
      output(payload);
    } catch (error) {
      output(error.message);
    }
  });

  $("list-workspaces").addEventListener("click", async () => {
    try {
      output(await vaultFetch("/api/workspaces"));
    } catch (error) {
      output(error.message);
    }
  });

  $("clear-output").addEventListener("click", () => output(""));
}

function readSettingsForm() {
  return {
    baseUrl: $("setting-base-url").value.trim() || defaultSettings.baseUrl,
    workspaceId: $("setting-workspace").value.trim() || defaultSettings.workspaceId,
    displayName: $("setting-display-name").value.trim() || defaultSettings.displayName,
    profileId: $("setting-profile").value.trim() || defaultSettings.profileId,
    resultLimit: Number($("setting-limit").value || defaultSettings.resultLimit),
  };
}

function bindVaultActions() {
  $("build-context").addEventListener("click", () => buildContext($("context-query").value));
  $("refresh-nodes").addEventListener("click", refreshNodes);
  $("refresh-graph").addEventListener("click", refreshGraph);
  $("generate-doc").addEventListener("click", generateDoc);
  $("refresh-proposals").addEventListener("click", refreshProposals);
  $("refresh-staging").addEventListener("click", refreshStaging);
}

async function buildContext(query) {
  if (!query.trim()) {
    output("Context query is empty.");
    return;
  }
  try {
    const payload = await vaultFetch("/api/context", {
      method: "POST",
      body: queryBody(query),
    });
    setStatus("Context 已构建", "ok");
    renderContext(payload);
    output(payload);
  } catch (error) {
    setStatus("Context 失败", "bad");
    output(error.message);
  }
}

function queryBody(query) {
  return {
    workspace_id: state.settings.workspaceId,
    query,
    profile_id: state.settings.profileId || null,
    result_limit: state.settings.resultLimit,
    relation_depth: 1,
    tags: ["lore"],
    enable_vector: false,
  };
}

function renderContext(bundle) {
  const box = $("context-output");
  const relevant = bundle.relevant_context ?? bundle.relevant ?? [];
  const refs = bundle.supporting_references ?? [];
  const warnings = bundle.warnings ?? [];
  const parts = [];
  parts.push(`<article><strong>Mandatory Constraints</strong><p>${escapeHtml((bundle.mandatory_constraints ?? []).join("\n") || "None")}</p></article>`);
  relevant.slice(0, 8).forEach((item) => {
    const title = item.title ?? item.node_id ?? "Context";
    const content = item.content ?? item.text ?? JSON.stringify(item);
    parts.push(`<article><strong>${escapeHtml(title)}</strong><p>${escapeHtml(content)}</p></article>`);
  });
  if (refs.length) {
    parts.push(`<article><strong>Supporting References</strong><p>${escapeHtml(JSON.stringify(refs, null, 2))}</p></article>`);
  }
  if (warnings.length) {
    parts.push(`<article><strong>Warnings</strong><p>${escapeHtml(warnings.join("\n"))}</p></article>`);
  }
  box.innerHTML = parts.join("");
}

async function refreshNodes() {
  try {
    const nodes = await vaultFetch(`/api/nodes?workspace_id=${encodeURIComponent(state.settings.workspaceId)}`);
    const list = $("node-list");
    list.innerHTML = nodes.length ? "" : `<div class="list-item muted">暂无正式节点</div>`;
    nodes.forEach((node) => {
      const row = document.createElement("div");
      row.className = "list-item";
      row.innerHTML = `
        <strong>${escapeHtml(node.title ?? node.node_id)}</strong>
        <small>${escapeHtml(node.node_type ?? "Node")} · ${escapeHtml(node.authority ?? "")}</small>
        <div class="tag-row">${(node.tags ?? node.tags_json ?? []).toString().split(",").filter(Boolean).map((tag) => `<span class="tag">${escapeHtml(tag.trim())}</span>`).join("")}</div>
      `;
      list.appendChild(row);
    });
    output(nodes);
  } catch (error) {
    output(error.message);
  }
}

async function refreshGraph() {
  try {
    const payload = await vaultFetch(`/api/graph/local?workspace_id=${encodeURIComponent(state.settings.workspaceId)}&depth=1&limit=80`);
    output(payload);
  } catch (error) {
    output(error.message);
  }
}

async function generateDoc() {
  const query = $("context-query").value || selectedProject().name;
  try {
    const payload = await vaultFetch("/api/documents/generate", {
      method: "POST",
      body: {
        ...queryBody(query),
        title: `${selectedProject().name} Story Bible`,
        audience: "writer",
      },
    });
    $("context-output").textContent = payload.markdown ?? JSON.stringify(payload, null, 2);
    output(payload);
  } catch (error) {
    output(error.message);
  }
}

async function refreshReview() {
  await Promise.allSettled([refreshProposals(), refreshStaging()]);
}

async function refreshProposals() {
  try {
    const proposals = await vaultFetch(`/api/proposals?workspace_id=${encodeURIComponent(state.settings.workspaceId)}`);
    const list = $("proposal-list");
    list.innerHTML = proposals.length ? "" : `<div class="list-item muted">暂无 Proposal</div>`;
    proposals.forEach((proposal) => {
      const nodes = proposal.proposed_nodes ?? proposal.nodes ?? [];
      const row = document.createElement("div");
      row.className = "list-item";
      row.innerHTML = `
        <strong>${escapeHtml(proposal.title ?? proposal.proposal_id)}</strong>
        <small>${escapeHtml(proposal.proposal_id)} · ${nodes.length} nodes</small>
        <div class="button-row"><button class="ghost-button">Stage</button></div>
      `;
      row.querySelector("button").addEventListener("click", () => stageProposal(proposal, nodes));
      list.appendChild(row);
    });
    output(proposals);
  } catch (error) {
    output(error.message);
  }
}

async function stageProposal(proposal, nodes) {
  const temporaryIds = nodes.map((node) => node.temporary_id).filter(Boolean);
  if (!temporaryIds.length) {
    output("Proposal has no stageable nodes.");
    return;
  }
  try {
    const payload = await vaultFetch(`/api/proposals/${encodeURIComponent(proposal.proposal_id)}/stage`, {
      method: "POST",
      body: { workspace_id: state.settings.workspaceId, temporary_ids: temporaryIds },
    });
    output(payload);
    await refreshReview();
  } catch (error) {
    output(error.message);
  }
}

async function refreshStaging() {
  try {
    const staging = await vaultFetch(`/api/staging?workspace_id=${encodeURIComponent(state.settings.workspaceId)}&status=pending`);
    const list = $("staging-list");
    list.innerHTML = staging.length ? "" : `<div class="list-item muted">暂无 Staging</div>`;
    staging.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "list-item";
      row.innerHTML = `
        <strong>${escapeHtml(entry.title ?? entry.node_id ?? entry.entry_id)}</strong>
        <small>${escapeHtml(entry.entry_id)} · ${escapeHtml(entry.status ?? "pending")}</small>
        <div class="button-row"><button class="ghost-button">Approve</button></div>
      `;
      row.querySelector("button").addEventListener("click", () => approveStaging(entry.entry_id));
      list.appendChild(row);
    });
    output(staging);
  } catch (error) {
    output(error.message);
  }
}

async function approveStaging(entryId) {
  try {
    const payload = await vaultFetch("/api/staging/approve", {
      method: "POST",
      body: {
        workspace_id: state.settings.workspaceId,
        entry_ids: [entryId],
        actor_id: "user:local",
      },
    });
    output(payload);
    await refreshReview();
    await refreshNodes();
  } catch (error) {
    output(error.message);
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("\n", " ");
}

function init() {
  bindNavigation();
  bindProjectInputs();
  bindAddButtons();
  bindChapterEditor();
  bindSettings();
  bindVaultActions();
  render();
}

init();

