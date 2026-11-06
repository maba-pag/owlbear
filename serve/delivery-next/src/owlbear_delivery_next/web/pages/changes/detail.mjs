import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { state, show, several, formsOf, send, starts } from "./state.mjs";
import { toggle, button, hd, text, info, notice, refusal } from "./widgets.mjs";
import {
  questionForm, retryForm, criteriaPanel, checkForm, mergeForm, restartButton, pullbackNote, stopNotice,
} from "./forms.mjs";
import { decisionForm, visualSection, beforeSection, roundRefused } from "./visual.mjs";
import { spendLines, toolLines, planInfo, roundsInfo, stepper } from "./progress.mjs";
import { activityLog, split } from "./activity.mjs";
import { approval, briefInfo } from "./brief.mjs";
import { choose } from "./list.mjs";
import { watcherSection } from "./watcher.mjs";
import { improvementSection } from "./improvement.mjs";
import { detailsOn, detailsSwitch } from "./details.mjs";
import { actionItems } from "./actions.mjs";

function detailHead(d) {
  const back = html`<p-button-pure type="button" icon="arrow-left" class="back" @click=${() => choose(null)}>All
    Changes</p-button-pure>`;
  let intent = nothing;
  if (!d.finished) {
    const body = { intent: d.paused ? "resume" : "pause" }, said = d.paused
      ? "Resumed: Delivery goes on once no question, check or stop holds the Change."
      : "Pause requested: the running step finishes first, then nothing new starts until you resume.";
    const go = async () => {
      if (await send("/intent", body, d) && state.selected === d.key) {
        state.started = { text: said };
        show();
      }
    };
    intent = button(d.paused ? "Resume" : "Pause", go, d.paused ? { icon: "play", ...starts(d) }
      : { variant: "secondary", icon: "pause" });
  }
  const under = [d.brief.title && d.slug, several() && `in ${d.projectName}`].filter(Boolean).join(" \u00b7 ");
  return html`<div class="detail-head">${back}<div>${hd(2, d.brief.title || d.slug, "xl", { tabindex: "-1" })}${under
    ? text(under, { size: "sm", color: "contrast-medium" }) : nothing}</div><div class="row">${detailsSwitch()}${intent}
    </div></div>`;
}

// The tag says the status; the line keeps its stage only where the stage says more than the tag.
function said(line, label) {
  const [stage, rest] = split(line);
  return stage && stage !== label ? line : rest;
}

const PAUSED = /· paused by you/;

export function badge(c) {
  if (c.stopped) return ["error", "Stopped"];
  if (PAUSED.test(c.line)) return ["secondary", "Paused"];
  if (c.actor === "you") return ["warning", "Your turn"];
  if (c.actor === "admin") return ["warning", "Admin"];
  if (c.line.startsWith("Done")) return ["success", "Done"];
  if (c.line.startsWith("Abandoned")) return ["secondary", "Abandoned"];
  return c.actor === "github" ? ["secondary", "GitHub"] : ["info", "Delivery"];
}

// What the owner needs to act always shows; the record behind it shows with the details (detailsOn).
export function detailView(d) {
  const [variant, label] = badge(d), forms = formsOf(d), on = detailsOn();
  const was = state.refused;
  if (was && was.forms !== forms) {  // #914: a refusal whose form went stays on top of its Change until he acts or goes
    state.refused = was.key !== d.key ? null : was.kept ? was
      : was.form && !was.unsure ? { ...was, form: "", kept: true } : null;
  }
  const refusedTop = state.refused && !state.refused.form ? refusal(state.refused.text, state.refused.unsure)
    : nothing;
  const behind = d.pullback?.state === "behind";
  const r = d.visual_round, deciding = r && r.outcome === "ask" && d.question?.options.some((o) => o.id === "fail");
  const amending = (d.amendments?.list ?? []).find((a) => a.state === "proposed");
  const pictures = d.visual ? visualSection(d.key, d.visual, d.before, d.visual_existing_errors, deciding, d.reference,
    amending)
    : d.before ? beforeSection(d.key, d.before, d.reference) : null;
  const unjudged = roundRefused(r, d.visual);
  const approvingNow = d.step === "shape" && d.brief.approved !== d.brief.version;
  let question = nothing;
  if (d.question) {
    question = deciding ? decisionForm(d.question, r, html`${pictures.lines}${pictures.shots}`, d)
      : d.retry ? retryForm(d.question, d.retry, d) : questionForm(d.question, d);
  }
  return html`${detailHead(d)}
    <div class="row status"><p-tag variant=${variant} compact="true">${label}</p-tag>${text(said(d.line, label))}
      ${d.diagnostics?.length ? html`<ul class="diagnostics">${d.diagnostics.map((e) => html`
        <li>Recorded ${new Date(e.at).toLocaleString()}: ${e.reason}</li>`)}</ul>` : nothing}
    </div>
    ${d.now && label !== "Done" ? text(d.now, { size: "sm", color: "contrast-medium" }) : nothing}
    ${refusedTop}
    ${d.settings_fault ? notice("error", "Settings could not be read", d.settings_fault,
      "Delivery assumes nothing from them; Pause and the other controls still work.") : nothing}
    ${label === "Stopped" || d.recovery ? stopNotice(d) : nothing}
    ${behind ? pullbackNote(d.pullback, d) : nothing}
    ${question}
    ${d.merge ? mergeForm(d.merge, d) : nothing}
    ${d.checks.filter((c) => c.waiting).map((c) => checkForm(c, d))}
    ${actionItems(d)}
    ${approvingNow ? approval(d) : nothing}
    ${pictures && !deciding ? info("Before and after", pictures.lines, unjudged,
      toggle("screenshots", `Screenshots (${pictures.count})`, pictures.shots))
      : unjudged !== nothing ? info("Before and after", unjudged) : nothing}
    ${d.owner_criteria.length ? criteriaPanel(d) : nothing}
    ${d.progress ? info("Progress", stepper(d.progress), d.restartable ? restartButton(d) : nothing) : nothing}
    ${d.plan.length || d.plan_versions.versions.length ? planInfo(d) : nothing}
    ${on && d.rounds ? roundsInfo(d.rounds) : nothing}
    ${!approvingNow && (d.brief.outcome || d.criteria.length) ? briefInfo(d) : nothing}
    ${d.pullback && !behind ? pullbackNote(d.pullback, d) : nothing}
    ${on ? watcherSection(d.watcher) : nothing}
    ${improvementSection(d)}
    ${on ? info("Recent activity", activityLog(d.activity)) : nothing}
    ${spendLines(d.spend)}
    ${on ? toolLines(d.tool_use) : nothing}`;
}
