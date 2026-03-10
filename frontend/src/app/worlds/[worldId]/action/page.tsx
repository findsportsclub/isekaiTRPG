"use client";

import { useEffect, useState } from "react";

type ActionItem = {
  action_id: string;
  label: string;
};

type NearbyNpc = {
  npc_id: string;
  name: string;
};

type NearbyEvent = {
  event_id: string;
  title: string;
};

type MoveDestination = {
  location_id: string;
  label: string;
};

type ActionListResponse = {
  location: string;
  time_label: string;
  actions: ActionItem[];
  nearby_npcs: NearbyNpc[];
  nearby_events: NearbyEvent[];
  move_destinations: MoveDestination[];
};

type ActionExecuteResponse = {
  summary: string;
  result_type: string;
};

function toJapaneseActionLabel(label: string) {
  switch (label) {
    case "話す":
    case "Talk":
      return "話す";
    case "調べる":
    case "Inspect":
      return "調べる";
    case "移動する":
    case "Move":
      return "移動する";
    case "休む":
    case "Rest":
      return "休む";
    default:
      return label;
  }
}

function toJapaneseTimeLabel(label: string) {
  switch (label) {
    case "Morning":
    case "朝":
      return "朝";
    case "Noon":
    case "昼":
      return "昼";
    case "Evening":
    case "夕方":
      return "夕方";
    case "Night":
    case "夜":
      return "夜";
    default:
      return label;
  }
}

async function fetchActions(worldId: string): Promise<ActionListResponse> {
  const res = await fetch(`http://localhost:8000/api/worlds/${worldId}/actions`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("行動一覧の取得に失敗しました");
  }

  return res.json();
}

export default function WorldActionPage({
  params,
}: {
  params: Promise<{ worldId: string }>;
}) {
  const [worldId, setWorldId] = useState<string>("");
  const [data, setData] = useState<ActionListResponse | null>(null);
  const [result, setResult] = useState<ActionExecuteResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [showMoveOptions, setShowMoveOptions] = useState(false);
  const [showTalkOptions, setShowTalkOptions] = useState(false);

  useEffect(() => {
    params.then(async ({ worldId }) => {
      setWorldId(worldId);
      const json = await fetchActions(worldId);
      setData(json);
    });
  }, [params]);

  async function handleAction(
    actionId: string,
    targetLocation?: string,
    targetNpcId?: string
  ) {
    if (!worldId) return;

    setLoading(true);
    setResult(null);
    setShowMoveOptions(false);
    setShowTalkOptions(false);

    const res = await fetch(`http://localhost:8000/api/worlds/${worldId}/actions/execute`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        action_id: actionId,
        target_location: targetLocation ?? null,
        target_npc_id: targetNpcId ?? null,
      }),
    });

    if (!res.ok) {
      setLoading(false);
      throw new Error("行動実行に失敗しました");
    }

    const json: ActionExecuteResponse = await res.json();
    setResult(json);

    const refreshed = await fetchActions(worldId);
    setData(refreshed);

    setLoading(false);
  }

  if (!data) {
    return <main style={{ padding: "24px", fontFamily: "sans-serif" }}>読み込み中...</main>;
  }

  return (
    <main style={{ padding: "24px", fontFamily: "sans-serif" }}>
      <h1 style={{ fontSize: "28px", marginBottom: "8px" }}>行動</h1>
      <p>現在地: {data.location}</p>
      <p style={{ marginBottom: "24px" }}>時間帯: {toJapaneseTimeLabel(data.time_label)}</p>

      <section style={{ marginBottom: "24px" }}>
        <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>選べる行動</h2>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {data.actions.map((action) => (
            <button
              key={action.action_id}
              onClick={() => {
                if (action.action_id === "move") {
                  setShowMoveOptions((prev) => !prev);
                  setShowTalkOptions(false);
                } else if (action.action_id === "talk") {
                  setShowTalkOptions((prev) => !prev);
                  setShowMoveOptions(false);
                } else {
                  handleAction(action.action_id);
                }
              }}
              style={{
                padding: "10px 14px",
                border: "1px solid #ccc",
                borderRadius: "8px",
                background: "white",
                color: "black",
                cursor: "pointer",
              }}
            >
              {toJapaneseActionLabel(action.label)}
            </button>
          ))}
        </div>
      </section>

      {showMoveOptions && (
        <section
          style={{
            marginBottom: "24px",
            padding: "16px",
            border: "1px solid #ccc",
            borderRadius: "8px",
          }}
        >
          <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>移動先を選ぶ</h2>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {data.move_destinations.map((destination) => (
              <button
                key={destination.location_id}
                onClick={() => handleAction("move", destination.location_id)}
                style={{
                  padding: "10px 14px",
                  border: "1px solid #ccc",
                  borderRadius: "8px",
                  background: "white",
                  color: "black",
                  cursor: "pointer",
                }}
              >
                {destination.label}
              </button>
            ))}
          </div>
        </section>
      )}

      {showTalkOptions && (
        <section
          style={{
            marginBottom: "24px",
            padding: "16px",
            border: "1px solid #ccc",
            borderRadius: "8px",
          }}
        >
          <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>話しかける相手を選ぶ</h2>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {data.nearby_npcs.map((npc) => (
              <button
                key={npc.npc_id}
                onClick={() => handleAction("talk", undefined, npc.npc_id)}
                style={{
                  padding: "10px 14px",
                  border: "1px solid #ccc",
                  borderRadius: "8px",
                  background: "white",
                  color: "black",
                  cursor: "pointer",
                }}
              >
                {npc.name}
              </button>
            ))}
          </div>
        </section>
      )}

      {loading && <p>実行中...</p>}

      {result && (
        <section
          style={{
            marginBottom: "24px",
            padding: "16px",
            border: "1px solid #ccc",
            borderRadius: "8px",
          }}
        >
          <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>結果</h2>
          <p>{result.summary}</p>
        </section>
      )}

      <section style={{ marginBottom: "24px" }}>
        <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>周辺NPC</h2>
        <ul>
          {data.nearby_npcs.map((npc) => (
            <li key={npc.npc_id}>{npc.name}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2 style={{ fontSize: "22px", marginBottom: "8px" }}>周辺イベント</h2>
        <ul>
          {data.nearby_events.map((event) => (
            <li key={event.event_id}>{event.title}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}