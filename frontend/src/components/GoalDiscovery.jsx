import { useState } from "react";
import { Loader2 } from "lucide-react";

const ALIVE_OPTIONS = [
  "Owning full product launches",
  "Solving complex technical problems",
  "Mentoring and building teams",
  "Knowing my skills are worth more than my current pay",
  "Creating things users love",
  "Working on high business impact",
];

const FRICTION_OPTIONS = [
  "Meetings about decisions already made",
  "Waiting on others to unblock me",
  "Not enough ownership",
  "Title doesn't match my impact",
  "Feeling stuck in the same role",
  "Missing strategic context",
];

const DIRECTIONS = [
  { value: "deepen", label: "Go deeper in my current field" },
  { value: "pivot", label: "Move into a different function" },
  { value: "leadership", label: "Move into leadership/management" },
  { value: "startup", label: "Start something / founding team" },
  { value: "international", label: "International opportunities" },
  { value: "explore", label: "Open - show me what fits best" },
];

const GEOGRAPHIES = ["India", "USA", "UK", "Canada", "Singapore", "Germany", "Remote/Anywhere"];

export default function GoalDiscovery({ onSubmit, isLoading }) {
  const [aliveMoments, setAliveMoments] = useState([]);
  const [frictionPoints, setFrictionPoints] = useState([]);
  const [direction, setDirection] = useState("");
  const [geography, setGeography] = useState("India");
  const [aspiration, setAspiration] = useState("");
  const [showIntl, setShowIntl] = useState(false);

  const toggle = (list, setList, value) => {
    setList((prev) => prev.includes(value) ? prev.filter((x) => x !== value) : [...prev, value]);
  };

  const handleDirectionChange = (val) => {
    setDirection(val);
    setShowIntl(val === "international");
  };

  const submit = () => {
    onSubmit({ alive_moments: aliveMoments, friction_points: frictionPoints, direction, geography, aspiration });
  };

  return (
    <div className="space-y-6 max-w-xl">
      <div>
        <h3 className="font-semibold text-gray-800 mb-3">What energises you at work?</h3>
        <div className="flex flex-wrap gap-2">
          {ALIVE_OPTIONS.map((opt) => (
            <button
              key={opt}
              onClick={() => toggle(aliveMoments, setAliveMoments, opt)}
              className={`text-sm px-3 py-1.5 rounded-full border transition-colors ${
                aliveMoments.includes(opt)
                  ? "bg-brand-500 border-brand-500 text-white"
                  : "border-gray-200 text-gray-600 hover:border-brand-300"
              }`}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>

      <div>
        <h3 className="font-semibold text-gray-800 mb-3">What causes friction for you?</h3>
        <div className="flex flex-wrap gap-2">
          {FRICTION_OPTIONS.map((opt) => (
            <button
              key={opt}
              onClick={() => toggle(frictionPoints, setFrictionPoints, opt)}
              className={`text-sm px-3 py-1.5 rounded-full border transition-colors ${
                frictionPoints.includes(opt)
                  ? "bg-orange-500 border-orange-500 text-white"
                  : "border-gray-200 text-gray-600 hover:border-orange-300"
              }`}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>

      <div>
        <h3 className="font-semibold text-gray-800 mb-3">What direction are you considering?</h3>
        <div className="grid grid-cols-2 gap-2">
          {DIRECTIONS.map((d) => (
            <button
              key={d.value}
              onClick={() => handleDirectionChange(d.value)}
              className={`text-sm px-3 py-2 rounded-lg border text-left transition-colors ${
                direction === d.value
                  ? "bg-brand-500 border-brand-500 text-white"
                  : "border-gray-200 text-gray-600 hover:border-brand-300"
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      {showIntl && (
        <div>
          <h3 className="font-semibold text-gray-800 mb-2">Which country / region?</h3>
          <select
            value={geography}
            onChange={(e) => setGeography(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {GEOGRAPHIES.map((g) => <option key={g}>{g}</option>)}
          </select>
        </div>
      )}

      <div>
        <h3 className="font-semibold text-gray-800 mb-2">Any specific role or industry in mind? <span className="text-gray-400 font-normal">(optional)</span></h3>
        <input
          type="text"
          placeholder="e.g. Product Manager at a fintech, or I'm curious about music tech"
          value={aspiration}
          onChange={(e) => setAspiration(e.target.value)}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      <button
        onClick={submit}
        disabled={!direction || isLoading}
        className="btn-primary flex items-center gap-2"
      >
        {isLoading ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating paths...</> : "Show my career paths"}
      </button>
    </div>
  );
}
