"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { getArtifactContent, getArtifacts, getJob, type Artifact, type Job } from "@/lib/api";

export default function JobDetailPage() {
  const params = useParams<{ job_id: string }>();
  const jobId = params.job_id;
  const [job, setJob] = useState<Job | null>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [selectedKind, setSelectedKind] = useState("resume");
  const [content, setContent] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const [j, a] = await Promise.all([getJob(jobId), getArtifacts(jobId)]);
        setJob(j);
        setArtifacts(a);
      } catch (error) {
        toast.error((error as Error).message);
      }
    };
    void load();
  }, [jobId]);

  const kinds = useMemo(() => {
    const all = artifacts.map((a) => a.kind);
    return Array.from(new Set(all));
  }, [artifacts]);

  useEffect(() => {
    if (!jobId || !selectedKind) return;
    const run = async () => {
      try {
        const res = await getArtifactContent(jobId, selectedKind);
        setContent(res.content);
      } catch {
        setContent("(Sem conteúdo disponível)");
      }
    };
    void run();
  }, [jobId, selectedKind]);

  const copy = async () => {
    await navigator.clipboard.writeText(content);
    toast.success("Copiado para área de transferência");
  };

  if (!job) {
    return <p className="text-sm text-muted">Carregando detalhes...</p>;
  }

  const anchors = job.anchors_json ? JSON.parse(job.anchors_json) : {};
  const breakdown = job.score_breakdown_json ? JSON.parse(job.score_breakdown_json) : {};

  return (
    <div className="space-y-6">
      <Card>
        <h2 className="text-2xl font-semibold">{job.title}</h2>
        <p className="text-sm text-muted">{job.company} · {job.location}</p>
        <p className="mt-3 whitespace-pre-wrap text-sm">{job.description}</p>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <h3 className="mb-2 font-medium">Anchors</h3>
          <pre className="overflow-auto text-xs text-muted">{JSON.stringify(anchors, null, 2)}</pre>
        </Card>
        <Card>
          <h3 className="mb-2 font-medium">Score breakdown</h3>
          <pre className="overflow-auto text-xs text-muted">{JSON.stringify(breakdown, null, 2)}</pre>
        </Card>
      </div>

      <Card>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Select value={selectedKind} onChange={(e) => setSelectedKind(e.target.value)}>
            {(kinds.length ? kinds : ["resume"]).map((kind) => (
              <option key={kind} value={kind}>{kind}</option>
            ))}
          </Select>
          <Button variant="outline" onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"}/artifacts/${jobId}/content?kind=${selectedKind}`, "_blank")}>Download artifact</Button>
          <Button onClick={() => void copy()}>Copiar texto</Button>
        </div>
        <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap rounded-md border border-border p-3 text-sm">{content}</pre>
      </Card>
    </div>
  );
}
