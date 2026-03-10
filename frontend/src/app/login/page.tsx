"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("test@example.com");
  const [loading, setLoading] = useState(false);
  const [alreadyLoggedIn, setAlreadyLoggedIn] = useState(false);

  useEffect(() => {
    const userId = localStorage.getItem("user_id");
    if (userId) {
      setAlreadyLoggedIn(true);
    }
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);

    const res = await fetch("http://localhost:8000/api/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email }),
    });

    if (!res.ok) {
      setLoading(false);
      throw new Error("ログインに失敗しました");
    }

    const json = await res.json();

    localStorage.setItem("user_id", String(json.user_id));
    localStorage.setItem("user_email", json.email);
    localStorage.setItem("username", json.username);

    setLoading(false);
    router.push("/worlds");
  }

  return (
    <main style={{ padding: "24px", fontFamily: "sans-serif" }}>
      <h1 style={{ fontSize: "28px", marginBottom: "16px" }}>ログイン</h1>

      {alreadyLoggedIn && (
        <div
          style={{
            marginBottom: "16px",
            padding: "12px",
            border: "1px solid #ccc",
            borderRadius: "8px",
          }}
        >
          <p style={{ marginBottom: "8px" }}>すでにログイン済みです。</p>
          <a
            href="/worlds"
            style={{
              display: "inline-block",
              padding: "8px 12px",
              border: "1px solid #ccc",
              borderRadius: "8px",
              textDecoration: "none",
              color: "inherit",
            }}
          >
            世界一覧へ進む
          </a>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: "grid", gap: "12px", maxWidth: "480px" }}>
        <div>
          <label>メールアドレス</label>
          <br />
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
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
          {loading ? "ログイン中..." : "ログインする"}
        </button>
      </form>
    </main>
  );
}