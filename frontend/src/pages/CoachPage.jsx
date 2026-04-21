import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Send, RefreshCw, BarChart2, LogOut, Loader2 } from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { useProfileStore } from "../stores/profileStore";
import { useSessionStore } from "../stores/sessionStore";
import { useChatStore } from "../stores/chatStore";
import { usePathStore } from "../stores/pathStore";
import { useMetricsStore } from "../stores/metricsStore";
import { streamSSE } from "../api/client";
import GoalDiscovery from "../components/GoalDiscovery";
import PathCard from "../components/PathCard";
import clsx from "clsx";

const REJECTION_REASONS = [
  "Wrong function",
  "Wrong seniority",
  "Wrong industry",
  "Salary too low",
  "Something else",
];


// Lightweight markdown renderer.
// Handles **bold**, numbered items (1.), bullets (* or -), and nested bullets under numbered items.
function MarkdownText({ content }) {
  if (!content) return null;

  const lines = content.split("\n");
  const elements = [];
  let numberedCounter = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.trim() === "") {
      elements.push(<div key={i} className="h-1.5" />);
      numberedCounter = 0;
      continue;
    }

    // Numbered item — e.g. "1. **Title**: text" (LLM often resets to 1. each time)
    const numMatch = line.match(/^\d+\.\s+(.*)/);
    if (numMatch) {
      numberedCounter++;
      elements.push(
        <div key={i} className="flex gap-2 mt-1.5">
          <span className="font-semibold text-gray-500 shrink-0 w-5 text-right">{numberedCounter}.</span>
          <span>{renderInline(numMatch[1])}</span>
        </div>
      );
      continue;
    }

    // Bullet item (* or -) — render as indented sub-bullet
    const bulletMatch = line.match(/^[\*\-]\s+(.*)/);
    if (bulletMatch) {
      elements.push(
        <div key={i} className="flex gap-2 ml-6">
          <span className="text-gray-400 shrink-0">•</span>
          <span>{renderInline(bulletMatch[1])}</span>
        </div>
      );
      continue;
    }

    // Regular paragraph
    elements.push(<p key={i} className="leading-relaxed">{renderInline(line)}</p>);
  }

  return <div className="space-y-0.5 text-sm">{elements}</div>;
}

function renderInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

export default function CoachPage() {
  const { logout } = useAuthStore();
  const { profile, fetchProfile } = useProfileStore();
  const { session, status, currentRound, startSession, submitGoal, pathAction } = useSessionStore();
  const { turns, isStreaming, streamBuffer, addTurn, sendMessage, loadFromSession, clear: clearChat } = useChatStore();
  const { pathSets, selectedPath, forcedClose, addPathSet, selectPath, setForcedClose, currentPaths, clear: clearPaths } = usePathStore();
  const { track, flush, setSessionId } = useMetricsStore();

  const [input, setInput] = useState("");
  const [goalLoading, setGoalLoading] = useState(false);
  const [streamingOpening, setStreamingOpening] = useState(false);
  const [showRejectionPicker, setShowRejectionPicker] = useState(false);
  const [selectedRejection, setSelectedRejection] = useState("");
  const bottomRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const init = async () => {
      const p = await fetchProfile();
      if (!p) { navigate("/upload"); return; }
      const s = await startSession();
      if (!s) return;
      setSessionId(s.id);
      clearChat();
      clearPaths();
      streamOpening(s.id);
    };
    init();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, streamBuffer]);

  const streamOpening = (sessionId) => {
    setStreamingOpening(true);
    let full = "";
    streamSSE(
      `/api/sessions/${sessionId}/stream/`,
      (token) => { full += token; useChatStore.setState((s) => ({ streamBuffer: s.streamBuffer + token })); },
      () => {
        useChatStore.setState((s) => ({
          turns: [...s.turns, { role: "assistant", content: full, turn_type: "opening" }],
          streamBuffer: "",
          isStreaming: false,
        }));
        setStreamingOpening(false);
        useSessionStore.setState({ status: "OPENING_SENT" });
      },
      () => setStreamingOpening(false),
    );
  };

  const handleGoalSubmit = async (goal) => {
    setGoalLoading(true);
    const { session: sess } = useSessionStore.getState();
    try {
      const data = await submitGoal(sess.id, goal);
      addPathSet(1, data.paths);
      // Inject path cards into the turn stream at this position
      addTurn({ role: "paths", turn_type: "paths", round: 1, paths: data.paths });
      track("alive_moment_selected", { moments: goal.alive_moments });
      track("direction_selected", { direction: goal.direction });
    } catch (e) {
      console.error(e);
    } finally {
      setGoalLoading(false);
    }
  };

  const handleSelectPath = async (path) => {
    const { session: sess } = useSessionStore.getState();
    try {
      await pathAction(sess.id, { type: "select", path_id: path.id });
      selectPath(path);
      track("path_card_selected", { path_id: path.id, round: currentRound });
      flush();
    } catch (e) {
      console.error(e);
    }
  };

  const handleRegenerate = async () => {
    if (!selectedRejection) return;
    const { session: sess } = useSessionStore.getState();
    try {
      const data = await pathAction(sess.id, { type: "regenerate", reason: selectedRejection });
      if (data.forced_close) {
        setForcedClose(data.message);
        addTurn({ role: "assistant", content: data.message, turn_type: "forced_close" });
      } else {
        addPathSet(data.round, data.paths);
        // Inject new path set into the turn stream
        addTurn({ role: "paths", turn_type: "paths", round: data.round, paths: data.paths });
        track("path_regenerated", { round: data.round, rejection_reason: selectedRejection });
      }
      setShowRejectionPicker(false);
      setSelectedRejection("");
    } catch (e) {
      console.error(e);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    const msg = input.trim();
    setInput("");
    const { session: sess } = useSessionStore.getState();
    await sendMessage(sess.id, msg);
    track("free_text_sent", { length_bucket: msg.split(" ").length < 20 ? "short" : "medium" });
  };

  // The latest paths turn (for showing the regenerate button on)
  const latestPathsTurnIndex = turns.reduce((acc, t, i) => t.turn_type === "paths" ? i : acc, -1);
  const isClosed = status === "CLOSED";
  const showGoalDiscovery = status === "OPENING_SENT" && !goalLoading && latestPathsTurnIndex === -1;

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-white border-b border-gray-100 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <h1 className="font-bold text-brand-900 text-lg">Career Coach</h1>
        <div className="flex gap-3">
          <button onClick={() => navigate("/metrics")} className="btn-secondary text-sm flex items-center gap-1.5 py-1.5 px-3">
            <BarChart2 className="w-4 h-4" /> Metrics
          </button>
          <button onClick={() => { logout(); navigate("/auth"); }} className="btn-secondary text-sm flex items-center gap-1.5 py-1.5 px-3">
            <LogOut className="w-4 h-4" /> Sign out
          </button>
        </div>
      </header>

      <main className="flex-1 max-w-3xl mx-auto w-full px-4 py-6 space-y-4">
        {turns.map((turn, i) => {
          if (turn.turn_type === "paths") {
            const isLatest = i === latestPathsTurnIndex;
            return (
              <PathsInline
                key={i}
                paths={turn.paths}
                round={turn.round}
                isLatest={isLatest && !isClosed}
                isClosed={isClosed}
                showRejectionPicker={isLatest && showRejectionPicker}
                selectedRejection={selectedRejection}
                onRejectionSelect={setSelectedRejection}
                onRegenerate={handleRegenerate}
                onCancelRegenerate={() => { setShowRejectionPicker(false); setSelectedRejection(""); }}
                onShowRejectionPicker={() => setShowRejectionPicker(true)}
                onSelectPath={handleSelectPath}
                currentRound={currentRound}
              />
            );
          }
          return <ChatBubble key={i} turn={turn} />;
        })}

        {/* Streaming buffer */}
        {(isStreaming || streamingOpening) && streamBuffer && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 max-w-[80%] shadow-sm text-sm text-gray-700 streaming-cursor">
              <MarkdownText content={streamBuffer} />
            </div>
          </div>
        )}

        {/* Loading spinner for opening */}
        {streamingOpening && !streamBuffer && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-100 rounded-2xl px-4 py-3 shadow-sm">
              <Loader2 className="w-4 h-4 animate-spin text-brand-500" />
            </div>
          </div>
        )}

        {/* Goal discovery */}
        {showGoalDiscovery && (
          <div className="card">
            <p className="text-sm font-medium text-gray-500 mb-4">Let me understand what you're looking for:</p>
            <GoalDiscovery onSubmit={handleGoalSubmit} isLoading={goalLoading} />
          </div>
        )}

        {goalLoading && (
          <div className="flex items-center gap-2 text-sm text-gray-500 py-2">
            <Loader2 className="w-4 h-4 animate-spin text-brand-500" />
            Generating your career paths...
          </div>
        )}

        {/* Selected path confirmation */}
        {selectedPath && (
          <div className="card bg-green-50 border-green-200">
            <p className="font-semibold text-green-800 mb-1">Path selected: {selectedPath.role}</p>
            <p className="text-sm text-green-600">{selectedPath.why_you_fit}</p>
            <p className="text-sm text-gray-500 mt-2">Ask me anything about this path, what to do in week 1, or skills to build.</p>
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      {/* Chat input */}
      <div className="sticky bottom-0 bg-white border-t border-gray-100 px-4 py-3">
        <form onSubmit={handleSendMessage} className="max-w-3xl mx-auto flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about your career..."
            disabled={isStreaming || streamingOpening || (!session)}
            className="flex-1 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:bg-gray-50"
          />
          <button type="submit" disabled={!input.trim() || isStreaming || streamingOpening} className="btn-primary px-4 py-2.5">
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}

function PathsInline({
  paths, round, isLatest, isClosed,
  showRejectionPicker, selectedRejection,
  onRejectionSelect, onRegenerate, onCancelRegenerate, onShowRejectionPicker,
  onSelectPath, currentRound,
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-gray-500">
          {round === 0 ? "Your requested path" : round > 3 ? "Your 3 career paths" : round > 1 ? `Round ${round} of 3 — Your 3 career paths` : "Your 3 career paths"}
        </p>
        {isLatest && !showRejectionPicker && round > 0 && (
          <button
            onClick={onShowRejectionPicker}
            className="btn-secondary text-sm flex items-center gap-1.5 py-1.5 px-3"
          >
            <RefreshCw className="w-4 h-4" />
            {currentRound >= 3 ? "Get recommendation" : "Suggest different paths"}
          </button>
        )}
      </div>

      {isLatest && showRejectionPicker && (
        <div className="card mb-4 bg-orange-50 border-orange-100">
          <p className="text-sm font-medium text-gray-700 mb-3">What wasn't right about these paths?</p>
          <div className="flex flex-wrap gap-2 mb-3">
            {REJECTION_REASONS.map((r) => (
              <button
                key={r}
                onClick={() => onRejectionSelect(r)}
                className={`text-sm px-3 py-1.5 rounded-full border transition-colors ${
                  selectedRejection === r
                    ? "bg-orange-500 border-orange-500 text-white"
                    : "border-gray-200 text-gray-600 hover:border-orange-300 bg-white"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={onRegenerate} disabled={!selectedRejection} className="btn-primary text-sm">
              {currentRound >= 3 ? "Get best recommendation" : "Show new paths"}
            </button>
            <button onClick={onCancelRegenerate} className="btn-secondary text-sm">Cancel</button>
          </div>
        </div>
      )}

      <div className="grid gap-4">
        {paths.map((path) => (
          <PathCard key={path.id} path={path} round={round} onSelect={onSelectPath} disabled={isClosed || !isLatest} />
        ))}
      </div>
    </div>
  );
}

function ChatBubble({ turn }) {
  const isUser = turn.role === "user";
  const isOffTopic = turn.turn_type === "off_topic";
  const isForcedClose = turn.turn_type === "forced_close";

  return (
    <div className={clsx("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={clsx(
          "rounded-2xl px-4 py-3 max-w-[80%] text-sm shadow-sm",
          isUser
            ? "bg-brand-500 text-white rounded-tr-sm"
            : isOffTopic
            ? "bg-gray-100 text-gray-500 rounded-tl-sm border border-gray-200 italic"
            : isForcedClose
            ? "bg-brand-50 text-brand-900 rounded-tl-sm border border-brand-200 font-medium"
            : "bg-white text-gray-700 rounded-tl-sm border border-gray-100"
        )}
      >
        {isUser ? turn.content : <MarkdownText content={turn.content} />}
      </div>
    </div>
  );
}
