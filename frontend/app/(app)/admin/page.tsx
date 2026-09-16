"use client";

import {
  Activity,
  AlertTriangle,
  Database,
  Gauge,
  RefreshCw,
  ServerCog,
  ShieldCheck,
  Users,
} from "lucide-react";
import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Reveal } from "@/components/animations/reveal";
import { Button } from "@/components/ui/button";
import {
  type AdminOverview,
  getAdminOverview,
  type ProviderStatus,
} from "@/services/admin.service";

const labels: Record<string, string> = {
  users: "Users",
  workspaces: "Workspaces",
  documents: "Documents",
  websites: "Websites",
  conversations: "Conversations",
  questions: "Questions",
  deep_research: "Deep research",
  live_searches: "Live searches",
  provider_errors: "Provider errors",
  security_events: "Security events",
};
function ProviderCard({
  provider,
  kind,
}: {
  provider: ProviderStatus;
  kind: string;
}) {
  return (
    <article className="provider-status-card">
      <div>
        <span>{kind}</span>
        <h3>{provider.name}</h3>
        <p>{provider.model ?? "Search provider"}</p>
      </div>
      <i className={`health-dot ${provider.health}`}>
        {provider.health.replaceAll("_", " ")}
      </i>
      <dl>
        <div>
          <dt>Requests</dt>
          <dd>{provider.requests ?? 0}</dd>
        </div>
        <div>
          <dt>Errors</dt>
          <dd>{provider.errors ?? 0}</dd>
        </div>
        <div>
          <dt>Avg latency</dt>
          <dd>
            {provider.average_latency_ms
              ? `${Math.round(provider.average_latency_ms)} ms`
              : "—"}
          </dd>
        </div>
        <div>
          <dt>Daily quota</dt>
          <dd>
            {provider.daily_quota
              ? `${provider.daily_requests ?? 0}/${provider.daily_quota}`
              : "Unlimited"}
          </dd>
        </div>
      </dl>
    </article>
  );
}
export default function AdminPage() {
  const [data, setData] = useState<AdminOverview | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const load = () => {
    setLoading(true);
    setError("");
    void getAdminOverview()
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);
  return (
    <div className="admin-page">
      <Reveal>
        <header className="page-heading">
          <div>
            <span className="page-kicker">PRIVACY-SAFE OPERATIONS</span>
            <h1>System intelligence</h1>
            <p>
              Operational health and aggregate usage—never private document or
              message content.
            </p>
          </div>
          <Button variant="secondary" onClick={load} disabled={loading}>
            <RefreshCw size={16} className={loading ? "spin" : ""} /> Refresh
          </Button>
        </header>
      </Reveal>
      {error && (
        <section className="admin-error">
          <AlertTriangle size={20} />
          <div>
            <strong>Admin data unavailable</strong>
            <p>{error}</p>
          </div>
          <Button size="sm" onClick={load}>
            Retry
          </Button>
        </section>
      )}
      {loading && !data ? (
        <div className="admin-skeleton">
          {Array.from({ length: 8 }).map((_, i) => (
            <i key={i} />
          ))}
        </div>
      ) : (
        data && (
          <>
            <div className="metric-grid">
              {Object.entries(data.metrics)
                .filter(([k]) => labels[k])
                .map(([key, value], i) => (
                  <Reveal key={key} delay={i * 0.025}>
                    <article className="metric-card">
                      <span>{labels[key]}</span>
                      <strong>{value.toLocaleString()}</strong>
                      <i>△</i>
                    </article>
                  </Reveal>
                ))}
            </div>
            <div className="admin-grid">
              <section className="admin-panel chart-panel">
                <header>
                  <Activity size={18} />
                  <div>
                    <span>14-DAY ACTIVITY</span>
                    <h2>Platform operations</h2>
                  </div>
                </header>
                <ResponsiveContainer width="100%" height={270}>
                  <AreaChart data={data.activity}>
                    <defs>
                      <linearGradient
                        id="activityFill"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="0"
                          stopColor="#7c5cff"
                          stopOpacity={0.5}
                        />
                        <stop offset="1" stopColor="#7c5cff" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.16} />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(v) => v.slice(5)}
                      fontSize={11}
                    />
                    <YAxis fontSize={11} />
                    <Tooltip />
                    <Area
                      type="monotone"
                      dataKey="conversations"
                      stroke="#8b72ff"
                      fill="url(#activityFill)"
                    />
                    <Area
                      type="monotone"
                      dataKey="documents"
                      stroke="#3dd9bd"
                      fill="transparent"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </section>
              <section className="admin-panel system-panel">
                <header>
                  <Database size={18} />
                  <div>
                    <span>INFRASTRUCTURE</span>
                    <h2>System health</h2>
                  </div>
                </header>
                {Object.entries(data.system).map(([name, state]) => (
                  <div className="system-row" key={name}>
                    <span>{name}</span>
                    <strong className={state}>
                      {state.replaceAll("_", " ")}
                    </strong>
                  </div>
                ))}
                <div className="privacy-admin-note">
                  <ShieldCheck size={18} />
                  <p>
                    Analytics intentionally exclude source text, prompts,
                    answers, citations, and secrets.
                  </p>
                </div>
              </section>
            </div>
            <section className="admin-panel">
              <header>
                <Gauge size={18} />
                <div>
                  <span>FALLBACK REGISTRIES</span>
                  <h2>Provider health & quota telemetry</h2>
                </div>
              </header>
              <div className="provider-grid">
                {data.providers.llm.map((p) => (
                  <ProviderCard key={`llm-${p.name}`} provider={p} kind="LLM" />
                ))}
                {data.providers.search.map((p) => (
                  <ProviderCard
                    key={`search-${p.name}`}
                    provider={p}
                    kind="SEARCH"
                  />
                ))}
              </div>
            </section>
            <section className="admin-panel operations-panel">
              <header>
                <ServerCog size={18} />
                <div>
                  <span>REQUEST OBSERVABILITY</span>
                  <h2>Privacy-safe API health</h2>
                </div>
              </header>
              <div className="operations-summary">
                <div><span>Total requests</span><strong>{data.operations.total_requests.toLocaleString()}</strong></div>
                <div><span>Active now</span><strong>{data.operations.active_requests}</strong></div>
                <div><span>Server errors</span><strong>{data.operations.server_errors}</strong></div>
                <div><span>Average latency</span><strong>{data.operations.average_duration_ms} ms</strong></div>
                <div><span>Process uptime</span><strong>{Math.floor(data.operations.uptime_seconds / 60).toLocaleString()} min</strong></div>
              </div>
              <div className="operations-table" role="region" aria-label="API route health" tabIndex={0}>
                <table>
                  <thead><tr><th>Route</th><th>Requests</th><th>Errors</th><th>Avg latency</th></tr></thead>
                  <tbody>
                    {data.operations.routes.length ? data.operations.routes.map((route) => (
                        <tr key={`${route.method}-${route.route}`}>
                          <td><i>{route.method}</i> {route.route}</td>
                          <td>{route.requests}</td>
                          <td>{route.errors}</td>
                          <td>{route.average_duration_ms} ms</td>
                        </tr>
                      )) : <tr><td colSpan={4}>No API requests recorded since this process started.</td></tr>}
                  </tbody>
                </table>
              </div>
              <p className="operations-privacy">Only normalized route templates, status classes, counts, and timing are retained in memory. Request bodies, query strings, source IDs, prompts, and user content are excluded.</p>
            </section>
            <div className="admin-grid">
              <section className="admin-panel log-panel">
                <header>
                  <Users size={18} />
                  <div>
                    <span>AUDIT TRAIL</span>
                    <h2>Recent protected actions</h2>
                  </div>
                </header>
                {data.audit_logs.length ? (
                  data.audit_logs.map((x, i) => (
                    <div className="log-row" key={`${x.action}-${i}`}>
                      <i>△</i>
                      <div>
                        <strong>{x.action.replaceAll("_", " ")}</strong>
                        <span>
                          {x.actor} · {x.resource_type ?? "system"}
                        </span>
                      </div>
                      <time>{new Date(x.created_at).toLocaleString()}</time>
                    </div>
                  ))
                ) : (
                  <p className="admin-empty">No audit events recorded.</p>
                )}
              </section>
              <section className="admin-panel log-panel">
                <header>
                  <ShieldCheck size={18} />
                  <div>
                    <span>SECURITY EVENTS</span>
                    <h2>Recent signals</h2>
                  </div>
                </header>
                {data.security_logs.length ? (
                  data.security_logs.map((x, i) => (
                    <div className="log-row" key={`${x.event}-${i}`}>
                      <i>!</i>
                      <div>
                        <strong>{x.event.replaceAll("_", " ")}</strong>
                        <span>{x.severity}</span>
                      </div>
                      <time>{new Date(x.created_at).toLocaleString()}</time>
                    </div>
                  ))
                ) : (
                  <p className="admin-empty">No security events recorded.</p>
                )}
              </section>
            </div>
          </>
        )
      )}
    </div>
  );
}
