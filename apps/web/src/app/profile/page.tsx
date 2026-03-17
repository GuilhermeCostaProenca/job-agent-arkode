"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, Send } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  chatWithProfileBrain,
  getProfileBrain,
  importGithubProfile,
  importLinkedinProfile,
  resolveProfileConflict,
  saveProfile,
  type Profile,
  type ProfileBrain,
} from "@/lib/api";

const EMPTY_BRAIN: ProfileBrain = {
  profile: {
    name: "",
    target_role: "",
    location: "",
    stacks: [],
    links: {},
    experiences: [],
    projects: [],
    education: [],
    preferences: {},
    bullet_bank: {},
    learning_plan: [],
  },
  evidences: [],
  memory_items: [],
  conversation: [],
  conflicts: [],
};

function compactProfile(brain: ProfileBrain): Profile {
  return {
    profile: brain.profile,
    evidences: brain.evidences,
  };
}

export default function ProfilePage() {
  const [brain, setBrain] = useState<ProfileBrain>(EMPTY_BRAIN);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [chatting, setChatting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [importingGithub, setImportingGithub] = useState(false);
  const [importingLinkedin, setImportingLinkedin] = useState(false);
  const [resolvingConflictId, setResolvingConflictId] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setBrain(await getProfileBrain());
      } catch (error) {
        toast.error((error as Error).message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const profileSignals = useMemo(
    () => [
      { label: "Objetivo atual", value: brain.profile.target_role || "Ainda nao definido" },
      { label: "Localizacao", value: brain.profile.location || "Nao definido" },
      { label: "Stacks foco", value: brain.profile.stacks.join(", ") || "Sem stacks priorizadas" },
      { label: "Aprendizado", value: brain.profile.learning_plan.join(" | ") || "Sem plano registrado" },
    ],
    [brain],
  );

  async function submitMessage() {
    const trimmed = message.trim();
    if (!trimmed) return;
    setChatting(true);
    try {
      const response = await chatWithProfileBrain(trimmed);
      setBrain(response.brain);
      setMessage("");
      toast.success(response.assistant_message);
    } catch (error) {
      toast.error((error as Error).message);
    } finally {
      setChatting(false);
    }
  }

  async function persistProfile() {
    setSaving(true);
    try {
      const saved = await saveProfile(compactProfile(brain));
      setBrain((prev) => ({ ...prev, profile: saved.profile, evidences: saved.evidences }));
      toast.success("Resumo estruturado salvo");
    } catch (error) {
      toast.error((error as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function syncGithub() {
    setImportingGithub(true);
    try {
      const result = await importGithubProfile(brain.profile.links.github);
      setBrain(result.brain);
      toast.success(`${result.assistant_message} (${result.imported_repositories} repos)`);
    } catch (error) {
      toast.error((error as Error).message);
    } finally {
      setImportingGithub(false);
    }
  }

  async function syncLinkedin() {
    setImportingLinkedin(true);
    try {
      const result = await importLinkedinProfile(brain.profile.links.linkedin);
      setBrain(result.brain);
      toast.success(result.assistant_message);
    } catch (error) {
      toast.error((error as Error).message);
    } finally {
      setImportingLinkedin(false);
    }
  }

  async function confirmConflictValue(field: string, value: string, conflictId: string) {
    setResolvingConflictId(conflictId);
    try {
      const result = await resolveProfileConflict(field, value);
      setBrain(result.brain);
      toast.success(result.assistant_message);
    } catch (error) {
      toast.error((error as Error).message);
    } finally {
      setResolvingConflictId(null);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold">Profile Brain</h2>
        <p className="max-w-3xl text-sm text-zinc-400">
          Conte para a IA o que voce quer agora, quais projetos terminou, o que nao quer mais e quais skills quer puxar.
          A memoria abaixo vira contexto real para descoberta, scoring e candidatura.
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Card className="space-y-4">
          <div className="space-y-2">
            <h3 className="text-lg font-medium">Conversa</h3>
            <p className="text-sm text-zinc-400">
              Exemplos: "agora quero mirar em estagio backend remoto", "terminei um projeto com FastAPI e PostgreSQL",
              "nao quero mais suporte ou vaga presencial".
            </p>
          </div>

          <div className="max-h-[28rem] space-y-3 overflow-y-auto rounded-xl border border-zinc-800 bg-zinc-950/70 p-4">
            {brain.conversation.length === 0 ? (
              <p className="text-sm text-zinc-500">Nenhuma conversa ainda. Comece descrevendo seu foco atual.</p>
            ) : (
              brain.conversation.map((turn) => (
                <div
                  key={turn.id}
                  className={`rounded-xl border px-4 py-3 text-sm ${
                    turn.role === "user"
                      ? "ml-10 border-emerald-900/60 bg-emerald-950/40 text-zinc-100"
                      : "mr-10 border-zinc-800 bg-zinc-900 text-zinc-200"
                  }`}
                >
                  <div className="mb-1 text-[11px] uppercase tracking-[0.18em] text-zinc-500">
                    {turn.role === "user" ? "Voce" : "Agent"}
                  </div>
                  <p className="whitespace-pre-wrap">{turn.message}</p>
                </div>
              ))
            )}
          </div>

          <div className="space-y-3">
            <textarea
              className="min-h-[150px] w-full rounded-xl border border-zinc-800 bg-zinc-950 p-4 text-sm outline-none ring-0 transition focus:border-emerald-700"
              placeholder="Ex: agora quero focar em vaga junior backend, remoto, e hoje terminei um projeto de dashboard com React + FastAPI."
              value={message}
              onChange={(event) => setMessage(event.target.value)}
            />
            <div className="flex justify-end">
              <Button onClick={() => void submitMessage()} disabled={chatting || !message.trim()} className="gap-2">
                {chatting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                Atualizar memoria
              </Button>
            </div>
          </div>
        </Card>

        <div className="space-y-6">
          <Card className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-medium">Resumo vivo</h3>
                <p className="text-sm text-zinc-400">Campo estruturado que o agente reaproveita nos fluxos automaticos.</p>
              </div>
              <Button variant="outline" onClick={() => void persistProfile()} disabled={saving}>
                {saving ? "Salvando..." : "Salvar resumo"}
              </Button>
            </div>

            <div className="grid gap-3">
              <Input
                value={brain.profile.name}
                onChange={(event) =>
                  setBrain((prev) => ({ ...prev, profile: { ...prev.profile, name: event.target.value } }))
                }
                placeholder="Nome"
              />
              <Input
                value={brain.profile.target_role}
                onChange={(event) =>
                  setBrain((prev) => ({ ...prev, profile: { ...prev.profile, target_role: event.target.value } }))
                }
                placeholder="Objetivo atual"
              />
              <Input
                value={brain.profile.location}
                onChange={(event) =>
                  setBrain((prev) => ({ ...prev, profile: { ...prev.profile, location: event.target.value } }))
                }
                placeholder="Preferencia de localizacao"
              />
              <Input
                value={brain.profile.links.github ?? ""}
                onChange={(event) =>
                  setBrain((prev) => ({
                    ...prev,
                    profile: {
                      ...prev.profile,
                      links: { ...prev.profile.links, github: event.target.value },
                    },
                  }))
                }
                placeholder="URL do GitHub"
              />
              <Input
                value={brain.profile.links.linkedin ?? ""}
                onChange={(event) =>
                  setBrain((prev) => ({
                    ...prev,
                    profile: {
                      ...prev.profile,
                      links: { ...prev.profile.links, linkedin: event.target.value },
                    },
                  }))
                }
                placeholder="URL do LinkedIn"
              />
              <Input
                value={brain.profile.stacks.join(", ")}
                onChange={(event) =>
                  setBrain((prev) => ({
                    ...prev,
                    profile: {
                      ...prev.profile,
                      stacks: event.target.value
                        .split(",")
                        .map((item) => item.trim())
                        .filter(Boolean),
                    },
                  }))
                }
                placeholder="Stacks foco"
              />
              <div className="flex justify-end">
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => void syncGithub()} disabled={importingGithub}>
                    {importingGithub ? "Importando GitHub..." : "Sincronizar GitHub"}
                  </Button>
                  <Button variant="outline" onClick={() => void syncLinkedin()} disabled={importingLinkedin}>
                    {importingLinkedin ? "Importando LinkedIn..." : "Sincronizar LinkedIn"}
                  </Button>
                </div>
              </div>
            </div>

            <div className="grid gap-3 rounded-xl border border-zinc-800 bg-zinc-950/70 p-4">
              {profileSignals.map((signal) => (
                <div key={signal.label}>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">{signal.label}</div>
                  <div className="mt-1 text-sm text-zinc-200">{signal.value}</div>
                </div>
              ))}
            </div>
          </Card>

          <Card className="space-y-4">
            <h3 className="text-lg font-medium">Memoria derivada</h3>
            <div className="space-y-3">
              {brain.memory_items.length === 0 ? (
                <p className="text-sm text-zinc-500">A IA ainda nao consolidou memorias permanentes.</p>
              ) : (
                brain.memory_items.map((item) => (
                  <div key={item.id} className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm font-medium text-zinc-100">{item.title}</div>
                      <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">
                        {item.kind} · {Math.round(item.confidence * 100)}%
                      </div>
                    </div>
                    <p className="mt-2 text-sm text-zinc-300">{item.content}</p>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Card className="space-y-4">
            <h3 className="text-lg font-medium">Revisao pendente</h3>
            <div className="space-y-3">
              {brain.conflicts.length === 0 ? (
                <p className="text-sm text-zinc-500">Nenhum conflito relevante entre chat, GitHub e LinkedIn.</p>
              ) : (
                brain.conflicts.map((conflict) => (
                  <div key={conflict.id} className="rounded-xl border border-amber-900/60 bg-amber-950/20 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm font-medium text-zinc-100">{conflict.summary}</div>
                      <div className="text-[11px] uppercase tracking-[0.18em] text-amber-300">
                        {Math.round(conflict.confidence * 100)}%
                      </div>
                    </div>
                    <p className="mt-2 text-sm text-zinc-300">{conflict.recommended_action}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {conflict.values.map((value) => (
                        <Button
                          key={value}
                          variant="outline"
                          disabled={resolvingConflictId === conflict.id}
                          onClick={() => void confirmConflictValue(conflict.field, value, conflict.id)}
                          className="h-auto rounded-full px-3 py-1 text-xs"
                        >
                          {value}
                        </Button>
                      ))}
                    </div>
                    <div className="mt-3 text-[11px] uppercase tracking-[0.18em] text-zinc-500">
                      Fontes: {conflict.sources.join(", ")}
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Card className="space-y-4">
            <h3 className="text-lg font-medium">Evidencias</h3>
            <div className="space-y-3">
              {brain.evidences.length === 0 ? (
                <p className="text-sm text-zinc-500">Ainda nao existem evidencias registradas.</p>
              ) : (
                brain.evidences.slice(0, 8).map((evidence) => (
                  <div key={evidence.id} className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm font-medium text-zinc-100">{evidence.title}</div>
                      <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">{evidence.source}</div>
                    </div>
                    <p className="mt-2 text-sm text-zinc-300">{evidence.content}</p>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
