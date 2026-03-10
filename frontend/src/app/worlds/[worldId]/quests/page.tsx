type QuestItem = {
  quest_id: string;
  category: string;
  title: string;
  status: string;
  description: string;
  progress: number;
};

type QuestListResponse = {
  quests: QuestItem[];
};

async function getQuests(worldId: string): Promise<QuestListResponse> {
  const res = await fetch(`http://localhost:8000/api/worlds/${worldId}/quests`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("クエスト一覧の取得に失敗しました");
  }

  return res.json();
}

function toJapaneseStatus(status: string) {
  switch (status) {
    case "ACTIVE":
      return "進行中";
    case "URGENT":
      return "緊急";
    case "CLEARED":
      return "達成";
    case "FAILED":
      return "失敗";
    default:
      return status;
  }
}

export default async function WorldQuestsPage({
  params,
}: {
  params: Promise<{ worldId: string }>;
}) {
  const { worldId } = await params;
  const data = await getQuests(worldId);

  return (
    <main style={{ padding: "24px", fontFamily: "sans-serif" }}>
      <a
        href={`/worlds/${worldId}`}
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
        ← 世界詳細へ戻る
      </a>

      <h1 style={{ fontSize: "28px", marginBottom: "16px" }}>クエスト一覧</h1>

      <div style={{ display: "grid", gap: "12px" }}>
        {data.quests.map((quest) => (
          <div
            key={quest.quest_id}
            style={{
              border: "1px solid #ccc",
              borderRadius: "12px",
              padding: "16px",
            }}
          >
            <h2 style={{ fontSize: "20px", marginBottom: "8px" }}>{quest.title}</h2>
            <p style={{ marginBottom: "8px" }}>種別: {quest.category === "main" ? "主" : "副"}</p>
            <p style={{ marginBottom: "8px" }}>状態: {toJapaneseStatus(quest.status)}</p>
            <p style={{ marginBottom: "8px" }}>進行度: {quest.progress}</p>
            <p>{quest.description}</p>
          </div>
        ))}
      </div>
    </main>
  );
}