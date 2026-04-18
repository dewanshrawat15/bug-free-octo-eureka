import { CheckCircle, TrendingUp, Clock, Globe } from "lucide-react";
import clsx from "clsx";

export default function PathCard({ path, round, onSelect, disabled }) {
  return (
    <div className="card hover:border-brand-300 hover:shadow-md transition-all group">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900 text-base leading-tight">{path.role}</h3>
          <p className="text-gray-400 text-sm mt-0.5">{path.company_type}</p>
        </div>
        <span className="text-brand-500 font-semibold text-sm whitespace-nowrap ml-4">{path.salary_range}</span>
      </div>

      <p className="text-gray-600 text-sm mb-4 leading-relaxed">{path.why_you_fit}</p>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div>
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">You have</p>
          <div className="flex flex-wrap gap-1">
            {path.skills_you_have?.slice(0, 3).map((s) => (
              <span key={s} className="bg-green-50 text-green-700 text-xs px-2 py-0.5 rounded-full">{s}</span>
            ))}
          </div>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">To learn</p>
          <div className="flex flex-wrap gap-1">
            {path.skills_gap?.slice(0, 3).map((s) => (
              <span key={s} className="bg-orange-50 text-orange-700 text-xs px-2 py-0.5 rounded-full">{s}</span>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4 text-xs text-gray-400 mb-4">
        {path.transition_timeline && (
          <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{path.transition_timeline}</span>
        )}
        {path.market_demand && (
          <span className="flex items-center gap-1"><TrendingUp className="w-3 h-3" />{path.market_demand}</span>
        )}
        {path.target_country && (
          <span className="flex items-center gap-1"><Globe className="w-3 h-3" />{path.target_country}</span>
        )}
      </div>

      {path.visa_notes && (
        <p className="text-xs text-blue-600 bg-blue-50 rounded-lg px-3 py-1.5 mb-4">{path.visa_notes}</p>
      )}

      <button
        onClick={() => onSelect(path)}
        disabled={disabled}
        className="btn-primary w-full text-sm"
      >
        Select this path
      </button>
    </div>
  );
}
