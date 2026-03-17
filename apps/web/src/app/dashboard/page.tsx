"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { applySelected, applyShortlist, diagnoseLinkedinJob, discoverLinkedinJobs, getDashboard, getMcpTools, getShortlistPreview, purgeLinkedinJobs, repairLinkedinJobs, resumeRun, setupLinkedinSession, type Dashboard, type ExecutionRun, type PendingAction, type ShortlistItem, startRun } from "@/lib/api";

const EMPTY_DASHBOARD: Dashboard = {
  jobs_discovered: 0,
  jobs_ready: 0,
  applications_total: 0,
  applications_submitted: 0,
  execution_paused: 0,
  inbox_updates: 0,
  platform_breakdown: {},
  recent_runs: [],
  recent_executions: [],
  recent_shortlist_results: [],
  paused_executions: [],
  pending_actions: [],
  operational_policy: {
    daily_application_limit: 0,
    platform_application_limit: 0,
    retry_backoff_window_minutes: 0,
    max_retries_per_connector: 0,
    today_total: 0,
    connectors: [],
  },
  browser_sessions: [],
  credential_states: [],
};

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<Dashboard>(EMPTY_DASHBOARD);
  const [tools, setTools] = useState<Array<{ name: string; description: string; category: string }>>([]);
  const [running, setRunning] = useState(false);
  const [busyRunId, setBusyRunId] = useState("");
  const [shortlistBusy, setShortlistBusy] = useState(false);
  const [shortlistLimit, setShortlistLimit] = useState(5);
  const [shortlistPreview, setShortlistPreview] = useState<ShortlistItem[]>([]);
  const [selectedShortlistIds, setSelectedShortlistIds] = useState<string[]>([]);
  const [sources, setSources] = useState("rss,manual");
  const [limit, setLimit] = useState(30);
  const [rssFeed, setRssFeed] = useState("https://remoteok.com/remote-dev-jobs.rss");
  const [manualUrls, setManualUrls] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [linkedinBusy, setLinkedinBusy] = useState(false);
  const [linkedinDiscovery, setLinkedinDiscovery] = useState<Array<{ url: string; title: string; company: string; location: string; description: string }>>([]);
  const [linkedinImportBusy, setLinkedinImportBusy] = useState(false);
  const [linkedinRepairBusy, setLinkedinRepairBusy] = useState(false);
  const [linkedinPurgeBusy, setLinkedinPurgeBusy] = useState(false);

  const load = async () => {
    try {
      const [dashboardData, toolData] = await Promise.all([getDashboard(), getMcpTools()]);
      setDashboard(dashboardData);
      setTools(toolData);
      const shortlist = await getShortlistPreview(shortlistLimit);
      setShortlistPreview(shortlist);
      setSelectedShortlistIds((current) => {
        const available = new Set(shortlist.map((item) => item.job_id));
        const preserved = current.filter((jobId) => available.has(jobId));
        return preserved.length ? preserved : shortlist.map((item) => item.job_id);
      });
    } catch (error) {
      toast.error((error as Error).message);
    }
  };

  useEffect(() => {
    void load();
  }, [shortlistLimit]);

  const runNow = async () => {
    setRunning(true);
    try {
      const result = await startRun({
        sources: sources.split(",").map((item) => item.trim()).filter(Boolean),
        limit: Math.max(1, limit),
        rss_feed: rssFeed.trim(),
        manual_urls: manualUrls.split(/\r?\n|,/).map((item) => item.trim()).filter(Boolean),
      });
      toast.success(`Run ${result.run_id} finalizado com ${result.jobs_collected} vagas.`);
      await load();
    } catch (error) {
      toast.error((error as Error).message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Cockpit</h2>
      <Card className="space-y-3">
        <h3 className="text-lg font-medium">Descobrir vagas agora</h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Input value={sources} onChange={(e) => setSources(e.target.value)} placeholder="rss,manual" />
          <Input type="number" value={limit} onChange={(e) => setLimit(Number(e.target.value || 1))} />
          <Input value={rssFeed} onChange={(e) => setRssFeed(e.target.value)} placeholder="RSS URL" />
        </div>
        <textarea className="min-h-[96px] w-full rounded-md border border-border bg-zinc-950 p-3 text-sm" value={manualUrls} onChange={(e) => setManualUrls(e.target.value)} placeholder="Manual URLs, uma por linha" />
        <div className="grid max-w-xs grid-cols-1 gap-2">
          <Input type="number" value={shortlistLimit} onChange={(e) => setShortlistLimit(Number(e.target.value || 1))} placeholder="Shortlist limit" />
        </div>
        <div className="flex gap-2">
          <Button onClick={() => void runNow()} disabled={running}>{running ? "Executando..." : "Executar run"}</Button>
          <Button
            variant="outline"
            disabled={shortlistBusy || selectedShortlistIds.length === 0}
            onClick={async () => {
              setShortlistBusy(true);
              try {
                const result = await applySelected(selectedShortlistIds);
                toast.success(result.message);
                await load();
              } catch (error) {
                toast.error((error as Error).message);
              } finally {
                setShortlistBusy(false);
              }
            }}
          >
            {shortlistBusy ? "Aplicando..." : "Apply selected"}
          </Button>
          <Button
            variant="outline"
            disabled={shortlistBusy}
            onClick={async () => {
              setShortlistBusy(true);
              try {
                const result = await applyShortlist(shortlistLimit);
                toast.success(result.message);
                await load();
              } catch (error) {
                toast.error((error as Error).message);
              } finally {
                setShortlistBusy(false);
              }
            }}
          >
            {shortlistBusy ? "Aplicando..." : "Apply shortlist"}
          </Button>
          <Button variant="outline" onClick={() => void load()} disabled={running}>Atualizar</Button>
        </div>
        {shortlistPreview.length > 0 ? (
          <div className="space-y-2 rounded-md border border-border p-3 text-sm">
            <p className="font-medium">Shortlist preview</p>
            {shortlistPreview.map((item) => (
              <div key={item.job_id} className="rounded-md border border-border p-2">
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={selectedShortlistIds.includes(item.job_id)}
                    onChange={(event) => {
                      setSelectedShortlistIds((current) =>
                        event.target.checked ? [...current, item.job_id] : current.filter((jobId) => jobId !== item.job_id),
                      );
                    }}
                  />
                  <div>
                    <p className="font-medium">{item.title}</p>
                    <p className="text-muted">{item.company} · score {item.score}</p>
                  </div>
                </label>
              </div>
            ))}
          </div>
        ) : null}
      </Card>

      <Card className="space-y-3">
        <h3 className="text-lg font-medium">LinkedIn Session Setup</h3>
        <p className="text-sm text-muted">
          O Playwright usa um perfil persistente proprio em vez da sessao do seu navegador principal.
        </p>
        <Input value={linkedinUrl} onChange={(e) => setLinkedinUrl(e.target.value)} placeholder="https://www.linkedin.com/jobs/view/..." />
        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={linkedinBusy}
            onClick={async () => {
              setLinkedinBusy(true);
              try {
                const result = await setupLinkedinSession();
                toast.success(result.message);
                await load();
              } catch (error) {
                toast.error((error as Error).message);
              } finally {
                setLinkedinBusy(false);
              }
            }}
          >
            {linkedinBusy ? "Abrindo..." : "Abrir sessao LinkedIn"}
          </Button>
          <Button
            disabled={linkedinBusy || !linkedinUrl.trim()}
            onClick={async () => {
              setLinkedinBusy(true);
              try {
                const result = await diagnoseLinkedinJob(linkedinUrl.trim());
                toast.success(result.message);
                await load();
              } catch (error) {
                toast.error((error as Error).message);
              } finally {
                setLinkedinBusy(false);
              }
            }}
          >
            {linkedinBusy ? "Diagnosticando..." : "Diagnosticar Easy Apply"}
          </Button>
          <Button
            variant="outline"
            disabled={linkedinBusy}
            onClick={async () => {
              setLinkedinBusy(true);
              try {
                const result = await discoverLinkedinJobs(8);
                setLinkedinDiscovery(result.jobs);
                toast.success(result.message);
                await load();
              } catch (error) {
                toast.error((error as Error).message);
              } finally {
                setLinkedinBusy(false);
              }
            }}
          >
            {linkedinBusy ? "Lendo vagas..." : "Preview discovery LinkedIn"}
          </Button>
          <Button
            disabled={linkedinImportBusy}
            onClick={async () => {
              setLinkedinImportBusy(true);
              try {
                const result = await startRun({
                  sources: ["linkedin"],
                  limit: 8,
                  rss_feed: rssFeed.trim(),
                  manual_urls: [],
                });
                toast.success(`LinkedIn importado: ${result.jobs_collected} vagas no run ${result.run_id}.`);
                await load();
              } catch (error) {
                toast.error((error as Error).message);
              } finally {
                setLinkedinImportBusy(false);
              }
            }}
          >
            {linkedinImportBusy ? "Importando vagas..." : "Importar vagas LinkedIn"}
          </Button>
          <Button
            variant="outline"
            disabled={linkedinRepairBusy}
            onClick={async () => {
              setLinkedinRepairBusy(true);
              try {
                const result = await repairLinkedinJobs(8);
                toast.success(result.message);
                await load();
              } catch (error) {
                toast.error((error as Error).message);
              } finally {
                setLinkedinRepairBusy(false);
              }
            }}
          >
            {linkedinRepairBusy ? "Reparando..." : "Repair pass LinkedIn"}
          </Button>
          <Button
            variant="outline"
            disabled={linkedinPurgeBusy}
            onClick={async () => {
              setLinkedinPurgeBusy(true);
              try {
                const result = await purgeLinkedinJobs(20);
                toast.success(result.message);
                await load();
              } catch (error) {
                toast.error((error as Error).message);
              } finally {
                setLinkedinPurgeBusy(false);
              }
            }}
          >
            {linkedinPurgeBusy ? "Limpando..." : "Purge low-fit LinkedIn"}
          </Button>
        </div>
        {linkedinDiscovery.length > 0 ? (
          <div className="space-y-2 rounded-md border border-border p-3 text-sm">
            {linkedinDiscovery.map((job) => (
              <div key={job.url} className="rounded-md border border-border p-2">
                <p className="font-medium">{job.title}</p>
                <p className="text-muted">{job.company} · {job.location}</p>
                <p className="mt-1 line-clamp-2 text-xs text-muted">{job.description}</p>
              </div>
            ))}
          </div>
        ) : null}
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <MetricCard label="Jobs encontrados" value={dashboard.jobs_discovered} />
        <MetricCard label="Prontos para aplicar" value={dashboard.jobs_ready} />
        <MetricCard label="Applications" value={dashboard.applications_total} />
        <MetricCard label="Submetidas" value={dashboard.applications_submitted} />
        <MetricCard label="Execucoes pausadas" value={dashboard.execution_paused} />
        <MetricCard label="Inbox updates" value={dashboard.inbox_updates} />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <h3 className="mb-3 text-lg font-medium">Runs recentes</h3>
          <div className="space-y-2 text-sm">
            {dashboard.recent_runs.map((run) => (
              <div key={run.id} className="flex items-center justify-between rounded-md border border-border p-2">
                <span>{run.id}</span>
                <span className="text-muted">{run.status} · {run.jobs_collected} jobs</span>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <h3 className="mb-3 text-lg font-medium">Execucoes recentes</h3>
          <div className="space-y-2 text-sm">
            {dashboard.recent_executions.map((run) => (
              <ExecutionCard key={run.id} run={run} />
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <h3 className="mb-3 text-lg font-medium">Ultimo apply shortlist</h3>
        <div className="space-y-2 text-sm">
          {dashboard.recent_shortlist_results.length === 0 ? (
            <p className="text-muted">Nenhuma execucao de shortlist registrada.</p>
          ) : (
            dashboard.recent_shortlist_results.map((run) => (
              <ExecutionCard key={run.id} run={run} />
            ))
          )}
        </div>
      </Card>

      <Card>
        <h3 className="mb-3 text-lg font-medium">Pausas que exigem acao</h3>
        <div className="space-y-2 text-sm">
          {dashboard.pending_actions.length === 0 ? (
            <p className="text-muted">Nenhuma execucao pausada no momento.</p>
          ) : (
            dashboard.pending_actions.map((item) => (
              <PendingActionCard
                key={item.id}
                item={item}
                busy={busyRunId === item.id}
                onResume={item.kind === "execution_pause" ? async () => {
                  setBusyRunId(item.id);
                  try {
                    await resumeRun(item.id);
                    toast.success("Execucao retomada");
                    await load();
                  } catch (error) {
                    toast.error((error as Error).message);
                  } finally {
                    setBusyRunId("");
                  }
                } : undefined}
              />
            ))
          )}
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <h3 className="mb-3 text-lg font-medium">Platform breakdown</h3>
          <div className="space-y-2 text-sm">
            {Object.entries(dashboard.platform_breakdown).map(([platform, count]) => (
              <div key={platform} className="flex items-center justify-between rounded-md border border-border p-2">
                <span>{platform}</span>
                <span>{count}</span>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <h3 className="mb-3 text-lg font-medium">Tools MCP catalogadas</h3>
          <div className="space-y-2 text-sm">
            {tools.map((tool) => (
              <div key={tool.name} className="rounded-md border border-border p-2">
                <p className="font-medium">{tool.name}</p>
                <p className="text-muted">{tool.category} · {tool.description}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <h3 className="mb-3 text-lg font-medium">Politica operacional</h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <MetricCard label="Uso diario" value={dashboard.operational_policy.today_total} />
          <MetricCard label="Teto diario" value={dashboard.operational_policy.daily_application_limit} />
          <MetricCard label="Teto por plataforma" value={dashboard.operational_policy.platform_application_limit} />
          <MetricCard label="Janela backoff (min)" value={dashboard.operational_policy.retry_backoff_window_minutes} />
        </div>
        <div className="mt-4 space-y-2 text-sm">
          {dashboard.operational_policy.connectors.map((item) => (
            <div key={item.connector} className="flex items-center justify-between rounded-md border border-border p-2">
              <span>{item.connector}</span>
              <span className="text-muted">
                hoje={item.today_count} · falhas={item.recent_failures} · sessao={item.session_state}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <p className="text-muted text-xs">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </Card>
  );
}

function ExecutionCard({ run, highlightPause = false }: { run: ExecutionRun; highlightPause?: boolean }) {
  return (
    <div className={`rounded-md border p-3 ${highlightPause ? "border-amber-500/40 bg-amber-500/5" : "border-border"}`}>
      <p className="font-medium">{run.connector}</p>
      <p className="text-muted">{run.status} · step={run.current_step}</p>
      {run.pause_reason ? <p className="text-xs text-amber-300">{run.pause_reason}</p> : null}
      {run.recommended_action ? <p className="text-xs text-muted">{run.recommended_action}</p> : null}
    </div>
  );
}

function PendingActionCard({ item, busy, onResume }: { item: PendingAction; busy: boolean; onResume?: () => Promise<void> }) {
  return (
    <div className="rounded-md border border-amber-500/40 bg-amber-500/5 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium">{item.title}</p>
          <p className="text-xs text-amber-300">{item.pause_reason}</p>
          <p className="text-xs text-muted">{item.recommended_action}</p>
        </div>
        {onResume ? (
          <Button variant="outline" disabled={busy} onClick={() => void onResume()}>
            {busy ? "Retomando..." : "Retomar"}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
