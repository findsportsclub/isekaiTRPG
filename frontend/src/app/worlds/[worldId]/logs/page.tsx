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

type LogItem = {
  log_id: number;
  log_type: string;
  title: string;
  body: string;
};

type LogListResponse = {
  logs: LogItem[];
};

async function getLogs(worldId: string): Promise<LogListResponse> {
  const res = await fetch(`http://localhost:8000/api/worlds/${worldId}/logs`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("ログ一覧の取得に失敗しました");
  }

  return res.json();
}

export default async function WorldLogsPage({
  params,
}: {
  params: Promise<{ worldId: string }>;
}) {
  const { worldId } = await params;
  const data = await getLogs(worldId);

  return (
    <main style={{ padding: "24px", fontFamily: "sans-serif" }}>
      <h1 style={{ fontSize: "28px", marginBottom: "16px" }}>ログ一覧</h1>

      <div style={{ display: "grid", gap: "12px" }}>
        {data.logs.map((log) => (
          <div
            key={log.log_id}
            style={{
              border: "1px solid #ccc",
              borderRadius: "12px",
              padding: "16px",
            }}
          >
            <h2 style={{ fontSize: "18px", marginBottom: "8px" }}>{log.title}</h2>
            <p>{log.body}</p>
          </div>
        ))}
      </div>
    </main>
  );
}