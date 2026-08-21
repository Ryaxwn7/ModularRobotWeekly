const state = {
  papers: [],
  filtered: [],
};

const fallbackFigure = "./assets/paper-placeholder.svg";

function normalize(value) {
  return String(value || "").toLowerCase();
}

function formatDate(value) {
  if (!value) return "Unknown date";
  return value;
}

function topicLabel(topic) {
  return topic.replaceAll("_", " ");
}

function isConsensusUrl(value) {
  try {
    const host = new URL(value).hostname.toLowerCase();
    return host === "consensus.app" || host.endsWith(".consensus.app");
  } catch {
    return false;
  }
}

function originalPaperUrl(paper) {
  if (paper.doi) return `https://doi.org/${String(paper.doi).replace(/^https?:\/\/doi\.org\//i, "")}`;
  return [paper.doi_url, paper.url, paper.original_url]
    .find((value) => value && !isConsensusUrl(value)) || "";
}

function renderTopicOptions(papers) {
  const select = document.querySelector("#topicFilter");
  const topics = new Set();
  papers.forEach((paper) => (paper.topics || []).forEach((topic) => topics.add(topic)));
  [...topics].sort().forEach((topic) => {
    const option = document.createElement("option");
    option.value = topic;
    option.textContent = topicLabel(topic);
    select.appendChild(option);
  });
}

function applyFilters() {
  const query = normalize(document.querySelector("#searchInput").value);
  const topic = document.querySelector("#topicFilter").value;
  const sort = document.querySelector("#sortSelect").value;

  state.filtered = state.papers.filter((paper) => {
    const haystack = normalize([
      paper.title,
      paper.summary,
      paper.abstract,
      paper.venue,
      ...(paper.tags || []),
      ...(paper.topics || []),
    ].join(" "));
    const matchesQuery = !query || haystack.includes(query);
    const matchesTopic = !topic || (paper.topics || []).includes(topic);
    return matchesQuery && matchesTopic;
  });

  state.filtered.sort((a, b) => {
    if (sort === "score") return (b.score || 0) - (a.score || 0);
    if (sort === "title") return String(a.title).localeCompare(String(b.title));
    return String(b.published || "").localeCompare(String(a.published || ""));
  });

  renderPapers();
}

function renderPapers() {
  const list = document.querySelector("#paperList");
  const template = document.querySelector("#paperTemplate");
  list.innerHTML = "";

  if (!state.filtered.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "没有符合筛选条件的论文。";
    list.appendChild(empty);
    return;
  }

  state.filtered.forEach((paper) => {
    const node = template.content.cloneNode(true);
    const figure = node.querySelector(".paper-figure");
    const figureLink = node.querySelector(".figure-link");
    const title = node.querySelector(".paper-title");
    const original = node.querySelector(".paper-link");
    const doi = node.querySelector(".doi-link");

    const url = originalPaperUrl(paper);
    figure.src = paper.figure_url || fallbackFigure;
    figure.alt = paper.figure_alt || `论文主图：${paper.title}`;

    node.querySelector(".paper-date").textContent = formatDate(paper.published);
    node.querySelector(".paper-venue").textContent = paper.venue || paper.source || "Unknown venue";
    node.querySelector(".paper-score").textContent = paper.score ? `Score ${paper.score}` : "";
    title.textContent = paper.title;
    if (url) {
      figureLink.href = url;
      title.href = url;
      original.href = url;
    } else {
      figureLink.removeAttribute("href");
      title.removeAttribute("href");
      original.remove();
    }
    node.querySelector(".paper-summary").textContent = paper.summary || paper.abstract || "暂无摘要。";

    const tags = node.querySelector(".paper-tags");
    [...(paper.topics || []), ...(paper.tags || [])].forEach((tag) => {
      const item = document.createElement("span");
      item.className = (paper.topics || []).includes(tag) ? "tag topic" : "tag";
      item.textContent = topicLabel(tag);
      tags.appendChild(item);
    });

    if (paper.doi) {
      doi.href = `https://doi.org/${String(paper.doi).replace(/^https?:\/\/doi\.org\//i, "")}`;
    } else {
      doi.remove();
    }

    list.appendChild(node);
  });
}

async function init() {
  const response = await fetch("./data/papers.json", { cache: "no-store" });
  const data = await response.json();
  state.papers = data.papers || [];
  state.filtered = state.papers.slice();

  document.querySelector("#paperCount").textContent = String(state.papers.length);
  document.querySelector("#reportCount").textContent = String(new Set(state.papers.map((paper) => paper.report_id)).size);
  document.querySelector("#updatedAt").textContent = data.updated_at ? data.updated_at.slice(0, 10) : "-";

  if (data.repository_url) {
    document.querySelector("[data-repo-link]").href = data.repository_url;
  }

  renderTopicOptions(state.papers);
  ["#searchInput", "#topicFilter", "#sortSelect"].forEach((selector) => {
    document.querySelector(selector).addEventListener("input", applyFilters);
  });
  applyFilters();
}

init().catch((error) => {
  document.querySelector("#paperList").innerHTML = `<div class="empty">数据加载失败：${error.message}</div>`;
});
