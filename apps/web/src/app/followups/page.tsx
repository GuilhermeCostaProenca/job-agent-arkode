"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getFollowups, setApplicationStatus } from "@/lib/api";

export default function FollowupsPage() {
  const [rows, setRows] = useState<Array<{ job_id: string; follow_up_date: string; status: string; notes: string }>>([]);
  const [note, setNote] = useState("");

  const load = async () => {
    try {
      setRows(await getFollowups());
    } catch (error) {
      toast.error((error as Error).message);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Follow-ups</h2>
      <Input placeholder="notes followup_done" value={note} onChange={(e) => setNote(e.target.value)} />
      <div className="space-y-3">
        {rows.map((row) => (
          <Card key={row.job_id} className="flex items-center justify-between">
            <div>
              <p className="font-medium">{row.job_id}</p>
              <p className="text-sm text-muted">due: {row.follow_up_date} · {row.status}</p>
            </div>
            <Button
              onClick={async () => {
                try {
                  await setApplicationStatus(row.job_id, "followup_done", { notes: note });
                  toast.success("Follow-up marcado");
                  await load();
                } catch (error) {
                  toast.error((error as Error).message);
                }
              }}
            >
              Marcar followup_done
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );
}
