"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { applyToJob, getApplications, getPendingActions, resumeRun, type Application, type PendingAction } from "@/lib/api";

export default function ApplicationsPage() {
  const [rows, setRows] = useState<Application[]>([]);
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);
  const [status, setStatus] = useState("");
  const [busyId, setBusyId] = useState("");

  const load = async () => {
    try {
      const [applications, pending] = await Promise.all([getApplications(status || undefined), getPendingActions()]);
      setRows(applications);
      setPendingActions(pending);
    } catch (error) {
      toast.error((error as Error).message);
    }
  };

  useEffect(() => {
    void load();
  }, [status]);

  const pendingByApplication = useMemo(() => {
    return new Map(pendingActions.filter((item) => item.kind === "execution_pause").map((item) => [item.application_id, item]));
  }, [pendingActions]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Applications</h2>
        <Select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">all</option>
          <option value="prepared">prepared</option>
          <option value="reviewed">reviewed</option>
          <option value="applied">applied</option>
          <option value="rejected">rejected</option>
        </Select>
      </div>
      <div className="space-y-3">
        {rows.map((row) => {
          const pending = pendingByApplication.get(row.id);
          const isBusy = busyId === row.id;
          return (
            <Card key={row.id} className="flex items-center justify-between gap-4">
              <div>
                <p className="font-medium">{row.job_id}</p>
                <p className="text-sm text-muted">{row.connector} · {row.status} · {row.recommendation}</p>
                {pending ? (
                  <>
                    <p className="text-xs text-amber-300">{pending.pause_reason}</p>
                    <p className="text-xs text-muted">{pending.recommended_action}</p>
                  </>
                ) : null}
              </div>
              <div className="flex gap-2">
                {pending ? (
                  <Button
                    variant="outline"
                    disabled={isBusy}
                    onClick={async () => {
                      setBusyId(row.id);
                      try {
                        await resumeRun(pending.id);
                        toast.success("Execucao retomada");
                        await load();
                      } catch (error) {
                        toast.error((error as Error).message);
                      } finally {
                        setBusyId("");
                      }
                    }}
                  >
                    {isBusy ? "Retomando..." : "Retomar"}
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    disabled={isBusy}
                    onClick={async () => {
                      setBusyId(row.id);
                      try {
                        await applyToJob(row.job_id);
                        toast.success("Execucao iniciada");
                        await load();
                      } catch (error) {
                        toast.error((error as Error).message);
                      } finally {
                        setBusyId("");
                      }
                    }}
                  >
                    {isBusy ? "Executando..." : "Executar"}
                  </Button>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
