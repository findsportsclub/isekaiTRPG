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

type WorldDetailResponse = {
  world_id: number;
  world_name: string;
  hero_name: string;
  era: string;
  current_location: string;
  crisis_scores: {
    dungeon: number;
    faction: number;
    demon: number;
  };
  main_event: {
    title: string;
    state: string;
    progress: number;    
  };
  recent_rumors: string[];
};

async function getWorld(worldId: string): Promise<WorldDetailResponse> {
  const res = await fetch(`http://localhost:8000/api/worlds/${worldId}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("世界詳細の取得に失敗しました");
  }

  return res.json();
}

export default async function WorldDetailPage({
  params,
}: {
  params: Promise<{ worldId: string }>;
}) {
  const { worldId } = await params;
  const world = await getWorld(worldId);

  return (
    <main style={{ padding: "24px", fontFamily: "sans-serif" }}>
      <h1 style={{ fontSize: "32px", marginBottom: "8px" }}>
        {world.world_name}
      </h1>

      <p style={{ marginBottom: "4px" }}>主人公: {world.hero_name}</p>
      <p style={{ marginBottom: "4px" }}>時代: {world.era}</p>
      <p style={{ marginBottom: "24px" }}>現在地: {world.current_location}</p>

      <section style={{ marginBottom: "24px" }}>
        <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>危機スコア</h2>
        <ul>
          <li>ダンジョン: {world.crisis_scores.dungeon}</li>
          <li>派閥: {world.crisis_scores.faction}</li>
          <li>魔族: {world.crisis_scores.demon}</li>
        </ul>
      </section>

      <section style={{ marginBottom: "24px" }}>
        <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>メインイベント</h2>
        <p>タイトル: {world.main_event.title}</p>
        <p>状態: {world.main_event.state}</p>
        <p>進行度: {world.main_event.progress}</p>
      </section>

      <section>
        <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>最近の噂</h2>
        <ul>
          {world.recent_rumors.map((rumor, index) => (
            <li key={index}>{rumor}</li>
          ))}
        </ul>
      </section>

      <section style={{ marginTop: "24px" }}>
        <a
          href={`/worlds/${world.world_id}/action`}
          style={{
            display: "inline-block",
            padding: "12px 16px",
            border: "1px solid #ccc",
            borderRadius: "8px",
            textDecoration: "none",
            color: "inherit",
          }}
        >
          行動へ進む
        </a>
      </section>
      <section style={{ marginTop: "12px" }}>
  <a
    href={`/worlds/${world.world_id}/logs`}
    style={{
      display: "inline-block",
      padding: "12px 16px",
      border: "1px solid #ccc",
      borderRadius: "8px",
      textDecoration: "none",
      color: "inherit",
    }}
  >
    ログを見る
  </a>
  <section style={{ marginTop: "12px" }}>
  <a
    href={`/worlds/${world.world_id}/quests`}
    style={{
      display: "inline-block",
      padding: "12px 16px",
      border: "1px solid #ccc",
      borderRadius: "8px",
      textDecoration: "none",
      color: "inherit",
    }}
  >
    クエストを見る
  </a>
</section>
</section>
    </main>
  );
}