"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getEmailEvents, syncEmail, type EmailEvent } from "@/lib/api";

export default function InboxPage() {
  const [rows, setRows] = useState<EmailEvent[]>([]);
  const [sender, setSender] = useState("talent@example.com");
  const [subject, setSubject] = useState("Interview invitation");
  const [snippet, setSnippet] = useState("We would like to schedule an interview.");

  const load = async () => {
    try {
      setRows(await getEmailEvents());
    } catch (error) {
      toast.error((error as Error).message);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Inbox Sync</h2>
      <Card className="space-y-3">
        <input className="h-10 w-full rounded-md border border-border bg-zinc-950 px-3 text-sm" value={sender} onChange={(e) => setSender(e.target.value)} placeholder="sender" />
        <input className="h-10 w-full rounded-md border border-border bg-zinc-950 px-3 text-sm" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="subject" />
        <textarea className="min-h-[120px] w-full rounded-md border border-border bg-zinc-950 p-3 text-sm" value={snippet} onChange={(e) => setSnippet(e.target.value)} placeholder="snippet" />
        <div className="flex gap-2">
          <Button onClick={async () => {
            try {
              const result = await syncEmail([{ sender, subject, snippet }]);
              toast.success(`Inbox sync: ${result.inserted} inseridos`);
              await load();
            } catch (error) {
              toast.error((error as Error).message);
            }
          }}>Simular Gmail sync</Button>
          <Button variant="outline" onClick={() => void load()}>Atualizar</Button>
        </div>
      </Card>
      <div className="space-y-3">
        {rows.map((row) => (
          <Card key={row.id}>
            <div className="flex items-center justify-between">
              <p className="font-medium">{row.subject}</p>
              <p className="text-sm text-muted">{row.status_inferred}</p>
            </div>
            <p className="text-sm text-muted">{row.sender}</p>
            <p className="mt-2 text-sm">{row.snippet}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
