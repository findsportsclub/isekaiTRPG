import Link from "next/link";

export default function HomePage() {
  return (
    <main style={{ padding: "24px", fontFamily: "sans-serif" }}>
      <h1 style={{ fontSize: "32px", marginBottom: "16px" }}>
        異世界TRPG
      </h1>

      <p style={{ marginBottom: "24px" }}>
        並行世界を巡る物語生成TRPGの試作版です。
      </p>

      <Link
        href="/login"
        style={{
          display: "inline-block",
          padding: "12px 16px",
          border: "1px solid #ccc",
          borderRadius: "8px",
          textDecoration: "none",
          color: "inherit",
        }}
      >
        ログインへ
      </Link>
    </main>
  );
}