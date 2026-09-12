import { useAuth } from "@clerk/clerk-react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function useApi() {
  const { getToken } = useAuth();

  async function request(path, options = {}) {
    const token = await getToken();

    const isFormData = options.body instanceof FormData;

    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        Authorization: `Bearer ${token}`,
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(body?.detail || `Request failed (${response.status})`);
    }

    return response.json();
  }

  return {
    // Generate a quiz from pasted notes
    generateSet: (text) =>
      request("/api/generate", {
        method: "POST",
        body: JSON.stringify({ text }),
      }),

    // Generate a quiz from an uploaded PDF
    generatePdf: (file) => {
      const formData = new FormData();
      formData.append("file", file);

      return request("/api/generate-pdf", {
        method: "POST",
        body: formData,
      });
    },

    // Fetch previously generated quizzes
    fetchHistory: () => request("/api/history"),

    // Wake/check backend
    wakeServer: () => request("/api/health"),
  };
}