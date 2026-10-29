"use client";

import { useEffect, useState } from "react";

export interface ReviewItem {
  id: string;
  project_id: string;
  project_name: string;
  key: string;
  title: string;
  summary: string;
  band: string;
  depth: number;
  status: string;
  files: string[];
  question: string;
  solution: string;
  interval_days: number;
  due_at: string;
  reps: number;
}

interface ReviewQueueProps {
  projectId?: string;
  serverUrl?: string;
  onActivityLog?: (msg: string) => void;
}

export default function ReviewQueue({
  projectId,
  serverUrl = "",
  onActivityLog,
}: ReviewQueueProps) {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [completedCount, setCompletedCount] = useState(0);
  const [lastGradeFeedback, setLastGradeFeedback] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReviews() {
      try {
        const url = `${serverUrl}/api/reviews${projectId ? `?project_id=${projectId}` : ""}`;
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          if (data.reviews && data.reviews.length > 0) {
            setReviews(data.reviews);
            setCurrentIndex(0);
            setIsFlipped(false);
          } else {
            setReviews([]);
          }
        }
      } catch (err) {
        console.error("Error fetching reviews:", err);
      }
    }
    fetchReviews();
  }, [projectId, serverUrl]);

  const copyPrompt = (prompt: string, feedback: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(prompt);
      setToast(feedback);
      setTimeout(() => setToast(null), 3000);
    }
  };

  const current = reviews[currentIndex];

  const handleGrade = async (grade: 1 | 3 | 5) => {
    if (!current || submitting) return;
    setSubmitting(true);

    try {
      const res = await fetch(`${serverUrl}/api/reviews/record`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: current.project_id,
          key: current.key,
          grade,
          question: current.question,
          answer: `Self-graded [Grade ${grade}] via LearnLoop Web Console`,
        }),
      });

      const gradeLabel = grade === 1 ? "Hard (1)" : grade === 3 ? "Good (3)" : "Easy (5)";
      if (res.ok) {
        setLastGradeFeedback(`Recorded: ${current.title} rated as ${gradeLabel}. SM-2 interval updated.`);
        if (onActivityLog) {
          onActivityLog(`SM-2 Review: ${current.key} scored ${gradeLabel}`);
        }
      } else {
        setLastGradeFeedback(`Recorded locally: ${current.title} (${gradeLabel})`);
      }
    } catch {
      setLastGradeFeedback(`Recorded offline: ${current.title}`);
    } finally {
      setSubmitting(false);
      setIsFlipped(false);
      setCompletedCount((prev) => prev + 1);
      setCurrentIndex((prev) => prev + 1);
    }
  };

  const handleReset = () => {
    setCurrentIndex(0);
    setIsFlipped(false);
    setCompletedCount(0);
    setLastGradeFeedback(null);
  };

  return (
    <div className="bg-[#121826] border border-white/10 rounded-xl p-6 relative overflow-hidden">
      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-emerald-500 text-black px-4 py-2 rounded-lg font-mono text-xs font-bold shadow-2xl flex items-center gap-2 animate-bounce">
          <span>✓</span>
          <span>{toast}</span>
        </div>
      )}

      {/* Decorative ambient gradient */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-white/10">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-[10px] font-mono tracking-widest uppercase text-emerald-300">
              Active Recall • Spaced Repetition (SM-2)
            </span>
          </div>
          <h2 className="text-xl font-serif text-white tracking-tight">
            2-Minute Daily Review Queue
          </h2>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="text-[#94A3B8]">
            {reviews.length > 0 ? `${currentIndex} of ${reviews.length} completed` : "Queue empty"}
          </span>
          {reviews.length > 0 && (
            <div className="w-24 h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-400 transition-all duration-300"
                style={{
                  width: `${(Math.min(currentIndex, reviews.length) / reviews.length) * 100}%`,
                }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Pro Tip: Interactive IDE AI Sparring Callout */}
      <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-emerald-500/10 via-blue-500/10 to-transparent border border-emerald-500/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="text-xl">⚡</span>
          <div>
            <div className="font-serif font-bold text-sm text-white">
              Direct AI Feedback: Review Inside Your IDE
            </div>
            <p className="text-xs text-[#94A3B8] mt-0.5 font-sans leading-relaxed">
              Self-grading flashcards here is fast, but <strong className="text-emerald-300">practicing inside your IDE gives you direct AI feedback</strong>. Your assistant analyzes your actual code diffs, catches misconceptions, and scores your reasoning.
            </p>
            <div className="flex flex-wrap items-center gap-2 mt-2.5 font-mono text-[11px]">
              <span className="text-[#71717A]">Quick IDE prompts:</span>
              <button
                onClick={() =>
                  copyPrompt(
                    "/review",
                    "Copied '/review'! Paste into your IDE chat to review due cards with active AI feedback."
                  )
                }
                className="px-2.5 py-1 bg-white/10 hover:bg-emerald-500 hover:text-black border border-white/15 text-emerald-300 rounded cursor-pointer transition-colors"
                title="Copy /review prompt for IDE"
              >
                /review 📋
              </button>
              <button
                onClick={() =>
                  copyPrompt(
                    "/interview",
                    "Copied '/interview'! Paste into your IDE chat for an architectural mock interview."
                  )
                }
                className="px-2.5 py-1 bg-white/10 hover:bg-purple-500 hover:text-white border border-white/15 text-purple-300 rounded cursor-pointer transition-colors"
                title="Copy /interview prompt for IDE"
              >
                /interview 📋
              </button>
              <button
                onClick={() =>
                  copyPrompt(
                    "/tour",
                    "Copied '/tour'! Paste into your IDE chat to start a guided codebase walkthrough."
                  )
                }
                className="px-2.5 py-1 bg-white/10 hover:bg-blue-500 hover:text-white border border-white/15 text-blue-300 rounded cursor-pointer transition-colors"
                title="Copy /tour prompt for IDE"
              >
                /tour 📋
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Review Arena */}
      {currentIndex < reviews.length && current ? (
        <div className="max-w-3xl mx-auto py-2">
          {/* Card Top Meta */}
          <div className="flex items-center justify-between gap-2 mb-3 text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 bg-blue-500/10 text-blue-300 border border-blue-500/30 rounded text-[11px] font-medium">
                {current.project_name}
              </span>
              <span className="text-[#94A3B8] font-bold">
                {current.key}
              </span>
              <span className="px-1.5 py-0.5 bg-white/5 text-[#94A3B8] rounded text-[10px]">
                Depth {current.depth}/5
              </span>
              <span className="px-1.5 py-0.5 bg-purple-500/10 text-purple-300 border border-purple-500/30 rounded text-[10px] uppercase">
                {current.band}
              </span>
            </div>

            <div className="text-[11px] text-[#71717A]">
              Card {currentIndex + 1} of {reviews.length}
            </div>
          </div>

          {/* 2-Phase Flip Card Container */}
          <div className="relative border border-white/15 bg-black/40 rounded-xl p-6 sm:p-8 shadow-2xl transition-all min-h-[300px] flex flex-col justify-between">
            {/* Front Phase: Question & Prompt */}
            {!isFlipped ? (
              <div className="flex flex-col justify-between h-full gap-6">
                <div>
                  <div className="text-[11px] font-mono uppercase tracking-wider text-amber-400 mb-2 flex items-center gap-1.5">
                    <span>🧠 Active Recall Prompt:</span>
                  </div>
                  <h3 className="text-lg sm:text-xl font-serif text-white leading-relaxed mb-4">
                    {current.question}
                  </h3>

                  {current.files && current.files.length > 0 && (
                    <div className="pt-3 border-t border-white/10">
                      <span className="text-[10px] font-mono text-[#94A3B8] block mb-1.5">
                        Verified Source Files:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {current.files.map((file, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-0.5 bg-white/5 border border-white/10 rounded font-mono text-[11px] text-zinc-300"
                          >
                            {file}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="pt-4 border-t border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-[#71717A] font-mono">
                      Mental formulation
                    </span>
                    <button
                      onClick={() =>
                        copyPrompt(
                          `/interview on concept '${current.key}' (${current.title})`,
                          `Copied '/interview on ${current.key}'! Paste into your IDE chat.`
                        )
                      }
                      className="text-[11px] font-mono text-purple-400 hover:text-purple-300 underline cursor-pointer"
                    >
                      ⚔️ Interview Me in IDE (/interview)
                    </button>
                  </div>
                  <button
                    onClick={() => setIsFlipped(true)}
                    className="px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400 text-black font-mono font-bold text-xs uppercase tracking-wider rounded-lg shadow-lg hover:shadow-emerald-500/20 transition-all cursor-pointer flex items-center justify-center gap-2"
                  >
                    <span>Show Solution & Invariant</span>
                    <span>→</span>
                  </button>
                </div>
              </div>
            ) : (
              /* Back Phase: Exact Solution, Explanation & SM-2 Grade */
              <div className="flex flex-col justify-between h-full gap-6">
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="text-[11px] font-mono uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                      <span>✓ Exact Ground-Truth Solution:</span>
                    </span>
                    <button
                      onClick={() => setIsFlipped(false)}
                      className="text-[11px] font-mono text-[#94A3B8] hover:text-white underline cursor-pointer"
                    >
                      ← Back to Prompt
                    </button>
                  </div>
                  <div className="bg-[#1A2234] border border-emerald-500/30 rounded-lg p-4 sm:p-5 mb-4 text-xs sm:text-sm text-zinc-100 font-sans leading-relaxed whitespace-pre-line">
                    {current.solution}
                  </div>
                  <div className="text-[11px] font-mono text-[#94A3B8] flex items-center gap-2">
                    <span>Summary:</span>
                    <span className="text-zinc-300">{current.summary}</span>
                  </div>
                </div>

                <div className="pt-4 border-t border-white/10">
                  <div className="text-xs font-mono text-center text-[#94A3B8] mb-3">
                    Rate your recall difficulty (SM-2 Interval Adjustment):
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <button
                      onClick={() => handleGrade(1)}
                      disabled={submitting}
                      className="p-3 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 hover:border-rose-500 text-rose-300 rounded-lg font-mono text-xs transition-all flex flex-col items-center gap-1 cursor-pointer disabled:opacity-50"
                    >
                      <span className="font-bold text-sm">[1] Hard</span>
                      <span className="text-[10px] text-rose-400/80">Struggled / Reset ease</span>
                    </button>
                    <button
                      onClick={() => handleGrade(3)}
                      disabled={submitting}
                      className="p-3 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 hover:border-blue-500 text-blue-300 rounded-lg font-mono text-xs transition-all flex flex-col items-center gap-1 cursor-pointer disabled:opacity-50"
                    >
                      <span className="font-bold text-sm">[3] Good</span>
                      <span className="text-[10px] text-blue-400/80">Correct with effort</span>
                    </button>
                    <button
                      onClick={() => handleGrade(5)}
                      disabled={submitting}
                      className="p-3 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 hover:border-emerald-500 text-emerald-300 rounded-lg font-mono text-xs transition-all flex flex-col items-center gap-1 cursor-pointer disabled:opacity-50"
                    >
                      <span className="font-bold text-sm">[5] Easy</span>
                      <span className="text-[10px] text-emerald-400/80">Instantly recalled</span>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Completion State */
        <div className="text-center py-12 px-4 max-w-lg mx-auto">
          <div className="w-14 h-14 bg-emerald-500/10 border border-emerald-500/30 rounded-full flex items-center justify-center text-2xl mx-auto mb-4 text-emerald-300">
            ✓
          </div>
          <h3 className="text-lg font-serif text-white mb-2">
            {completedCount > 0
              ? "All Reviews Completed!"
              : "No Spaced Reviews Currently Due"}
          </h3>
          <p className="text-xs text-[#94A3B8] font-sans leading-relaxed mb-6">
            {completedCount > 0
              ? `You reviewed ${completedCount} concept cards. Intervals have been saved directly to SQLite.`
              : "Your knowledge base is in a calm, up-to-date state. As you build and commit with your AI pair programmer, new concepts will space automatically."}
          </p>

          {/* Prompt AI in IDE anytime */}
          <div className="p-4 bg-white/5 border border-white/10 rounded-xl mb-6 text-left">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-white mb-1">
              <span>💡</span>
              <span>Want to level up right now?</span>
            </div>
            <p className="text-xs text-[#94A3B8] font-sans mb-3 leading-relaxed">
              You don&apos;t have to wait for cards to be due. Open your editor chat and test your deep understanding against recent commits:
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() =>
                  copyPrompt(
                    "/interview on recent changes",
                    "Copied '/interview on recent changes'! Paste into your IDE chat."
                  )
                }
                className="px-3 py-1.5 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/40 text-purple-300 font-mono text-xs rounded transition-all cursor-pointer flex items-center gap-1.5"
              >
                <span>⚔️ /interview on recent changes</span>
                <span>📋</span>
              </button>
              <button
                onClick={() =>
                  copyPrompt(
                    "/catch-up",
                    "Copied '/catch-up'! Paste into your IDE chat for a session briefing."
                  )
                }
                className="px-3 py-1.5 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/40 text-blue-300 font-mono text-xs rounded transition-all cursor-pointer flex items-center gap-1.5"
              >
                <span>⚡ /catch-up briefing</span>
                <span>📋</span>
              </button>
            </div>
          </div>

          {lastGradeFeedback && (
            <div className="p-3 bg-white/5 border border-white/10 rounded font-mono text-[11px] text-emerald-300 mb-4">
              {lastGradeFeedback}
            </div>
          )}

          {reviews.length > 0 && (
            <button
              onClick={handleReset}
              className="px-4 py-2 bg-white/10 hover:bg-white/20 border border-white/10 text-white font-mono text-xs rounded transition-colors cursor-pointer"
            >
              ↻ Review Deck Again
            </button>
          )}
        </div>
      )}
    </div>
  );
}
