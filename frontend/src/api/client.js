const API_BASE = import.meta.env.VITE_API_URL || "";

const getToken = () => {
  try {
    const stored = JSON.parse(localStorage.getItem("auth-storage") || "{}");
    return stored?.state?.token || null;
  } catch {
    return null;
  }
};

async function request(method, path, body, isFormData = false) {
  const token = getToken();
  const headers = token ? { Authorization: `Token ${token}` } : {};
  if (!isFormData) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw Object.assign(new Error(err.error || res.statusText), { status: res.status, data: err });
  }
  return res.json();
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
  upload: (path, form) => request("POST", path, form, true),
};

export async function streamSSE(path, onToken, onDone, onError) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Token ${token}` } : {},
  });

  if (!res.ok) {
    onError?.(new Error(`HTTP ${res.status}`));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.token) onToken(data.token);
          if (data.done) onDone?.(data);
          if (data.error) onError?.(new Error(data.error));
        } catch {}
      }
    }
  } catch (e) {
    onError?.(e);
  }
}
