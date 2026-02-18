"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Card } from "@/components/ui/card";
import { getFeed, getFollowups, getJobs, getRuns, type Run } from "@/lib/api";

type DashboardState = {
  runs: Run[];
  newJobs: number;
  applyCount: number;
  followups: number;
  hiringSignals: number;
};

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [state, setState] = useState<DashboardState>({
    runs: [],
    newJobs: 0,
    applyCount: 0,
    followups: 0,
    hiringSignals: 0,
  });

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [runs, jobs, followups, feed] = await Promise.all([
          getRuns(),
          getJobs({ min_score: 0, status: "new" }),
          getFollowups(),
          getFeed({ hiring_only: true }),
        ]);

        const plainJobs = jobs.filter((j) => "id" in j) as Array<{ recommendation: string }>;
        const applyCount = plainJobs.filter((j) => j.recommendation === "APPLY").length;

        setState({
          runs,
          newJobs: plainJobs.length,
          applyCount,
          followups: followups.length,
          hiringSignals: feed.length,
        });
      } catch (error) {
        toast.error((error as Error).message);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, []);

  const runsToday = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10);
    return state.runs.filter((r) => r.started_at.startsWith(today)).length;
  }, [state.runs]);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Dashboard</h2>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
        <Card>
          <p className="text-muted text-xs">Runs hoje</p>
          <p className="text-2xl font-bold">{loading ? "..." : runsToday}</p>
        </Card>
        <Card>
          <p className="text-muted text-xs">New jobs</p>
          <p className="text-2xl font-bold">{loading ? "..." : state.newJobs}</p>
        </Card>
        <Card>
          <p className="text-muted text-xs">APPLY count</p>
          <p className="text-2xl font-bold">{loading ? "..." : state.applyCount}</p>
        </Card>
        <Card>
          <p className="text-muted text-xs">Followups pendentes</p>
          <p className="text-2xl font-bold">{loading ? "..." : state.followups}</p>
        </Card>
        <Card>
          <p className="text-muted text-xs">Hiring signals</p>
          <p className="text-2xl font-bold">{loading ? "..." : state.hiringSignals}</p>
        </Card>
      </div>

      <Card>
        <h3 className="mb-3 text-lg font-medium">Últimos runs</h3>
        {!state.runs.length && !loading ? (
          <p className="text-sm text-muted">Sem runs disponíveis (verifique se a API está ativa).</p>
        ) : null}
        <div className="space-y-2 text-sm">
          {state.runs.slice(0, 8).map((run) => (
            <div key={run.id} className="flex items-center justify-between rounded-md border border-border p-2">
              <span>{run.id}</span>
              <span className="text-muted">{run.status} · {run.jobs_collected} jobs</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
