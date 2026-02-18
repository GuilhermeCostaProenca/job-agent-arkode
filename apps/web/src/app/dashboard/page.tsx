import { Card } from "@/components/ui/card";
import { getFeed, getJobs, getRuns, getFollowups } from "@/lib/api";

export default async function DashboardPage() {
  const [runs, jobs, followups, feed] = await Promise.all([
    getRuns(),
    getJobs({ min_score: 0, status: "new" }),
    getFollowups(),
    getFeed({ hiring_only: true }),
  ]);

  const plainJobs = jobs.filter((j) => "id" in j) as Array<{ recommendation: string }>;
  const applyCount = plainJobs.filter((j) => j.recommendation === "APPLY").length;

  const today = new Date().toISOString().slice(0, 10);
  const runsToday = runs.filter((r) => r.started_at.startsWith(today)).length;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Dashboard</h2>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
        <Card>
          <p className="text-muted text-xs">Runs hoje</p>
          <p className="text-2xl font-bold">{runsToday}</p>
        </Card>
        <Card>
          <p className="text-muted text-xs">New jobs</p>
          <p className="text-2xl font-bold">{plainJobs.length}</p>
        </Card>
        <Card>
          <p className="text-muted text-xs">APPLY count</p>
          <p className="text-2xl font-bold">{applyCount}</p>
        </Card>
        <Card>
          <p className="text-muted text-xs">Followups pendentes</p>
          <p className="text-2xl font-bold">{followups.length}</p>
        </Card>
        <Card>
          <p className="text-muted text-xs">Hiring signals</p>
          <p className="text-2xl font-bold">{feed.length}</p>
        </Card>
      </div>

      <Card>
        <h3 className="mb-3 text-lg font-medium">Últimos runs</h3>
        <div className="space-y-2 text-sm">
          {runs.slice(0, 8).map((run) => (
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
