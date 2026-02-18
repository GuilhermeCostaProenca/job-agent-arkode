"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getFeed, createFeedDrafts, addFeedUrl, type FeedItem } from "@/lib/api";

export default function FeedPage() {
  const [rows, setRows] = useState<FeedItem[]>([]);
  const [hiringOnly, setHiringOnly] = useState(true);
  const [url, setUrl] = useState("");
  const [drafts, setDrafts] = useState<{ comment: string; dm: string; email: string } | null>(null);

  const load = async () => {
    try {
      setRows(await getFeed({ hiring_only: hiringOnly }));
    } catch (error) {
      toast.error((error as Error).message);
    }
  };

  useEffect(() => {
    void load();
  }, [hiringOnly]);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Feed Hunter</h2>
      <Card className="flex flex-wrap items-center gap-3">
        <Input placeholder="Adicionar URL de post" value={url} onChange={(e) => setUrl(e.target.value)} />
        <Button onClick={async () => {
          try {
            await addFeedUrl(url);
            toast.success("Feed item adicionado");
            setUrl("");
            await load();
          } catch (error) {
            toast.error((error as Error).message);
          }
        }}>feed add --url</Button>
        <Button variant="outline" onClick={() => setHiringOnly((v) => !v)}>
          hiring_only: {String(hiringOnly)}
        </Button>
      </Card>

      <div className="space-y-3">
        {rows.map((item) => (
          <Card key={item.id}>
            <div className="mb-2 flex items-center justify-between">
              <p className="font-medium">{item.url || item.source}</p>
              <p className="text-xs text-muted">hiring={String(item.is_hiring)} · conf={item.confidence.toFixed(2)}</p>
            </div>
            <p className="mb-2 text-sm text-muted">{item.text.slice(0, 180)}</p>
            <Button onClick={async () => {
              try {
                const result = await createFeedDrafts(item.id);
                setDrafts(result);
                toast.success("Drafts gerados");
              } catch (error) {
                toast.error((error as Error).message);
              }
            }}>Generate drafts</Button>
          </Card>
        ))}
      </div>

      {drafts ? (
        <Card>
          <h3 className="mb-3 text-lg font-medium">Drafts Viewer</h3>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {Object.entries(drafts).map(([key, value]) => (
              <div key={key} className="rounded-md border border-border p-3">
                <p className="mb-2 text-sm font-medium">{key}</p>
                <pre className="mb-2 whitespace-pre-wrap text-xs text-muted">{value}</pre>
                <Button variant="outline" onClick={async () => {
                  await navigator.clipboard.writeText(value);
                  toast.success(`${key} copiado`);
                }}>Copiar</Button>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
    </div>
  );
}
