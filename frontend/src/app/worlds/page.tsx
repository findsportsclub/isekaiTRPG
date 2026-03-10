"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type WorldListItem = {
  world_id: number;
  world_name: string;
  hero_name: string;
  era: string;
  current_location: string;
};

type WorldListResponse = {
  worlds: WorldListItem[];
};

export default function WorldsPage() {
  const router = useRouter();

  const [worlds, setWorlds] = useState<WorldListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [username, setUsername] = useState("");
  const [userEmail, setUserEmail] = useState("");

  useEffect(() => {
    const userId = localStorage.getItem("user_id");
    const storedUsername = localStorage.getItem("username");
    const storedEmail = localStorage.getItem("user_email");

    if (storedUsername) setUsername(storedUsername);
    if (storedEmail) setUserEmail(storedEmail);

    if (!userId) {
      setLoading(false);
      return;
    }

    fetch(`http://localhost:8000/api/users/${userId}/worlds`, {
      cache: "no-store",
    })
      .then((res) => {
        if (!res.ok) {
          throw new Error("世界一覧の取得に失敗しました");
        }
        return res.json();
      })
      .then((data: WorldListResponse) => {
        setWorlds(data.worlds);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, []);

  function handleLogout() {
    localStorage.removeItem("user_id");
    localStorage.removeItem("user_email");
    localStorage.removeItem("username");
    router.push("/login");
  }

  return (
    <main style={{ padding: "24px", fontFamily: "sans-serif" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "16px",
          marginBottom: "24px",
        }}
      >
        <div>
          <h1 style={{ fontSize: "28px", marginBottom: "8px" }}>世界一覧</h1>
          {username && <p style={{ marginBottom: "4px" }}>ユーザー名: {username}</p>}
          {userEmail && <p>メール: {userEmail}</p>}
        </div>

        <button
          onClick={handleLogout}
          style={{
            padding: "10px 14px",
            border: "1px solid #ccc",
            borderRadius: "8px",
            background: "white",
            color: "black",
            cursor: "pointer",
          }}
        >
          ログアウト
        </button>
      </div>

      <div style={{ marginBottom: "16px" }}>
        <a
          href="/worlds/new"
          style={{
            display: "inline-block",
            padding: "10px 14px",
            border: "1px solid #ccc",
            borderRadius: "8px",
            textDecoration: "none",
            color: "inherit",
          }}
        >
          ＋ 新しい世界を作る
        </a>
      </div>

      {loading ? (
        <p>読み込み中...</p>
      ) : worlds.length === 0 ? (
        <p>まだ世界がありません。新しい世界を作成してください。</p>
      ) : (
        <div style={{ display: "grid", gap: "12px" }}>
          {worlds.map((world) => (
            <Link
              key={world.world_id}
              href={`/worlds/${world.world_id}`}
              style={{
                border: "1px solid #ccc",
                borderRadius: "12px",
                padding: "16px",
                display: "block",
                color: "inherit",
                textDecoration: "none",
              }}
            >
              <h2 style={{ fontSize: "20px", marginBottom: "8px" }}>
                {world.world_name}
              </h2>
              <p>主人公: {world.hero_name}</p>
              <p>時代: {world.era}</p>
              <p>現在地: {world.current_location}</p>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}