from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.domain.pause_control import build_pause_context


class LinkedInPlaywrightRuntime:
    def __init__(self, profile_dir: Path, artifacts_dir: Path, headless: bool) -> None:
        self.profile_dir = profile_dir
        self.artifacts_dir = artifacts_dir
        self.headless = headless
        self._playwright: Any | None = None
        self._context: Any | None = None
        self._page: Any | None = None

    def open_job(self, job_url: str) -> dict[str, str]:
        page = self._ensure_page(job_url)
        page.goto(job_url, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        screenshot_path, snapshot_path = self.capture("linkedin-prepare")
        if self._requires_auth(page):
            return {
                "status": "paused",
                "summary": "LinkedIn exige autenticacao antes da candidatura.",
                "screenshot_path": screenshot_path,
                "snapshot_path": snapshot_path,
                **build_pause_context("auth_required"),
            }
        return {
            "status": "completed",
            "summary": "Pagina da vaga aberta no LinkedIn com sessao persistente.",
            "screenshot_path": screenshot_path,
            "snapshot_path": snapshot_path,
        }

    def setup_session(self, login_url: str, timeout_seconds: int) -> dict[str, str]:
        page = self._ensure_page(login_url)
        page.goto(login_url, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        if not self._requires_auth(page):
            screenshot_path, snapshot_path = self.capture("linkedin-session-ready")
            return {
                "status": "completed",
                "summary": "Sessao persistente do LinkedIn ja esta pronta.",
                "screenshot_path": screenshot_path,
                "snapshot_path": snapshot_path,
            }

        deadline = timeout_seconds * 1000
        elapsed = 0
        while elapsed < deadline:
            page.wait_for_timeout(2000)
            elapsed += 2000
            if not self._requires_auth(page):
                screenshot_path, snapshot_path = self.capture("linkedin-session-ready")
                return {
                    "status": "completed",
                    "summary": "Login concluido na sessao persistente do LinkedIn.",
                    "screenshot_path": screenshot_path,
                    "snapshot_path": snapshot_path,
                }

        screenshot_path, snapshot_path = self.capture("linkedin-session-timeout")
        return {
            "status": "paused",
            "summary": "A sessao do LinkedIn ainda exige login no perfil persistente do Playwright.",
            "screenshot_path": screenshot_path,
            "snapshot_path": snapshot_path,
            **build_pause_context("session_setup_required"),
        }

    def ensure_easy_apply(self, job_url: str) -> dict[str, str]:
        page = self._ensure_page(job_url)
        page.goto(job_url, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        easy_apply_button = page.get_by_role(
            "button",
            name=re.compile(r"(easy apply|candidatura simplificada)", re.IGNORECASE),
        ).first
        easy_apply_link = page.get_by_role(
            "link",
            name=re.compile(r"(easy apply|candidatura simplificada)", re.IGNORECASE),
        ).first
        easy_apply_href = page.locator('a[href*="/apply/"]').first

        apply_target = easy_apply_button
        if apply_target.count() == 0:
            apply_target = easy_apply_link
        if apply_target.count() == 0:
            apply_target = easy_apply_href
        if apply_target.count() == 0:
            screenshot_path, snapshot_path = self.capture("linkedin-no-easy-apply")
            return {
                "status": "paused",
                "summary": "Botao Easy Apply nao encontrado na vaga.",
                "screenshot_path": screenshot_path,
                "snapshot_path": snapshot_path,
                **build_pause_context("linkedin_easy_apply_unavailable"),
            }
        apply_target.click()
        page.wait_for_timeout(1000)
        screenshot_path, snapshot_path = self.capture("linkedin-modal-open")
        return {
            "status": "completed",
            "summary": "Modal Easy Apply aberto no LinkedIn.",
            "screenshot_path": screenshot_path,
            "snapshot_path": snapshot_path,
        }

    def upload_resume(self, resume_path: Path, job_url: str) -> dict[str, str]:
        page = self._ensure_page(job_url)
        self.ensure_easy_apply(job_url)
        file_input = page.locator('input[type="file"]').first
        if file_input.count() > 0:
            file_input.set_input_files(str(resume_path))
            page.wait_for_timeout(1000)
        screenshot_path, snapshot_path = self.capture("linkedin-upload")
        return {
            "status": "completed",
            "summary": "Upload do curriculo executado quando o campo estava disponivel.",
            "screenshot_path": screenshot_path,
            "snapshot_path": snapshot_path,
        }

    def answer_questions(self, answers: dict[str, str], effective_profile: dict[str, Any], job_url: str) -> dict[str, str]:
        page = self._ensure_page(job_url)
        self.ensure_easy_apply(job_url)
        textareas = page.locator("textarea")
        for index in range(textareas.count()):
            area = textareas.nth(index)
            if area.is_visible() and area.input_value().strip() == "":
                prompt = self._nearest_prompt_text(area)
                area.fill(resolve_prompt_answer(prompt, answers, effective_profile))
        text_inputs = page.locator('input[type="text"]')
        for index in range(text_inputs.count()):
            field = text_inputs.nth(index)
            if field.is_visible() and field.input_value().strip() == "":
                prompt = self._nearest_prompt_text(field)
                candidate = resolve_prompt_answer(prompt, answers, effective_profile)
                if candidate:
                    field.fill(candidate)
        screenshot_path, snapshot_path = self.capture("linkedin-answers")
        return {
            "status": "completed",
            "summary": "Campos textuais simples do LinkedIn foram preenchidos quando possivel.",
            "screenshot_path": screenshot_path,
            "snapshot_path": snapshot_path,
        }

    def advance_or_submit(self, job_url: str, allow_submit: bool) -> dict[str, str]:
        page = self._ensure_page(job_url)
        self.ensure_easy_apply(job_url)

        for _ in range(6):
            submit_button = page.get_by_role(
                "button",
                name=re.compile(r"(submit application|send application|enviar candidatura|enviar inscri..o)", re.IGNORECASE),
            ).first
            if submit_button.count() > 0:
                screenshot_path, snapshot_path = self.capture("linkedin-ready-submit")
                if not allow_submit:
                    return {
                        "status": "paused",
                        "summary": "LinkedIn pronto para envio final; aguardando aprovacao humana.",
                        "screenshot_path": screenshot_path,
                        "snapshot_path": snapshot_path,
                        **build_pause_context("manual_review_before_submit"),
                    }
                submit_button.click()
                page.wait_for_timeout(1500)
                screenshot_path, snapshot_path = self.capture("linkedin-submitted")
                return {
                    "status": "completed",
                    "summary": "Submissao final executada no LinkedIn.",
                    "screenshot_path": screenshot_path,
                    "snapshot_path": snapshot_path,
                }

            next_button = page.get_by_role(
                "button",
                name=re.compile(r"(next|review|avan.ar|revisar)", re.IGNORECASE),
            ).first
            if next_button.count() > 0:
                next_button.click()
                page.wait_for_timeout(1000)
                continue

            required_empty_inputs = page.locator("input[required], textarea[required], select[required]")
            if required_empty_inputs.count() > 0:
                screenshot_path, snapshot_path = self.capture("linkedin-review-required")
                return {
                    "status": "paused",
                    "summary": "Formulario do LinkedIn ainda exige revisao manual.",
                    "screenshot_path": screenshot_path,
                    "snapshot_path": snapshot_path,
                    **build_pause_context("linkedin_form_requires_review"),
                }
            break

        screenshot_path, snapshot_path = self.capture("linkedin-review-required")
        return {
            "status": "paused",
            "summary": "Fluxo Easy Apply nao chegou ao estado de submit automaticamente.",
            "screenshot_path": screenshot_path,
            "snapshot_path": snapshot_path,
            **build_pause_context("linkedin_form_requires_review"),
        }

    def scrape_profile(self, profile_url: str) -> dict[str, Any]:
        page = self._ensure_page(profile_url)
        page.goto(profile_url, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        screenshot_path, snapshot_path = self.capture("linkedin-profile-import")
        if self._requires_auth(page):
            return {
                "status": "paused",
                "summary": "LinkedIn exige autenticacao antes da leitura do perfil.",
                "screenshot_path": screenshot_path,
                "snapshot_path": snapshot_path,
                **build_pause_context("auth_required"),
            }

        data = page.evaluate(
            """() => {
                const clean = (value) => (value || "").replace(/\\s+/g, " ").trim();
                const text = (selectors) => {
                  for (const selector of selectors) {
                    const node = document.querySelector(selector);
                    if (node) {
                      const value = clean(node.textContent);
                      if (value) return value;
                    }
                  }
                  return "";
                };
                const findSectionText = (labels) => {
                  const sections = Array.from(document.querySelectorAll("section"));
                  for (const section of sections) {
                    const heading = clean(section.querySelector("h2, h3, span[aria-hidden='true']")?.textContent);
                    if (labels.some((label) => heading.toLowerCase().includes(label))) {
                      return clean(section.textContent);
                    }
                  }
                  return "";
                };
                const experiences = [];
                const sections = Array.from(document.querySelectorAll("section"));
                for (const section of sections) {
                  const heading = clean(section.querySelector("h2, h3, span[aria-hidden='true']")?.textContent).toLowerCase();
                  if (!heading.includes("experience") && !heading.includes("experi")) continue;
                  const items = Array.from(section.querySelectorAll("li")).slice(0, 6);
                  for (const item of items) {
                    const lines = clean(item.textContent).split(/\\s{2,}|\\n/).map((part) => clean(part)).filter(Boolean);
                    if (lines.length) experiences.push(lines.slice(0, 5));
                  }
                }
                return {
                  name: text(["h1"]),
                  headline: text([
                    ".text-body-medium.break-words",
                    ".pv-text-details__left-panel .text-body-medium",
                    ".ph5 .mt2 .text-body-medium",
                  ]),
                  location: text([
                    ".text-body-small.inline.t-black--light.break-words",
                    ".pv-text-details__left-panel .text-body-small",
                    ".ph5 .mt2 .text-body-small",
                  ]),
                  about: findSectionText(["about", "sobre"]),
                  experiences,
                };
            }"""
        )
        return {
            "status": "completed",
            "summary": "Perfil do LinkedIn lido com a sessao persistente.",
            "screenshot_path": screenshot_path,
            "snapshot_path": snapshot_path,
            "data": data,
        }

    def scrape_job_recommendations(
        self,
        keywords: str,
        location: str,
        limit: int = 10,
        easy_apply_only: bool = True,
    ) -> list[dict[str, str]]:
        query_keywords = re.sub(r"\s+", "%20", keywords.strip())
        query_location = re.sub(r"\s+", "%20", location.strip())
        url = f"https://www.linkedin.com/jobs/search/?keywords={query_keywords}&location={query_location}"
        if easy_apply_only:
            url += "&f_AL=true"
        page = self._ensure_page(url)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        if self._requires_auth(page):
            raise ValueError("LinkedIn exige autenticacao antes da descoberta de vagas.")

        items = page.evaluate(
            f"""() => {{
                const clean = (value) => (value || "").replace(/\\s+/g, " ").trim();
                const dedupeRepeated = (value) => {{
                  const text = clean(value);
                  if (!text) return "";
                  const midpoint = Math.floor(text.length / 2);
                  if (text.length % 2 === 0) {{
                    const left = text.slice(0, midpoint).trim();
                    const right = text.slice(midpoint).trim();
                    if (left && left === right) return left;
                  }}
                  const words = text.split(" ");
                  if (words.length % 2 === 0) {{
                    const half = words.length / 2;
                    const left = words.slice(0, half).join(" ").trim();
                    const right = words.slice(half).join(" ").trim();
                    if (left && left === right) return left;
                  }}
                  return text;
                }};
                const normalizeHref = (value) => {{
                  const href = clean(value).split("?")[0];
                  if (!href) return "";
                  return href.startsWith("http") ? href : `https://www.linkedin.com${{href}}`;
                }};
                const scrubTitle = (value) => dedupeRepeated(value).replace(/\\s+with verification$/i, "").trim();
                const cards = Array.from(document.querySelectorAll("li[data-occludable-job-id], .jobs-search-results__list-item")).slice(0, {max(limit * 3, limit)});
                const jobs = [];
                for (const card of cards) {{
                  const link = card.querySelector("a.job-card-list__title--link, a.job-card-container__link, a[href*='/jobs/view/']");
                  if (!link) continue;
                  const href = normalizeHref(link.getAttribute("href") || link.href || "");
                  const title = scrubTitle(link.getAttribute("aria-label")) || scrubTitle(link.textContent);
                  const company = dedupeRepeated(
                    card.querySelector(".artdeco-entity-lockup__subtitle, .job-card-container__company-name, .job-card-container__primary-description")?.textContent
                  );
                  const location = dedupeRepeated(
                    card.querySelector(".job-card-container__metadata-wrapper li, .job-card-container__metadata-item, .artdeco-entity-lockup__caption")?.textContent
                  );
                  const insight = dedupeRepeated(card.querySelector(".job-card-container__job-insight-text, .job-card-list__insight")?.textContent);
                  const footerItems = Array.from(card.querySelectorAll(".job-card-container__footer-item, .job-card-list__footer-wrapper li"))
                    .map((node) => dedupeRepeated(node.textContent))
                    .filter(Boolean);
                  const descriptionParts = [insight, ...footerItems]
                    .filter(Boolean)
                    .filter((value) => ![title, company, location].some((known) => known && value === known));
                  const description = descriptionParts.join(" | ");
                  const easyApplyText = footerItems.find((value) => /easy apply|candidatura simplificada/i.test(value)) || "";
                  if (!href || !title) continue;
                  if ({str(easy_apply_only).lower()} && !easyApplyText) continue;
                  jobs.push({{
                    url: href,
                    title,
                    company: company || "LinkedIn",
                    location: location || "nao informado",
                    description: description || easyApplyText || "LinkedIn job card captured.",
                  }});
                }}
                return jobs;
            }}"""
        )
        deduped: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            url_value = str(item.get("url", "")).strip()
            if not url_value or url_value in seen:
                continue
            seen.add(url_value)
            deduped.append(
                {
                    "url": url_value,
                    "title": str(item.get("title", "")).strip(),
                    "company": str(item.get("company", "")).strip(),
                    "location": str(item.get("location", "")).strip(),
                    "description": str(item.get("description", "")).strip(),
                }
            )
            if len(deduped) >= limit:
                break
        self.capture("linkedin-job-discovery")
        enriched: list[dict[str, str]] = []
        for item in deduped:
            enriched.append(self.scrape_job_details(item))
        return enriched

    def scrape_job_details(self, job: str | dict[str, str]) -> dict[str, str]:
        if isinstance(job, str):
            payload = {
                "url": job,
                "title": "",
                "company": "",
                "location": "",
                "description": "",
            }
        else:
            payload = job
        return self._enrich_job_card(payload)

    def capture(self, name: str) -> tuple[str, str]:
        page = self._ensure_page()
        checkpoint_dir = self.artifacts_dir / "browser" / "linkedin"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = checkpoint_dir / f"{name}.png"
        snapshot_path = checkpoint_dir / f"{name}.html"
        page.screenshot(path=str(screenshot_path), full_page=True)
        snapshot_path.write_text(page.content(), encoding="utf-8")
        return str(screenshot_path), str(snapshot_path)

    def close(self) -> None:
        if self._context is not None:
            self._context.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._context = None
        self._page = None
        self._playwright = None

    def _ensure_page(self, job_url: str | None = None) -> Any:
        if self._page is not None:
            return self._page
        try:
            from playwright.sync_api import sync_playwright
        except ModuleNotFoundError as exc:  # pragma: no cover - exercised in env without playwright
            raise RuntimeError("playwright_not_installed") from exc

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
        )
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        if job_url:
            self._page.goto(job_url, wait_until="domcontentloaded")
        return self._page

    @staticmethod
    def _nearest_prompt_text(element: Any) -> str:
        try:
            prompt = element.evaluate(
                """(node) => {
                    const clean = (value) => (value || "").replace(/\\s+/g, " ").trim();
                    const label = node.closest("label");
                    if (label) return clean(label.textContent);
                    const group = node.closest("div, fieldset");
                    if (group) {
                      const heading = group.querySelector("label, legend, span, p");
                      if (heading) return clean(heading.textContent);
                    }
                    return clean(node.getAttribute("aria-label")) || clean(node.getAttribute("placeholder"));
                }"""
            )
        except Exception:
            return ""
        return str(prompt or "")

    @staticmethod
    def _requires_auth(page: Any) -> bool:
        current_url = page.url.lower()
        if "/login" in current_url or "linkedin.com/checkpoint" in current_url:
            return True
        try:
            content = page.content().lower()
        except Exception:
            return True
        return "sign in" in content and "linkedin" in content

    def _enrich_job_card(self, job: dict[str, str]) -> dict[str, str]:
        page = self._ensure_page(job["url"])
        page.goto(job["url"], wait_until="domcontentloaded")
        try:
            page.wait_for_function(
                """() => {
                    const clean = (value) => (value || "").replace(/\\s+/g, " ").trim();
                    return Array.from(document.querySelectorAll('[componentkey^="JobDetails_AboutTheJob_"], section, div[data-sdui-component]'))
                      .some((node) => {
                        const heading = clean(node.querySelector("h2, h3")?.textContent);
                        const body = clean(node.querySelector('[data-testid="expandable-text-box"]')?.textContent);
                        return /about the job|sobre a vaga/i.test(heading) && body.length > 40;
                      });
                }""",
                timeout=8000,
            )
        except Exception:
            page.wait_for_timeout(3000)
        if self._requires_auth(page):
            return job
        details = page.evaluate(
            """() => {
                const clean = (value) => (value || "").replace(/\\s+/g, " ").trim();
                const firstNonEmpty = (...values) => values.map(clean).find(Boolean) || "";
                const title = firstNonEmpty(
                  document.querySelector(".job-details-jobs-unified-top-card__job-title, h1")?.textContent,
                  document.querySelector('main [role="main"] h1')?.textContent
                );
                const company = firstNonEmpty(
                  document.querySelector(".job-details-jobs-unified-top-card__company-name a, .job-details-jobs-unified-top-card__company-name")?.textContent,
                  document.querySelector('[aria-label^="Company,"] p a, [aria-label^="Company,"] p')?.textContent
                );
                const locationNode = document.querySelector(
                  ".job-details-jobs-unified-top-card__tertiary-description-container span, .job-details-jobs-unified-top-card__primary-description-container span, .job-details-jobs-unified-top-card__primary-description-container"
                );
                const location = clean(locationNode?.textContent);
                const aboutSection = Array.from(document.querySelectorAll('[componentkey^="JobDetails_AboutTheJob_"], section, div[data-sdui-component]'))
                  .find((node) => /about the job|sobre a vaga/i.test(clean(node.querySelector("h2, h3")?.textContent)));
                const expandableText = aboutSection?.querySelector('[data-testid="expandable-text-box"]');
                const description = firstNonEmpty(
                  expandableText?.textContent,
                  aboutSection?.textContent,
                  document.querySelector(".jobs-description__content .jobs-box__html-content, .jobs-description-content__text, #job-details, .jobs-description")?.textContent
                );
                return { title, company, location, description };
            }"""
        )
        description = str(details.get("description", "")).strip()
        return {
            "url": job["url"],
            "title": str(details.get("title", "")).strip() or job["title"],
            "company": str(details.get("company", "")).strip() or job["company"],
            "location": str(details.get("location", "")).strip() or job["location"],
            "description": description or job["description"],
        }


def resolve_prompt_answer(prompt: str, answers: dict[str, str], effective_profile: dict[str, Any]) -> str:
    normalized = re.sub(r"\s+", " ", (prompt or "").strip().lower())
    focus_stacks = [str(item) for item in effective_profile.get("focus_stacks", [])]
    target_role = str(effective_profile.get("target_role", "")).strip()
    location = str(effective_profile.get("location", "")).strip()
    fit_summary = str(effective_profile.get("fit_summary", "")).strip() or answers.get("fit_summary", "")

    if any(term in normalized for term in ["current location", "localiza", "where are you based", "cidade", "location"]):
        return location or fit_summary or next(iter(answers.values()), "")
    if any(term in normalized for term in ["target role", "desired role", "cargo", "position are you targeting", "job title"]):
        return target_role or fit_summary or next(iter(answers.values()), "")
    if any(term in normalized for term in ["tech stack", "stack", "skills", "tecnologias", "languages", "frameworks"]):
        if focus_stacks:
            return ", ".join(focus_stacks)
    if any(term in normalized for term in ["why", "fit", "summary", "about you", "interested", "experience"]):
        return fit_summary or next(iter(answers.values()), "")

    for question, answer in answers.items():
        if question and question.lower() in normalized:
            return answer

    return fit_summary or next(iter(answers.values()), "I am a strong fit for this role based on hands-on delivery and product execution.")
