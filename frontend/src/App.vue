<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from "vue";
import {
  Activity,
  ArrowDownLeft,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCheck,
  ChevronRight,
  CircleHelp,
  Clock3,
  Command,
  FileText,
  Layers3,
  LoaderCircle,
  Plus,
  Radio,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Unplug,
  X,
} from "lucide-vue-next";
import fixtures from "./demo.json";
import { RelayClient } from "./api";
import type { Decision, Incident, Submission } from "./types";

const incidents = ref<Incident[]>(structuredClone(fixtures) as Incident[]);
const selectedId = ref(incidents.value[0]?.id);
const selected = computed(() =>
  incidents.value.find((i) => i.id === selectedId.value),
);
const search = ref(""),
  filter = ref("all"),
  section = ref("inbox");
const filtered = computed(() =>
  incidents.value.filter(
    (i) =>
      `${i.title} ${i.service}`
        .toLowerCase()
        .includes(search.value.toLowerCase()) &&
      (filter.value === "all" || i.severity === filter.value) &&
      (section.value !== "reviewed" || i.status === "reviewed"),
  ),
);
const pending = computed(
  () => incidents.value.filter((i) => i.status !== "reviewed").length,
);
const mode = ref<"demo" | "live">("demo"),
  modal = ref<"submit" | "connect" | "about" | null>(null);
const busy = ref(false),
  error = ref(""),
  token = ref(""),
  note = ref("");
const expanded = ref<string | null>(null);
const form = ref<Submission>({
  title: "",
  description: "",
  service: "",
  severity: "P2",
});
let client: RelayClient | null = null;
let poll: ReturnType<typeof setTimeout> | undefined;
let generation = 0;
let submissionKey = crypto.randomUUID();
let submissionFingerprint = "";
const time = (s: string) =>
  new Date(s).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/London",
  });
const zone = (s: string) =>
  new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/London",
    timeZoneName: "short",
  })
    .formatToParts(new Date(s))
    .find((p) => p.type === "timeZoneName")?.value;
const percent = (n: number) => `${Math.round(n * 100)}%`;
function select(id: string) {
  selectedId.value = id;
  note.value = "";
  expanded.value = null;
  error.value = "";
}
function open(which: typeof modal.value) {
  modal.value = which;
  error.value = "";
}
function demo() {
  generation++;
  clearTimeout(poll);
  client = null;
  mode.value = "demo";
  token.value = "";
  incidents.value = structuredClone(fixtures) as Incident[];
  selectedId.value = incidents.value[0]?.id;
  section.value = "inbox";
  note.value = "";
  error.value = "";
}
async function refresh(currentGeneration: number) {
  const activeClient = client;
  if (!activeClient) return;
  try {
    const result = await activeClient.list();
    if (currentGeneration !== generation) return;
    incidents.value = result;
    error.value = "";
    if (!result.some((i) => i.id === selectedId.value))
      selectedId.value = result[0]?.id;
  } catch (e) {
    if (currentGeneration === generation) error.value = (e as Error).message;
  }
  if (currentGeneration === generation)
    poll = setTimeout(() => refresh(currentGeneration), 3000);
}
async function connect() {
  busy.value = true;
  error.value = "";
  try {
    const next = new RelayClient(token.value.trim());
    const result = await next.list();
    generation++;
    clearTimeout(poll);
    client = next;
    incidents.value = result;
    mode.value = "live";
    selectedId.value = result[0]?.id;
    modal.value = null;
    token.value = "";
    section.value = "inbox";
    poll = setTimeout(() => refresh(generation), 3000);
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
async function submit() {
  if (!client) return;
  busy.value = true;
  error.value = "";
  const fingerprint = JSON.stringify(form.value);
  if (fingerprint !== submissionFingerprint) {
    submissionKey = crypto.randomUUID();
    submissionFingerprint = fingerprint;
  }
  try {
    const result = await client.submit(form.value, submissionKey);
    incidents.value = [
      result,
      ...incidents.value.filter((i) => i.id !== result.id),
    ];
    select(result.id);
    modal.value = null;
    section.value = "inbox";
    form.value = { title: "", description: "", service: "", severity: "P2" };
    submissionFingerprint = "";
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
async function review(decision: Decision) {
  const incident = selected.value;
  if (!incident || incident.status !== "ready") return;
  busy.value = true;
  error.value = "";
  try {
    const updated =
      mode.value === "live" && client
        ? await client.review(incident, decision, note.value)
        : {
            ...incident,
            status: "reviewed" as const,
            version: incident.version + 1,
            review: {
              decision,
              note: note.value,
              at: new Date().toISOString(),
            },
            timeline: [
              ...incident.timeline,
              {
                at: new Date().toISOString(),
                label: `Engineer ${decision} recommendation`,
              },
            ],
          };
    incidents.value = incidents.value.map((i) =>
      i.id === updated.id ? updated : i,
    );
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
let previousFocus: HTMLElement | null = null;
watch(modal, async (value) => {
  if (value) {
    previousFocus = document.activeElement as HTMLElement;
    await nextTick();
    document
      .querySelector<HTMLElement>(
        '[role="dialog"] input, [role="dialog"] .close-button',
      )
      ?.focus();
  } else {
    error.value = "";
    token.value = "";
    previousFocus?.focus();
  }
});
function keyboard(event: KeyboardEvent) {
  if (!modal.value) {
    if (
      event.key === "/" &&
      !(event.target instanceof HTMLInputElement) &&
      !(event.target instanceof HTMLTextAreaElement)
    ) {
      event.preventDefault();
      document.querySelector<HTMLInputElement>(".search input")?.focus();
    }
    return;
  }
  if (event.key === "Escape" && !busy.value) {
    modal.value = null;
    return;
  }
  if (event.key !== "Tab") return;
  const controls = [
    ...document.querySelectorAll<HTMLElement>(
      '[role="dialog"] button:not(:disabled), [role="dialog"] input, [role="dialog"] select, [role="dialog"] textarea',
    ),
  ];
  const first = controls[0],
    last = controls[controls.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last?.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first?.focus();
  }
}
document.addEventListener("keydown", keyboard);
onUnmounted(() => {
  generation++;
  clearTimeout(poll);
  document.removeEventListener("keydown", keyboard);
});
</script>

<template>
  <div class="workspace">
    <aside class="sidebar">
      <a
        href="#"
        class="brand"
        aria-label="Relay home"
        @click.prevent="section = 'inbox'"
        ><span class="brand-mark"><Radio :size="22" /></span>relay<span
          class="brand-dot"
          >.</span
        ></a
      >
      <div class="workspace-name">
        <span class="workspace-avatar">R</span>
        <div>Relay workspace<small>Incident intelligence</small></div>
        <ChevronRight :size="14" />
      </div>
      <div class="nav-label">WORKSPACE</div>
      <nav aria-label="Workspace navigation">
        <button
          :class="{ active: section === 'inbox' }"
          @click="section = 'inbox'"
        >
          <Layers3 :size="18" /> Incident inbox <span>{{ pending }}</span>
        </button>
        <button
          :class="{ active: section === 'reviewed' }"
          @click="section = 'reviewed'"
        >
          <CheckCheck :size="18" /> Reviewed
          <span>{{ incidents.length - pending }}</span>
        </button>
        <button @click="open('about')">
          <FileText :size="18" /> How Relay works <ArrowUpRight :size="14" />
        </button>
      </nav>
      <div class="sidebar-note">
        <div class="mini-wave">
          <span></span><span></span><span></span><span></span><span></span
          ><span></span><span></span>
        </div>
        <h3>A signal. A starting point.</h3>
        <p>AI finds the evidence.<br />You make the call.</p>
        <button @click="open('about')">
          Behind the model <ArrowRight :size="14" />
        </button>
      </div>
      <div class="sidebar-bottom">
        <span class="online-dot"></span
        >{{ mode === "demo" ? "Demo workspace" : "API connected"
        }}<button
          @click="mode === 'demo' ? open('connect') : demo()"
          :aria-label="mode === 'demo' ? 'Connect API' : 'Disconnect API'"
        >
          <Unplug :size="16" />
        </button>
      </div>
      <div class="profile">
        <span class="profile-avatar">{{ mode === "demo" ? "DE" : "EN" }}</span>
        <div>
          {{ mode === "demo" ? "Demo engineer" : "Workspace engineer"
          }}<small>{{
            mode === "demo"
              ? "Sample incidents · local review"
              : "Private review workspace"
          }}</small>
        </div>
      </div>
    </aside>

    <main>
      <header class="topbar">
        <div>
          <span class="breadcrumb">Workspace</span
          ><ChevronRight :size="13" /><span>{{
            section === "reviewed" ? "Reviewed" : "Incident inbox"
          }}</span>
        </div>
        <button class="help-button" @click="open('about')">
          <CircleHelp :size="17" /> About this project
        </button>
      </header>
      <div class="page-heading">
        <div>
          <div class="eyebrow"><span></span> FROM ALERT TO UNDERSTANDING</div>
          <h1>
            {{
              section === "reviewed"
                ? "Decisions, recorded."
                : "Find the signal."
            }}
          </h1>
          <p>
            {{
              section === "reviewed"
                ? "A record of the recommendations your team has reviewed."
                : "A quieter place to make sense of operational incidents."
            }}
          </p>
        </div>
        <button
          class="primary-button"
          @click="open(mode === 'demo' ? 'connect' : 'submit')"
        >
          <Plus :size="17" /> New incident
        </button>
      </div>
      <div class="demo-banner" v-if="mode === 'demo'">
        <span class="demo-label">DEMO</span>
        <p>Sample alerts. Real model output. Reviews stay in this session.</p>
        <button @click="open('connect')">
          Connect your API <ArrowUpRight :size="14" />
        </button>
      </div>
      <div class="live-banner" v-else>
        <span class="online-dot"></span>Live workspace · refreshes every 3
        seconds <button @click="demo()">Return to demo</button>
      </div>
      <div class="error-banner" role="alert" v-if="error && !modal">
        {{ error }}
      </div>
      <div class="overview">
        <div>
          <span class="overview-icon"><Activity :size="18" /></span>
          <p>
            In the workspace<strong
              >{{ String(incidents.length).padStart(2, "0")
              }}<small> incidents</small></strong
            >
          </p>
        </div>
        <div>
          <span class="overview-icon"><Clock3 :size="18" /></span>
          <p>
            Awaiting a decision<strong
              >{{ String(pending).padStart(2, "0")
              }}<small> to review</small></strong
            >
          </p>
        </div>
        <div>
          <span class="overview-icon"><ShieldCheck :size="18" /></span>
          <p>
            Built for human judgement<strong class="text-stat"
              >Evidence first<ArrowDownLeft :size="17"
            /></strong>
          </p>
        </div>
      </div>
      <div class="workbench">
        <section class="inbox" aria-label="Incident list">
          <div class="list-heading">
            <h2>
              {{
                section === "reviewed" ? "Reviewed incidents" : "All incidents"
              }}<span>{{ filtered.length }}</span>
            </h2>
            <SlidersHorizontal :size="16" />
          </div>
          <div class="list-controls">
            <label class="search"
              ><Search :size="15" /><input
                v-model="search"
                placeholder="Search incidents…"
                aria-label="Search incidents"
              /><kbd>/</kbd></label
            ><select v-model="filter" aria-label="Filter priority">
              <option value="all">All priorities</option>
              <option>P1</option>
              <option>P2</option>
              <option>P3</option>
            </select>
          </div>
          <div class="incident-list">
            <button
              v-for="incident in filtered"
              :key="incident.id"
              class="incident-row"
              :class="{ selected: selectedId === incident.id }"
              @click="select(incident.id)"
            >
              <div class="incident-meta">
                <span
                  class="priority"
                  :class="incident.severity.toLowerCase()"
                  >{{ incident.severity }}</span
                ><span>{{ incident.service }}</span
                ><time>{{ time(incident.created_at) }}</time>
              </div>
              <h3>{{ incident.title }}</h3>
              <div class="incident-footer">
                <span
                  :class="{ 'muted-status': incident.status === 'reviewed' }"
                  ><span class="status-dot" :class="incident.status"></span
                  >{{
                    incident.status === "queued"
                      ? "Analysing"
                      : incident.status === "reviewed"
                        ? "Reviewed"
                        : incident.analysis?.abstained
                          ? "Needs investigation"
                          : "Ready to review"
                  }}</span
                ><ChevronRight :size="15" />
              </div>
            </button>
            <div class="empty-list" v-if="!filtered.length">
              <Search :size="23" />
              <p>No incidents here yet.</p>
              <small>{{
                section === "reviewed"
                  ? "Review an incident to see it here."
                  : "Try another search or submit an alert."
              }}</small>
            </div>
          </div>
          <div class="list-footnote">
            <span class="online-dot"></span
            >{{
              mode === "demo"
                ? "Five sample alerts · synthetic data"
                : "Latest 100 incidents · live data"
            }}
          </div>
        </section>
        <section class="detail" v-if="selected" aria-label="Selected incident">
          <div class="detail-topline">
            <span class="mono"
              >INC-{{ selected.id.slice(0, 6).toUpperCase() }}</span
            ><span class="detail-state"
              ><span class="status-dot" :class="selected.status"></span
              >{{
                selected.status === "reviewed"
                  ? "Review recorded"
                  : selected.status === "queued"
                    ? "Queued for analysis"
                    : "Awaiting review"
              }}</span
            >
          </div>
          <h2 class="incident-title">{{ selected.title }}</h2>
          <div class="detail-tags">
            <span class="priority" :class="selected.severity.toLowerCase()"
              >{{ selected.severity }} priority</span
            ><span><Layers3 :size="13" />{{ selected.service }}</span
            ><span
              ><Clock3 :size="13" />{{ time(selected.created_at) }}
              {{ zone(selected.created_at) }}</span
            >
          </div>
          <div class="signal-section">
            <div class="section-label">
              <Activity :size="15" /> THE INCOMING SIGNAL
            </div>
            <p>{{ selected.description }}</p>
          </div>
          <div
            v-if="selected.analysis"
            class="analysis-panel"
            :class="{ abstained: selected.analysis.abstained }"
          >
            <div class="analysis-heading">
              <span class="ai-mark"><Command :size="16" /></span>
              <h3>Relay assessment</h3>
              <span class="model-tag">{{
                selected.analysis.abstained ? "LOW SIGNAL" : "EVIDENCE MATCH"
              }}</span>
            </div>
            <div class="classification">
              <span>{{
                selected.analysis.abstained
                  ? "More context needed"
                  : selected.analysis.category
              }}</span
              ><span class="score" :title="selected.analysis.score_note"
                >{{ percent(selected.analysis.score)
                }}<small>model score</small></span
              >
            </div>
            <p>{{ selected.analysis.summary }}</p>
            <div class="score-track">
              <span :style="{ width: percent(selected.analysis.score) }"></span>
            </div>
            <small class="score-note"
              >Uncalibrated score. A starting point for investigation.</small
            >
          </div>
          <div class="queued-panel" v-else>
            <LoaderCircle :size="24" class="spin" />
            <h3>Waiting for the worker</h3>
            <p>
              Your incident is recorded. The event dispatcher will deliver it
              for analysis.
            </p>
          </div>
          <template v-if="selected.analysis">
            <div class="next-steps" v-if="!selected.analysis.abstained">
              <div class="section-label">
                <ArrowRight :size="15" /> SUGGESTED FIRST CHECKS
              </div>
              <ol>
                <li
                  v-for="(check, index) in selected.analysis.checks"
                  :key="check"
                >
                  <span>{{ String(index + 1).padStart(2, "0") }}</span
                  >{{ check }}
                </li>
              </ol>
              <p class="recommendation">
                {{ selected.analysis.recommendation }}
              </p>
            </div>
            <div class="evidence-section">
              <div class="section-label">
                <FileText :size="15" /> SUPPORTING RUNBOOKS
                <span>{{ selected.analysis.evidence.length }}</span>
              </div>
              <p v-if="!selected.analysis.evidence.length" class="no-evidence">
                No sufficiently similar runbooks. Collect logs and a
                reproducible timeline before making a diagnosis.
              </p>
              <div
                class="evidence"
                v-for="item in selected.analysis.evidence"
                :key="item.id"
              >
                <button
                  :aria-expanded="expanded === item.id"
                  @click="expanded = expanded === item.id ? null : item.id"
                >
                  <span class="document-icon"><FileText :size="16" /></span
                  ><span
                    ><strong>{{ item.title }}</strong
                    ><small
                      >{{ item.id }} · {{ item.owner }} · revised
                      {{ item.revision }}</small
                    ></span
                  ><span class="match"
                    >{{ percent(item.similarity)
                    }}<small>similarity</small></span
                  ><ChevronRight
                    :size="15"
                    :class="{ rotated: expanded === item.id }"
                  />
                </button>
                <div class="evidence-body" v-if="expanded === item.id">
                  <p>{{ item.action }}</p>
                  <ul>
                    <li v-for="check in item.checks" :key="check">
                      {{ check }}
                    </li>
                  </ul>
                </div>
              </div>
            </div>
            <div class="review-section">
              <div class="section-label">
                <ShieldCheck :size="15" /> THE ENGINEER'S CALL
              </div>
              <template v-if="!selected.review"
                ><p>
                  {{
                    selected.analysis.abstained
                      ? "Record whether the recommendation to investigate is useful."
                      : "Is this a useful direction? Record your judgement before acting."
                  }}
                </p>
                <label class="note-label"
                  >Review note <span>optional</span
                  ><textarea
                    v-model="note"
                    maxlength="2000"
                    rows="2"
                    placeholder="What did you find? Add context for the next engineer."
                  />
                </label>
                <div class="review-actions">
                  <button
                    class="accept-button"
                    :disabled="busy"
                    @click="review('accepted')"
                  >
                    <Check :size="15" />{{
                      busy ? "Saving…" : "Accept direction"
                    }}</button
                  ><button
                    class="secondary-button"
                    :disabled="busy"
                    @click="review('rejected')"
                  >
                    Needs a different approach
                  </button>
                </div></template
              >
              <div v-else class="recorded-review">
                <CheckCheck :size="18" />
                <div>
                  <strong>{{
                    selected.review.decision === "accepted"
                      ? "Direction accepted"
                      : "Different approach requested"
                  }}</strong>
                  <p>{{ selected.review.note || "No additional note." }}</p>
                  <small
                    >{{
                      mode === "demo"
                        ? "Recorded in this demo session"
                        : "Saved to the incident record"
                    }}
                    · {{ time(selected.review.at) }}</small
                  >
                </div>
              </div>
            </div>
          </template>
          <div class="timeline">
            <div v-for="(event, index) in selected.timeline" :key="index">
              <span></span><time>{{ time(event.at) }}</time
              >{{ event.label }}
            </div>
          </div>
          <div class="detail-footnote" v-if="selected.analysis">
            <ShieldCheck :size="13" />No automated remediation<span
              >{{ selected.analysis.model_version }} ·
              {{ selected.analysis.training_digest }}</span
            >
          </div>
        </section>
        <section v-else class="no-selection">
          <Radio :size="36" />
          <h2>A little breathing room.</h2>
          <p>
            Select an incident, or connect your API and submit your first alert.
          </p>
        </section>
      </div>
      <footer class="page-footer">
        <span>RELAY / INCIDENT INTELLIGENCE</span
        ><span>Less noise. Better questions.</span>
      </footer>
    </main>
    <div
      class="modal-backdrop"
      v-if="modal"
      @click.self="!busy && (modal = null)"
    >
      <section
        class="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <button
          class="close-button"
          :disabled="busy"
          aria-label="Close dialog"
          @click="modal = null"
        >
          <X :size="20" />
        </button>
        <template v-if="modal === 'connect'"
          ><div class="eyebrow">YOUR WORKSPACE</div>
          <h2 id="modal-title">Connect to Relay.</h2>
          <p>
            The browser calls the API through this site's
            <code>/api</code> proxy. Enter the workspace token from your backend
            environment.
          </p>
          <form @submit.prevent="connect">
            <label
              >Workspace token<input
                v-model="token"
                type="password"
                required
                autocomplete="off"
                placeholder="RELAY_API_TOKEN"
            /></label>
            <p class="fine-print">
              The token stays in memory and is cleared on reload. Run the local
              containers before connecting.
            </p>
            <div class="error-banner" role="alert" v-if="error">
              {{ error }}
            </div>
            <button class="primary-button" :disabled="busy">
              {{ busy ? "Connecting…" : "Connect workspace"
              }}<ArrowRight :size="16" />
            </button></form
        ></template>
        <template v-else-if="modal === 'submit'"
          ><div class="eyebrow">A NEW SIGNAL</div>
          <h2 id="modal-title">What are you seeing?</h2>
          <p>
            Include symptoms, timing and recent changes. Keep credentials and
            personal data out of the incident.
          </p>
          <form @submit.prevent="submit">
            <label
              >Incident title<input
                v-model="form.title"
                required
                minlength="8"
                maxlength="160"
                placeholder="e.g. Checkout latency rising under load"
            /></label>
            <div class="form-row">
              <label
                >Service<input
                  v-model="form.service"
                  required
                  maxlength="80"
                  placeholder="checkout-api" /></label
              ><label
                >Priority<select v-model="form.severity">
                  <option>P1</option>
                  <option>P2</option>
                  <option>P3</option>
                </select></label
              >
            </div>
            <label
              >What happened?<textarea
                v-model="form.description"
                required
                minlength="20"
                maxlength="12000"
                rows="5"
                placeholder="Describe the signal and the evidence you already have…"
              />
            </label>
            <div class="error-banner" role="alert" v-if="error">
              {{ error }}
            </div>
            <button class="primary-button" :disabled="busy">
              {{ busy ? "Submitting…" : "Submit for analysis"
              }}<ArrowRight :size="16" />
            </button></form
        ></template>
        <template v-else
          ><div class="eyebrow">THE REASONING BEHIND RELAY</div>
          <h2 id="modal-title">Evidence before action.</h2>
          <p>
            Relay is an incident triage showcase. A Python TF-IDF classifier
            suggests an incident category; a separate retrieval index ranks six
            versioned runbooks. Low scores, narrow margins or missing evidence
            trigger abstention.
          </p>
          <div class="about-flow">
            <span>Alert</span><ChevronRight :size="15" /><span
              >Durable event</span
            ><ChevronRight :size="15" /><span>Analysis</span
            ><ChevronRight :size="15" /><span>Your review</span>
          </div>
          <p>
            The model is trained on 48 synthetic examples. Its score is
            uncalibrated. It does not generate a root cause or run remediation
            commands.
          </p>
          <p>
            Python / Django REST Framework · Vue / TypeScript · MongoDB · AWS
            EventBridge, SQS and DynamoDB. Celery handles local delivery.
          </p>
          <button class="primary-button" @click="modal = null">
            Back to the workbench<ArrowRight :size="16" /></button
        ></template>
      </section>
    </div>
  </div>
</template>
