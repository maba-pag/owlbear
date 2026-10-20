import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { state, show, several, formsOf, send } from "./state.mjs";
import { toggle, button, hd, text, row, info, notice, refusal } from "./widgets.mjs";
import { questionForm, retryForm, criteriaPanel, checkForm, mergeForm, restartButton, pullbackNote } from "./forms.mjs";
import { decisionForm, visualSection, beforeSection } from "./visual.mjs";
import { spendLines, activityLog, planList, roundsInfo, stepper } from "./progress.mjs";
import { approval, briefInfo } from "./brief.mjs";
import { choose } from "./list.mjs";

function detailHead(d) {
  const back = html`<p-button-pure type="button" icon="arrow-left" class="back" @click=${() => choose(null)}>All
    Changes</p-button-pure>`;
  let intent = nothing;
  if (!/^(Done|Abandoned) /.test(d.line)) {  // a finished Change has nothing left to pause
    const body = { intent: d.paused ? "resume" : "pause" }, said = d.paused
      ? "Resumed: Delivery goes on once no question, check or stop holds the Change."
      : "Pause requested: the running step finishes first, then nothing new starts until you resume.";
    const go = async () => {
      if (await send("/intent", body, d) && state.selected === d.key) {
        state.started = { text: said };
        show();
      }
    };
    intent = button(d.paused ? "Resume" : "Pause", go, d.paused ? { icon: "play" }
      : { variant: "secondary", icon: "pause" });
  }
  return html`<div class="detail-head">${back}<div>${hd(2, d.slug, "xl", { tabindex: "-1" })}${d.brief.title
    ? text(d.brief.title, { color: "contrast-medium" }) : nothing}${several()
    ? text(`in ${d.projectName}`, { size: "xs", color: "contrast-medium" }) : nothing}</div>${intent}</div>`;
}

const PAUSED = /· paused by you/;

export function badge(c) {
  if (/(^|· )stopped:/.test(c.line)) return ["error", "Stopped"];
  if (PAUSED.test(c.line)) return ["secondary", "Paused"];
  if (c.actor === "you") return ["warning", "Your turn"];
  if (c.actor === "admin") return ["warning", "Admin"];
  if (c.line.startsWith("Done")) return ["success", "Done"];
  if (c.line.startsWith("Abandoned")) return ["secondary", "Abandoned"];
  return c.actor === "github" ? ["secondary", "GitHub"] : ["info", "Delivery"];
}

export function detailView(d) {
  const [variant, label] = badge(d), forms = formsOf(d);
  if (state.refused && state.refused.forms !== forms) state.refused = null;
  const refusedTop = state.refused && !state.refused.form ? refusal(state.refused.text) : nothing;
  const behind = d.pullback?.state === "behind";
  const r = d.visual_round, deciding = r && r.outcome === "ask" && d.question?.options.some((o) => o.id === "fail");
  const pictures = d.visual ? visualSection(d.key, d.visual, d.before, d.visual_existing_errors, deciding)
    : d.before ? beforeSection(d.key, d.before) : null;
  const approvingNow = d.step === "shape" && d.brief.approved !== d.brief.version;
  let question = nothing;
  if (d.question) {
    question = deciding ? decisionForm(d.question, r, html`${pictures.lines}${pictures.shots}`, d)
      : d.retry ? retryForm(d.question, d.retry, d) : questionForm(d.question, d);
  }
  return html`${detailHead(d)}
    ${row(html`<p-tag variant=${variant} compact="true">${label}</p-tag>`, text(d.line))}
    ${refusedTop}
    ${label === "Stopped" ? notice("error", "Stopped", `${d.line.replace(/^.*?stopped: /, "")}.`,
      d.action ? `What to do: ${d.action}.` : "") : nothing}
    ${behind ? pullbackNote(d.pullback, d) : nothing}
    ${question}
    ${d.merge ? mergeForm(d.merge, d) : nothing}
    ${d.checks.filter((c) => c.waiting).map((c) => checkForm(c, d))}
    ${approvingNow ? approval(d) : nothing}
    ${pictures && !deciding ? info("Before and after", pictures.lines,
      toggle("screenshots", `Screenshots (${pictures.count})`, pictures.shots)) : nothing}
    ${d.owner_criteria.length ? criteriaPanel(d) : nothing}
    ${d.progress ? info("Progress", stepper(d.progress), d.restartable ? restartButton(d) : nothing) : nothing}
    ${d.plan.length ? info("Plan", planList(d)) : nothing}
    ${d.rounds ? roundsInfo(d.rounds, d) : nothing}
    ${!approvingNow && (d.brief.outcome || d.criteria.length) ? briefInfo(d) : nothing}
    ${d.pullback && !behind ? pullbackNote(d.pullback, d) : nothing}
    ${info("Recent activity", activityLog(d.activity))}
    ${spendLines(d.spend)}`;
}
