import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";

export default function AuthCallback() {
  const navigate = useNavigate();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash || "";
    const m = hash.match(/session_id=([^&]+)/);
    const sessionId = m ? decodeURIComponent(m[1]) : null;

    if (!sessionId) {
      navigate("/login", { replace: true });
      return;
    }

    (async () => {
      try {
        const { data } = await api.post("/auth/session", { session_id: sessionId });
        window.history.replaceState({}, "", "/");
        navigate("/", { replace: true, state: { user: data.user } });
      } catch (e) {
        console.error("Auth exchange failed", e);
        navigate("/login", { replace: true });
      }
    })();
  }, [navigate]);

  return (
    <div className="min-h-screen w-full bg-[#0B0B0E] flex items-center justify-center font-body text-[#9A8868]">
      <div className="flex items-center gap-3">
        <span className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse" />
        <span className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse [animation-delay:150ms]" />
        <span className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse [animation-delay:300ms]" />
        <span className="ml-3 text-sm">signing you in</span>
      </div>
    </div>
  );
}
