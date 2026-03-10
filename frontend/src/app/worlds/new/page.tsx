"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function NewWorldPage() {
  const router = useRouter();

  const [worldName, setWorldName] = useState("");
  const [heroName, setHeroName] = useState("");
  const [seed, setSeed] = useState("0");
  const [loading, setLoading] = useState(false);
  const [username, setUsername] = useState("");
  const [userEmail, setUserEmail] = useState("");

  useEffect(() => {
    const storedUsername = localStorage.getItem("username");
    const storedEmail = localStorage.getItem("user_email");

    if (storedUsername) setUsername(storedUsername);
    if (storedEmail) setUserEmail(storedEmail);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);

    const res = await fetch("http://localhost:8000/api/worlds", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: Number(localStorage.getItem("user_id")),
        world_name: worldName,
        hero_name: heroName,
        seed: Number(seed),
      }),
    });

    if (!res.ok) {
      setLoading(false);
      throw new Error("世界作成に失敗しました");
    }

    const json = await res.json();
    setLoading(false);
    router.push(`/worlds/${json.world_id}`);
  }

  return (
    <main style={{ padding: "24px", fontFamily: "sans-serif" }}>
      <div style={{ marginBottom: "24px" }}>
        <a
          href="/worlds"
          style={{
            display: "inline-block",
            marginBottom: "16px",
            textDecoration: "none",
            color: "inherit",
            border: "1px solid #ccc",
            borderRadius: "8px",
            padding: "8px 12px",
          }}
        >
          ← 世界一覧へ戻る
        </a>

        <h1 style={{ fontSize: "28px", marginBottom: "8px" }}>新しい世界を作成</h1>
        {username && <p style={{ marginBottom: "4px" }}>ユーザー名: {username}</p>}
        {userEmail && <p>メール: {userEmail}</p>}
      </div>

      <form onSubmit={handleSubmit} style={{ display: "grid", gap: "12px", maxWidth: "480px" }}>
        <div>
          <label>世界名</label>
          <br />
          <input
            value={worldName}
            onChange={(e) => setWorldName(e.target.value)}
            style={{ width: "100%", padding: "8px" }}
          />
        </div>

        <div>
          <label>主人公名</label>
          <br />
          <input
            value={heroName}
            onChange={(e) => setHeroName(e.target.value)}
            style={{ width: "100%", padding: "8px" }}
          />
        </div>

        <div>
          <label>seed</label>
          <br />
          <input
            value={seed}
            onChange={(e) => setSeed(e.target.value)}
            style={{ width: "100%", padding: "8px" }}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "10px 14px",
            border: "1px solid #ccc",
            borderRadius: "8px",
            background: "white",
            color: "black",
            cursor: "pointer",
          }}
        >
          {loading ? "作成中..." : "作成する"}
        </button>
      </form>
    </main>
  );
}