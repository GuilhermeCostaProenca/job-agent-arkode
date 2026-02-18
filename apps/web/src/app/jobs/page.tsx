"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  approveJob,
  getJobs,
  rejectJob,
  setApplicationStatus,
  type Job,
} from "@/lib/api";
import { useDebounce } from "@/hooks/use-debounce";

const approveReasons = [
  "like_company",
  "like_role",
  "good_growth",
  "good_learning",
  "good_stack_match",
];
const rejectReasons = [
  "stack_mismatch",
  "seniority_too_high",
  "salary_low",
  "location_bad",
  "company_type_bad",
  "description_generic",
  "red_flag_pj",
  "red_flag_unpaid",
  "support_disguised",
  "commute_too_far",
];

export default function JobsPage() {
  const [rows, setRows] = useState<Array<{ job: Job; is_exploration: boolean }>>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const debounced = useDebounce(search, 350);
  const [minScore, setMinScore] = useState(70);
  const [status, setStatus] = useState("new");
  const [explore, setExplore] = useState(false);
  const [notes, setNotes] = useState("");
  const [reason, setReason] = useState(approveReasons[0]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const data = await getJobs({ min_score: minScore, status, explore });
      const normalized = data.map((item) =>
        "job" in item ? item : { job: item, is_exploration: false },
      );
      setRows(normalized);
    } catch (error) {
      toast.error((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchData();
  }, [minScore, status, explore]);

  const filtered = useMemo(() => {
    return rows.filter((row) => {
      const hay = `${row.job.company} ${row.job.title}`.toLowerCase();
      return hay.includes(debounced.toLowerCase());
    });
  }, [debounced, rows]);

  const action = async (fn: () => Promise<unknown>, okMessage: string) => {
    try {
      await fn();
      toast.success(okMessage);
      await fetchData();
    } catch (error) {
      toast.error((error as Error).message);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Jobs Inbox</h2>
      <Card className="grid grid-cols-1 gap-3 md:grid-cols-5">
        <Input placeholder="Buscar empresa/cargo" value={search} onChange={(e) => setSearch(e.target.value)} />
        <Input type="number" value={minScore} onChange={(e) => setMinScore(Number(e.target.value || 0))} />
        <Select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="new">new</option>
          <option value="reviewed">reviewed</option>
          <option value="applied">applied</option>
          <option value="rejected">rejected</option>
        </Select>
        <Select value={explore ? "yes" : "no"} onChange={(e) => setExplore(e.target.value === "yes")}>
          <option value="no">Sem exploração</option>
          <option value="yes">80/20 exploração</option>
        </Select>
        <Button onClick={() => void fetchData()}>Atualizar</Button>
      </Card>

      {loading ? <p className="text-sm text-muted">Carregando...</p> : null}

      <div className="space-y-3">
        {filtered.map(({ job, is_exploration }) => (
          <Card key={job.id}>
            <div className="mb-3 flex items-center justify-between">
              <div>
                <p className="font-medium">{job.title}</p>
                <p className="text-sm text-muted">{job.company} · {job.score}</p>
              </div>
              <div className="flex items-center gap-2">
                {is_exploration ? <span className="rounded bg-primary px-2 py-1 text-xs">exploration</span> : null}
                <Link className="text-sm text-primary underline" href={`/jobs/${job.id}`}>Abrir</Link>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-2 md:grid-cols-4">
              <Select value={reason} onChange={(e) => setReason(e.target.value)}>
                {approveReasons.concat(rejectReasons).map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </Select>
              <Input placeholder="notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
              <div className="flex gap-2">
                <Button onClick={() => void action(() => approveJob(job.id, reason, notes), "Aprovado")}>Approve</Button>
                <Button variant="destructive" onClick={() => void action(() => rejectJob(job.id, reason, notes), "Rejeitado")}>Reject</Button>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={() => void action(() => setApplicationStatus(job.id, "applied", { notes }), "Applied")}>Applied</Button>
                <Button variant="outline" onClick={() => void action(() => setApplicationStatus(job.id, "replied", { notes }), "Replied")}>Replied</Button>
                <Button variant="outline" onClick={() => void action(() => setApplicationStatus(job.id, "interview", { notes }), "Interview")}>Interview</Button>
                <Button variant="outline" onClick={() => void action(() => setApplicationStatus(job.id, "offer", { notes }), "Offer")}>Offer</Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
