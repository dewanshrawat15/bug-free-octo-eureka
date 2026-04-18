import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, FileText, Loader2 } from "lucide-react";
import { useProfileStore } from "../stores/profileStore";
import { useMetricsStore } from "../stores/metricsStore";

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef(null);

  const { uploadResume, isLoading } = useProfileStore();
  const { track } = useMetricsStore();
  const navigate = useNavigate();

  const handleFile = (f) => {
    if (!f?.name.endsWith(".pdf")) {
      setError("Please upload a PDF file.");
      return;
    }
    setError("");
    setFile(f);
  };

  const submit = async () => {
    if (!file) return;
    track("session_started", { file_name: file.name });
    try {
      await uploadResume(file);
      navigate("/coach");
    } catch (e) {
      track("resume_upload_failed", { error: e.message });
      setError(e.message || "Upload failed. Please try again.");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 to-white px-4">
      <div className="card w-full max-w-lg text-center">
        <h1 className="text-2xl font-bold text-brand-900 mb-1">Career Coach</h1>
        <p className="text-gray-500 text-sm mb-8">
          Upload your resume and get personalised career paths in minutes.
        </p>

        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
          onClick={() => fileRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-10 cursor-pointer transition-colors mb-4 ${
            dragging ? "border-brand-500 bg-brand-50" : "border-gray-200 hover:border-brand-300"
          }`}
        >
          {file ? (
            <div className="flex items-center justify-center gap-3 text-brand-600">
              <FileText className="w-6 h-6" />
              <span className="font-medium">{file.name}</span>
            </div>
          ) : (
            <>
              <Upload className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-600 font-medium">Drop your resume here</p>
              <p className="text-gray-400 text-sm mt-1">PDF only</p>
            </>
          )}
        </div>
        <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={(e) => handleFile(e.target.files[0])} />

        {error && <p className="text-red-500 text-sm mb-3">{error}</p>}

        <button onClick={submit} disabled={!file || isLoading} className="btn-primary w-full flex items-center justify-center gap-2">
          {isLoading ? <><Loader2 className="w-4 h-4 animate-spin" /> Analysing...</> : "Analyse my Profile"}
        </button>
      </div>
    </div>
  );
}
