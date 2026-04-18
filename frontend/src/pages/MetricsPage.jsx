import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, FunnelChart, Funnel, LabelList } from "recharts";
import { ArrowLeft, Loader2 } from "lucide-react";
import { api } from "../api/client";

const COLORS = ["#4f46e5", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

export default function MetricsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/api/metrics/summary/")
      .then((d) => setData(d))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-brand-500" />
      </div>
    );
  }

  if (!data) return <div className="p-8 text-gray-500">No data yet.</div>;

  const funnelData = [
    { name: "Sessions started", value: data.funnel.started },
    { name: "Goal discovered", value: data.funnel.goal_discovered },
    { name: "Paths seen", value: data.funnel.paths_seen },
    { name: "Path selected", value: data.funnel.path_selected },
  ];

  const personaData = Object.entries(data.persona_breakdown || {}).map(([name, value]) => ({ name, value }));

  const eventData = Object.entries(data.event_counts || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([name, value]) => ({ name: name.replace(/_/g, " "), value }));

  const rejectionData = Object.entries(data.rejection_reasons || {}).map(([name, value]) => ({ name, value }));

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="max-w-5xl mx-auto">
        <button onClick={() => navigate("/coach")} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-6">
          <ArrowLeft className="w-4 h-4" /> Back to coach
        </button>
        <h1 className="text-2xl font-bold text-brand-900 mb-6">Session Metrics</h1>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Total sessions", value: data.total_sessions },
            { label: "Path selected", value: data.funnel.path_selected },
            { label: "Goal discovered", value: data.funnel.goal_discovered },
            { label: "Paths seen", value: data.funnel.paths_seen },
          ].map((s) => (
            <div key={s.label} className="card text-center">
              <div className="text-3xl font-bold text-brand-500">{s.value ?? 0}</div>
              <div className="text-xs text-gray-400 mt-1">{s.label}</div>
            </div>
          ))}
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-6">
          <div className="card">
            <h2 className="font-semibold text-gray-700 mb-4">Session Funnel</h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={funnelData} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="name" type="category" width={110} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#4f46e5" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <h2 className="font-semibold text-gray-700 mb-4">Persona Breakdown</h2>
            {personaData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={personaData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                    {personaData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : <p className="text-gray-400 text-sm">No data yet</p>}
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div className="card">
            <h2 className="font-semibold text-gray-700 mb-4">Top User Actions</h2>
            {eventData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={eventData} layout="vertical">
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis dataKey="name" type="category" width={130} tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#10b981" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-gray-400 text-sm">No events yet</p>}
          </div>

          <div className="card">
            <h2 className="font-semibold text-gray-700 mb-4">Path Rejection Reasons</h2>
            {rejectionData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={rejectionData} layout="vertical">
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis dataKey="name" type="category" width={110} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#f59e0b" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-gray-400 text-sm">No regenerations yet</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
