import { useEffect, useState } from "react";
import { fetchProjects } from "./api";
import type { Project } from "./contracts";

export const DIB_PROJECT_CARD_DIRECT_ACTION_ID = "DIB-LIVE-002M-PROJECT-CARD-DIRECT-DIB-ACTION-v1";

function dibProjectUrl(projectId: string): string {
  return `#dib?project_id=${encodeURIComponent(projectId)}`;
}

function openDIBForProject(projectId: string) {
  window.location.hash = dibProjectUrl(projectId);
  window.location.reload();
}

function makeDIBActionButton(project: Project): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "cc-btn cc-btn--ghost cc-btn--sm";
  button.dataset.dibProjectCardAction = DIB_PROJECT_CARD_DIRECT_ACTION_ID;
  button.dataset.projectId = project.project_id;
  button.setAttribute("aria-label", `افتح DIB للمشروع ${project.name}`);
  button.textContent = "افتح DIB";
  button.addEventListener("click", () => openDIBForProject(project.project_id));
  return button;
}

function attachDirectActions(projects: Project[]) {
  const projectRows = Array.from(document.querySelectorAll<HTMLElement>(".cc-card .cc-row"));
  projectRows.slice(0, projects.length).forEach((row, index) => {
    if (row.querySelector("[data-dib-project-card-action]")) return;
    const project = projects[index];
    if (!project?.project_id) return;
    row.appendChild(makeDIBActionButton(project));
  });
}

export function DIBProjectCardDirectActionMount() {
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    let cancelled = false;
    void fetchProjects()
      .then((items) => {
        if (!cancelled) setProjects(items.slice(0, 6));
      })
      .catch(() => {
        if (!cancelled) setProjects([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!projects.length) return;
    attachDirectActions(projects);
    const observer = new MutationObserver(() => attachDirectActions(projects));
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [projects]);

  return null;
}
