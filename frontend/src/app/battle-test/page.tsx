"use client";

import { useEffect, useMemo, useState } from "react";

type BattleCreateResponse = {
  battle_id: number;
  state: string;
  turn_no: number;
};

type CombatantCreateResponse = {
  combatant_id: number;
  display_name: string;
  side: string;
  state: string;
};

type BattleCombatant = {
  combatant_id: number;
  display_name: string;
  side: string;
  role: string;
  hp_current: number;
  hp_max: number;
  mp_current: number;
  mp_max: number;
  state: string;
  defend_active: boolean;
  defend_used_tags_json: string;
  has_acted_this_turn: boolean;
  range_band: string;
  position_tags_json: string;
  controller_type: string;
  ai_profile_key: string;
  current_order_text: string;
  available_skill_keys_json: string;
  available_spell_keys_json: string;
  equipped_item_keys_json: string;
};

type BattleDetailResponse = {
  battle_id: number;
  world_id: number;
  location_id: string;
  battlefield_id: number | null;
  battle_type: string;
  source_type: string;
  state: string;
  turn_no: number;
  objective_type: string;
  combatants: BattleCombatant[];
};

type BattleActionLog = {
  action_log_id: number;
  turn_no: number;
  declaration_id: number | null;
  actor_combatant_id: number;
  actor_name: string;
  target_combatant_id: number | null;
  target_name: string | null;
  result_type: string;
  hit_success: boolean;
  crit_success: boolean;
  guard_success: boolean;
  evade_success: boolean;
  damage_value: number;
  hp_after: number;
  declared_tactic_text: string;
  used_tags_json: string;
  narrative_result: string;
  ai_reason_summary: string;
  order_applied_text: string;
};

type AdvanceTurnResponse = {
  battle_id: number;
  turn_no: number;
  state: string;
  acted_enemy_count: number;
};

type TurnOrderItem = {
  combatant_id: number;
  display_name: string;
  side: string;
  spd: number;
  state: string;
  has_acted: boolean;
};

type BattleTurnOrderResponse = {
  battle_id: number;
  turn_no: number;
  order: TurnOrderItem[];
};

type CompanionOrderResponse = {
  battle_id: number;
  target_combatant_id: number;
  order_text: string;
  priority: string;
  accepted: boolean;
};

type CombatAiProfileResponse = {
  profile_key: string;
  controller_type: string;
  combat_role: string;
  behavior_mode: string;
  base_traits_json: string;
  dynamic_traits_json: string;
  growth_stats_json: string;
  relationship_modifiers_json: string;
  temporary_state_tags_json: string;
  combat_experience: string;
  tactical_judgment: string;
  command_obedience: number;
  command_comprehension: number;
  teamwork_skill: number;
  morale: number;
  panic_action_rate: number;
  hesitation_rate: number;
  misplay_tendency: number;
  communication_method: string;
  noise_tolerance: number;
  requires_line_of_sight_for_command: boolean;
  current_order_text: string;
  current_order_priority: string;
};

type UsableSkillItem = {
  skill_key: string;
  name: string;
  category: string;
  target_type: string;
  resource_type: string;
  resource_cost: number;
  cooldown_turns: number;
  current_cooldown: number;
  usable: boolean;
  reason: string;
};

type UsableSpellItem = {
  spell_key: string;
  name: string;
  category: string;
  target_type: string;
  resource_type: string;
  resource_cost: number;
  cooldown_turns: number;
  current_cooldown: number;
  usable: boolean;
  reason: string;
};

type CombatantUsablesResponse = {
  battle_id: number;
  combatant_id: number;
  skill_items: UsableSkillItem[];
  spell_items: UsableSpellItem[];
};

type CombinedUsableAction =
  | (UsableSkillItem & { kind: "skill"; action_key: string })
  | (UsableSpellItem & { kind: "spell"; action_key: string });

type TargetOption = {
  combatant_id: number;
  label: string;
};

export default function BattleTestPage() {
  const API_BASE = "http://localhost:8000";

  const [battleId, setBattleId] = useState<number | null>(null);
  const [allyId, setAllyId] = useState<number | null>(null);
  const [enemyId, setEnemyId] = useState<number | null>(null);

  const [currentTurn, setCurrentTurn] = useState<number>(1);

  const [detail, setDetail] = useState<BattleDetailResponse | null>(null);
  const [logs, setLogs] = useState<BattleActionLog[]>([]);
  const [turnOrder, setTurnOrder] = useState<TurnOrderItem[]>([]);
  const [selectedAiProfile, setSelectedAiProfile] = useState<CombatAiProfileResponse | null>(null);
  const [usables, setUsables] = useState<CombatantUsablesResponse | null>(null);

  const [message, setMessage] = useState<string>("未実行");
  const [loading, setLoading] = useState<boolean>(false);

  const [tacticText, setTacticText] = useState<string>("太陽を背に回り込みながら斬りかかる");
  const [allyOrderTargetId, setAllyOrderTargetId] = useState<string>("");
  const [allyOrderText, setAllyOrderText] = useState<string>("無理をするな");
  const [allyOrderPriority, setAllyOrderPriority] = useState<string>("NORMAL");

  const [selectedActionKey, setSelectedActionKey] = useState<string>("");
  const [selectedActionKind, setSelectedActionKind] = useState<"skill" | "spell" | "">("");
  const [selectedTargetId, setSelectedTargetId] = useState<string>("");

  function parseJsonText(text: string): string {
    try {
      return JSON.stringify(JSON.parse(text), null, 2);
    } catch {
      return text;
    }
  }

  async function readErrorMessage(res: Response, fallback: string): Promise<string> {
    const contentType = res.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const data = await res.json().catch(() => null);
      if (data && typeof data.detail === "string" && data.detail) {
        return data.detail;
      }
    }

    const text = await res.text().catch(() => "");
    return text || fallback;
  }

  const combinedUsables = useMemo<CombinedUsableAction[]>(() => {
    if (!usables) return [];
    return [
      ...usables.skill_items.map((x) => ({
        ...x,
        kind: "skill" as const,
        action_key: x.skill_key,
      })),
      ...usables.spell_items.map((x) => ({
        ...x,
        kind: "spell" as const,
        action_key: x.spell_key,
      })),
    ];
  }, [usables]);

  const selectedAction = useMemo(() => {
    if (!selectedActionKey || !selectedActionKind) return null;
    return (
      combinedUsables.find(
        (item) => item.kind === selectedActionKind && item.action_key === selectedActionKey
      ) ?? null
    );
  }, [combinedUsables, selectedActionKey, selectedActionKind]);

  const manualPlayer = useMemo(() => {
    if (!detail || !allyId) return null;
    return detail.combatants.find((combatant) => combatant.combatant_id === allyId) ?? null;
  }, [detail, allyId]);

  const targetOptions = useMemo<TargetOption[]>(() => {
    if (!detail || !manualPlayer || !selectedAction) return [];

    if (selectedAction.target_type === "single_enemy") {
      return detail.combatants
        .filter((combatant) => combatant.state === "ACTIVE" && combatant.side !== manualPlayer.side)
        .map((combatant) => ({
          combatant_id: combatant.combatant_id,
          label: `${combatant.display_name} (${combatant.side}) HP ${combatant.hp_current}/${combatant.hp_max}`,
        }));
    }

    if (selectedAction.target_type === "single_ally") {
      return detail.combatants
        .filter((combatant) => combatant.state === "ACTIVE" && combatant.side === manualPlayer.side)
        .map((combatant) => ({
          combatant_id: combatant.combatant_id,
          label: `${combatant.display_name} (${combatant.side}) HP ${combatant.hp_current}/${combatant.hp_max}`,
        }));
    }

    return [];
  }, [detail, manualPlayer, selectedAction]);

  useEffect(() => {
    if (!selectedAction) {
      setSelectedTargetId("");
      return;
    }

    if (selectedAction.target_type === "self") {
      setSelectedTargetId(allyId ? String(allyId) : "");
      return;
    }

    setSelectedTargetId((current) => {
      if (targetOptions.some((option) => String(option.combatant_id) === current)) {
        return current;
      }
      return "";
    });
  }, [selectedAction, allyId, targetOptions]);

  async function createBattle() {
    setLoading(true);
    setMessage("戦闘作成中...");
    try {
      const res = await fetch(`${API_BASE}/api/battles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          world_id: 1,
          location_id: "test_field",
          battle_type: "ENCOUNTER",
          source_type: "MANUAL",
          source_ref_id: "frontend_test_battle",
          objective_type: "DEFEAT",
        }),
      });

      if (!res.ok) throw new Error("戦闘作成に失敗しました");

      const data: BattleCreateResponse = await res.json();
      setBattleId(data.battle_id);
      setCurrentTurn(data.turn_no);
      setAllyId(null);
      setEnemyId(null);
      setDetail(null);
      setLogs([]);
      setTurnOrder([]);
      setSelectedAiProfile(null);
      setUsables(null);
      setSelectedActionKey("");
      setSelectedActionKind("");
      setSelectedTargetId("");
      setAllyOrderTargetId("");
      setMessage(`戦闘を作成しました: battle_id=${data.battle_id}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    } finally {
      setLoading(false);
    }
  }

  async function addManualPlayer() {
    if (!battleId) {
      setMessage("先に戦闘を作成してください");
      return;
    }

    setLoading(true);
    setMessage("プレイヤー追加中...");
    try {
      const res = await fetch(`${API_BASE}/api/battle-combatants`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          battle_id: battleId,
          entity_type: "PLAYER",
          entity_id: "player_001",
          display_name: "アオ",
          side: "ALLY",
          role: "FRONT",
          hp_current: 30,
          hp_max: 30,
          mp_current: 10,
          mp_max: 10,
          atk: 12,
          defense: 5,
          mag: 4,
          res: 3,
          spd: 8,
          hit: 5,
          eva: 2,
          crit: 5,
          guard_rate: 0,
          is_player_controlled: true,
          ai_profile_key: "player_manual",
          loadout_key: "basic_fighter",
          notes_json: "{}",
        }),
      });

      if (!res.ok) throw new Error("プレイヤー追加に失敗しました");

      const data: CombatantCreateResponse = await res.json();
      setAllyId(data.combatant_id);
      setMessage(`プレイヤーを追加しました: combatant_id=${data.combatant_id}`);
      await refreshBattle();
      await refreshLogs();
      await refreshUsables(data.combatant_id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    } finally {
      setLoading(false);
    }
  }

  async function addAllyNpc() {
    if (!battleId) {
      setMessage("先に戦闘を作成してください");
      return;
    }

    setLoading(true);
    setMessage("味方NPC追加中...");
    try {
      const res = await fetch(`${API_BASE}/api/battle-combatants`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          battle_id: battleId,
          entity_type: "ALLY_NPC",
          entity_id: "ally_npc_001",
          display_name: "見習い衛兵",
          side: "ALLY",
          role: "FRONT",
          hp_current: 26,
          hp_max: 26,
          mp_current: 0,
          mp_max: 0,
          atk: 10,
          defense: 4,
          mag: 0,
          res: 2,
          spd: 6,
          hit: 3,
          eva: 1,
          crit: 1,
          guard_rate: 0,
          is_player_controlled: false,
          ai_profile_key: "ally_guard_novice",
          loadout_key: "basic_fighter",
          notes_json: "{}",
        }),
      });

      if (!res.ok) throw new Error("味方NPC追加に失敗しました");

      const data: CombatantCreateResponse = await res.json();
      setMessage(`味方NPCを追加しました: combatant_id=${data.combatant_id}`);
      await refreshBattle();
      await refreshLogs();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    } finally {
      setLoading(false);
    }
  }

  async function addEnemyMob() {
    if (!battleId) {
      setMessage("先に戦闘を作成してください");
      return;
    }

    setLoading(true);
    setMessage("敵追加中...");
    try {
      const res = await fetch(`${API_BASE}/api/battle-combatants`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          battle_id: battleId,
          entity_type: "MONSTER",
          entity_id: "monster_001",
          display_name: "坑道の獣",
          side: "ENEMY",
          role: "FRONT",
          hp_current: 24,
          hp_max: 24,
          mp_current: 0,
          mp_max: 0,
          atk: 9,
          defense: 4,
          mag: 0,
          res: 2,
          spd: 5,
          hit: 2,
          eva: 1,
          crit: 0,
          guard_rate: 0,
          is_player_controlled: false,
          ai_profile_key: "mob_basic_melee",
          loadout_key: "basic_monster",
          notes_json: "{}",
        }),
      });

      if (!res.ok) throw new Error("敵追加に失敗しました");

      const data: CombatantCreateResponse = await res.json();
      setEnemyId(data.combatant_id);
      setMessage(`敵を追加しました: combatant_id=${data.combatant_id}`);
      await refreshBattle();
      await refreshLogs();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    } finally {
      setLoading(false);
    }
  }

  async function addNamedEnemy() {
    if (!battleId) {
      setMessage("先に戦闘を作成してください");
      return;
    }

    setLoading(true);
    setMessage("ネームド敵追加中...");
    try {
      const res = await fetch(`${API_BASE}/api/battle-combatants`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          battle_id: battleId,
          entity_type: "NAMED_ENEMY",
          entity_id: "named_enemy_001",
          display_name: "冷徹な指揮官",
          side: "ENEMY",
          role: "COMMANDER",
          hp_current: 36,
          hp_max: 36,
          mp_current: 8,
          mp_max: 8,
          atk: 11,
          defense: 5,
          mag: 4,
          res: 4,
          spd: 9,
          hit: 5,
          eva: 3,
          crit: 3,
          guard_rate: 0,
          is_player_controlled: false,
          ai_profile_key: "named_enemy_cold_tactician",
          loadout_key: "basic_mage",
          notes_json: "{}",
        }),
      });

      if (!res.ok) throw new Error("ネームド敵追加に失敗しました");

      const data: CombatantCreateResponse = await res.json();
      setEnemyId(data.combatant_id);
      setMessage(`ネームド敵を追加しました: combatant_id=${data.combatant_id}`);
      await refreshBattle();
      await refreshLogs();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    } finally {
      setLoading(false);
    }
  }

  async function executeAttack() {
    if (!battleId || !allyId || !enemyId) {
      setMessage("先に戦闘・プレイヤー・敵を揃えてください");
      return;
    }

    setLoading(true);
    setMessage("攻撃実行中...");
    try {
      const res = await fetch(`${API_BASE}/api/battles/basic-attack`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          battle_id: battleId,
          turn_no: currentTurn,
          actor_combatant_id: allyId,
          target_combatant_id: enemyId,
          declared_tactic_text: tacticText,
          risk_level: "LOW",
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "攻撃実行に失敗しました");
      }

      setMessage("攻撃を実行しました");
      await refreshBattle();
      await refreshLogs();
      await refreshTurnOrder();
      await refreshUsables(allyId);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    } finally {
      setLoading(false);
    }
  }

  async function executeDefend() {
    if (!battleId || !allyId) {
      setMessage("先に戦闘とプレイヤーを用意してください");
      return;
    }

    setLoading(true);
    setMessage("防御実行中...");
    try {
      const res = await fetch(`${API_BASE}/api/battles/basic-defend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          battle_id: battleId,
          turn_no: currentTurn,
          actor_combatant_id: allyId,
          declared_tactic_text: tacticText,
          risk_level: "LOW",
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "防御実行に失敗しました");
      }

      setMessage("防御を実行しました");
      await refreshBattle();
      await refreshLogs();
      await refreshTurnOrder();
      await refreshUsables(allyId);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    } finally {
      setLoading(false);
    }
  }

  async function useSelectedAction() {
    if (!battleId || !allyId) {
      setMessage("先に戦闘とプレイヤーを用意してください");
      return;
    }
    if (!selectedActionKey || !selectedActionKind) {
      setMessage("skill/spell を選択してください");
      return;
    }

    if (!selectedAction) {
      setMessage("選択中の action 情報を取得できません");
      return;
    }

    let targetId: number | null = null;
    if (selectedAction.target_type === "self") {
      targetId = allyId;
    } else {
      if (!selectedTargetId) {
        setMessage("対象を選択してください");
        return;
      }

      targetId = Number(selectedTargetId);
      if (!Number.isInteger(targetId)) {
        setMessage("対象の combatant_id が不正です");
        return;
      }
      if (!targetOptions.some((option) => option.combatant_id === targetId)) {
        setMessage("選択中の action に対して不正な対象です");
        return;
      }
    }

    setLoading(true);
    setMessage("スキル/魔法使用中...");
    try {
      const res = await fetch(`${API_BASE}/api/battles/use-skill`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          battle_id: battleId,
          turn_no: currentTurn,
          actor_combatant_id: allyId,
          target_combatant_id: targetId,
          skill_key: selectedActionKey,
          declared_tactic_text: tacticText,
          risk_level: "LOW",
        }),
      });

      if (!res.ok) {
        throw new Error(await readErrorMessage(res, "スキル/魔法使用に失敗しました"));
      }

      await res.json();
      setMessage(`使用しました: ${selectedActionKey}`);
      await refreshBattle();
      await refreshLogs();
      await refreshTurnOrder();
      await refreshUsables(allyId);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    } finally {
      setLoading(false);
    }
  }

  async function advanceTurn() {
    if (!battleId) {
      setMessage("先に戦闘を作成してください");
      return;
    }

    setLoading(true);
    setMessage("ターン進行中...");
    try {
      const res = await fetch(`${API_BASE}/api/battles/advance-turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ battle_id: battleId }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "ターン進行に失敗しました");
      }

      const data: AdvanceTurnResponse = await res.json();
      setCurrentTurn(data.turn_no);
      setMessage(`ターンを進めました: ${data.turn_no} / 敵行動数: ${data.acted_enemy_count}`);
      await refreshBattle();
      await refreshLogs();
      await refreshTurnOrder();
      if (allyId) {
        await refreshUsables(allyId);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    } finally {
      setLoading(false);
    }
  }

  async function issueCompanionOrder() {
    if (!battleId) {
      setMessage("先に戦闘を作成してください");
      return;
    }
    if (!allyOrderTargetId) {
      setMessage("指示対象の combatant_id を入力してください");
      return;
    }

    setLoading(true);
    setMessage("指示送信中...");
    try {
      const res = await fetch(`${API_BASE}/api/battles/companion-order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          battle_id: battleId,
          target_combatant_id: Number(allyOrderTargetId),
          order_text: allyOrderText,
          priority: allyOrderPriority,
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "指示送信に失敗しました");
      }

      const data: CompanionOrderResponse = await res.json();
      setMessage(
        `指示を送信しました: target=${data.target_combatant_id} / accepted=${data.accepted ? "true" : "false"}`
      );
      await refreshBattle();
      await refreshTurnOrder();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    } finally {
      setLoading(false);
    }
  }

  async function refreshBattle() {
    if (!battleId) {
      setMessage("先に戦闘を作成してください");
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/battles/${battleId}`, {
        cache: "no-store",
      });

      if (!res.ok) throw new Error("戦闘詳細取得に失敗しました");

      const data: BattleDetailResponse = await res.json();
      setDetail(data);
      setCurrentTurn(data.turn_no);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    }
  }

  async function refreshLogs() {
    if (!battleId) {
      setMessage("先に戦闘を作成してください");
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/battles/${battleId}/logs`, {
        cache: "no-store",
      });

      if (!res.ok) throw new Error("戦闘ログ取得に失敗しました");

      const data: BattleActionLog[] = await res.json();
      setLogs(data);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    }
  }

  async function refreshTurnOrder() {
    if (!battleId) {
      setMessage("先に戦闘を作成してください");
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/battles/${battleId}/turn-order`, {
        cache: "no-store",
      });

      if (!res.ok) throw new Error("行動順取得に失敗しました");

      const data: BattleTurnOrderResponse = await res.json();
      setTurnOrder(data.order);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    }
  }

  async function refreshUsables(combatantId: number) {
    if (!battleId) {
      setMessage("先に戦闘を作成してください");
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/battles/${battleId}/combatants/${combatantId}/usables`, {
        cache: "no-store",
      });

      if (!res.ok) throw new Error("使用可能一覧取得に失敗しました");

      const data: CombatantUsablesResponse = await res.json();
      setUsables(data);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    }
  }

  async function loadAiProfile(combatantId: number) {
    if (!battleId) {
      setMessage("先に戦闘を作成してください");
      return;
    }

    setLoading(true);
    setMessage("AIプロファイル取得中...");
    try {
      const res = await fetch(
        `${API_BASE}/api/battles/${battleId}/combatants/${combatantId}/ai-profile`,
        { cache: "no-store" }
      );

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "AIプロファイル取得に失敗しました");
      }

      const data: CombatAiProfileResponse = await res.json();
      setSelectedAiProfile(data);
      setMessage(`AIプロファイルを取得しました: ${combatantId}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "不明なエラー");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: "1200px", margin: "0 auto", padding: "24px" }}>
      <h1>戦闘テスト α版</h1>

      <section style={{ marginTop: "16px" }}>
        <h2>基本操作</h2>
        <div style={{ display: "grid", gap: "12px", marginTop: "12px" }}>
          <button onClick={createBattle} disabled={loading}>
            1. 戦闘作成
          </button>

          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <button onClick={addManualPlayer} disabled={loading || !battleId}>
              2. プレイヤー追加
            </button>
            <button onClick={addAllyNpc} disabled={loading || !battleId}>
              3. 味方NPC追加
            </button>
            <button onClick={addEnemyMob} disabled={loading || !battleId}>
              4. MOB敵追加
            </button>
            <button onClick={addNamedEnemy} disabled={loading || !battleId}>
              5. ネームド敵追加
            </button>
          </div>

          <label style={{ display: "grid", gap: "8px" }}>
            <span>戦術宣言</span>
            <input
              value={tacticText}
              onChange={(e) => setTacticText(e.target.value)}
              style={{ padding: "8px" }}
            />
          </label>

          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <button onClick={executeAttack} disabled={loading || !battleId || !allyId || !enemyId}>
              通常攻撃
            </button>
            <button onClick={executeDefend} disabled={loading || !battleId || !allyId}>
              防御
            </button>
            <button onClick={advanceTurn} disabled={loading || !battleId}>
              次のターンへ
            </button>
          </div>

          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <button onClick={refreshBattle} disabled={loading || !battleId}>
              戦闘詳細更新
            </button>
            <button onClick={refreshLogs} disabled={loading || !battleId}>
              戦闘ログ更新
            </button>
            <button onClick={refreshTurnOrder} disabled={loading || !battleId}>
              行動順更新
            </button>
            <button onClick={() => allyId && refreshUsables(allyId)} disabled={loading || !battleId || !allyId}>
              使用可能一覧更新
            </button>
          </div>
        </div>
      </section>

      <section style={{ marginTop: "24px" }}>
        <h2>スキル / 魔法使用</h2>
        <div style={{ display: "grid", gap: "8px", marginTop: "12px" }}>
          <label style={{ display: "grid", gap: "4px" }}>
            <span>使用する action</span>
            <select
              value={selectedActionKind && selectedActionKey ? `${selectedActionKind}:${selectedActionKey}` : ""}
              onChange={(e) => {
                const value = e.target.value;
                if (!value) {
                  setSelectedActionKind("");
                  setSelectedActionKey("");
                  return;
                }
                const [kind, key] = value.split(":");
                setSelectedActionKind(kind as "skill" | "spell");
                setSelectedActionKey(key);
              }}
              style={{ padding: "8px" }}
            >
              <option value="">未選択</option>
              {combinedUsables.map((item) => (
                <option key={`${item.kind}:${item.kind === "skill" ? item.skill_key : item.spell_key}`} value={`${item.kind}:${item.kind === "skill" ? item.skill_key : item.spell_key}`}>
                  {item.kind === "skill" ? item.name : item.name} / CD:{item.current_cooldown} / Cost:{item.resource_cost} / {item.usable ? "usable" : item.reason}
                </option>
              ))}
            </select>
          </label>

          <div style={{ display: "grid", gap: "4px" }}>
            <p>target_type: {selectedAction?.target_type ?? "未選択"}</p>

            {selectedAction?.target_type === "self" ? (
              <p>対象: 自分 {manualPlayer ? `(${manualPlayer.display_name})` : ""}</p>
            ) : selectedAction ? (
              <label style={{ display: "grid", gap: "4px" }}>
                <span>
                  対象を選択
                  {selectedAction.target_type === "single_enemy" ? "（敵単体）" : "（味方単体）"}
                </span>
                <select
                  value={selectedTargetId}
                  onChange={(e) => setSelectedTargetId(e.target.value)}
                  style={{ padding: "8px" }}
                  disabled={targetOptions.length === 0}
                >
                  <option value="">未選択</option>
                  {targetOptions.map((option) => (
                    <option key={option.combatant_id} value={option.combatant_id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>

          <button onClick={useSelectedAction} disabled={loading || !battleId || !allyId || !selectedActionKey}>
            選択したスキル / 魔法を使う
          </button>

          {usables ? (
            <div style={{ display: "grid", gap: "12px" }}>
              <div>
                <h3>usable skills</h3>
                {usables.skill_items.map((item) => (
                  <div key={item.skill_key} style={{ border: "1px solid #ccc", padding: "8px", marginTop: "8px" }}>
                    <p>{item.name} ({item.skill_key})</p>
                    <p>category: {item.category}</p>
                    <p>target_type: {item.target_type}</p>
                    <p>cost: {item.resource_cost} {item.resource_type}</p>
                    <p>cooldown: {item.current_cooldown} / {item.cooldown_turns}</p>
                    <p>usable: {item.usable ? "true" : "false"}</p>
                    <p>reason: {item.reason || "none"}</p>
                  </div>
                ))}
              </div>

              <div>
                <h3>usable spells</h3>
                {usables.spell_items.map((item) => (
                  <div key={item.spell_key} style={{ border: "1px solid #ccc", padding: "8px", marginTop: "8px" }}>
                    <p>{item.name} ({item.spell_key})</p>
                    <p>category: {item.category}</p>
                    <p>target_type: {item.target_type}</p>
                    <p>cost: {item.resource_cost} {item.resource_type}</p>
                    <p>cooldown: {item.current_cooldown} / {item.cooldown_turns}</p>
                    <p>usable: {item.usable ? "true" : "false"}</p>
                    <p>reason: {item.reason || "none"}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p>まだ使用可能一覧はありません。</p>
          )}
        </div>
      </section>

      <section style={{ marginTop: "24px" }}>
        <h2>味方NPCへの指示</h2>
        <div style={{ display: "grid", gap: "8px", marginTop: "12px" }}>
          <label style={{ display: "grid", gap: "4px" }}>
            <span>対象 combatant_id</span>
            <input
              value={allyOrderTargetId}
              onChange={(e) => setAllyOrderTargetId(e.target.value)}
              placeholder="例: 2"
              style={{ padding: "8px" }}
            />
          </label>

          <label style={{ display: "grid", gap: "4px" }}>
            <span>指示テキスト</span>
            <input
              value={allyOrderText}
              onChange={(e) => setAllyOrderText(e.target.value)}
              placeholder="例: 無理をするな / 敵の術師を狙え"
              style={{ padding: "8px" }}
            />
          </label>

          <label style={{ display: "grid", gap: "4px" }}>
            <span>優先度</span>
            <select
              value={allyOrderPriority}
              onChange={(e) => setAllyOrderPriority(e.target.value)}
              style={{ padding: "8px" }}
            >
              <option value="LOW">LOW</option>
              <option value="NORMAL">NORMAL</option>
              <option value="HIGH">HIGH</option>
            </select>
          </label>

          <button onClick={issueCompanionOrder} disabled={loading || !battleId}>
            指示を送る
          </button>
        </div>
      </section>

      <section style={{ marginTop: "24px" }}>
        <h2>状態</h2>
        <p>{message}</p>
        <p>battle_id: {battleId ?? "未作成"}</p>
        <p>manual_player_id: {allyId ?? "未追加"}</p>
        <p>enemy_id: {enemyId ?? "未追加"}</p>
        <p>current_turn: {currentTurn}</p>
      </section>

      <section style={{ marginTop: "24px" }}>
        <h2>戦闘詳細</h2>
        {detail ? (
          <div style={{ display: "grid", gap: "8px" }}>
            <p>battle_id: {detail.battle_id}</p>
            <p>location_id: {detail.location_id}</p>
            <p>state: {detail.state}</p>
            <p>turn_no: {detail.turn_no}</p>
            <p>objective_type: {detail.objective_type}</p>

            <div style={{ display: "grid", gap: "12px", marginTop: "12px" }}>
              {detail.combatants.map((combatant) => (
                <div
                  key={combatant.combatant_id}
                  style={{
                    border: "1px solid #ccc",
                    borderRadius: "8px",
                    padding: "12px",
                  }}
                >
                  <p>ID: {combatant.combatant_id}</p>
                  <p>名前: {combatant.display_name}</p>
                  <p>陣営: {combatant.side}</p>
                  <p>役割: {combatant.role}</p>
                  <p>操作種別: {combatant.controller_type}</p>
                  <p>AIプロファイル: {combatant.ai_profile_key || "なし"}</p>
                  <p>HP: {combatant.hp_current} / {combatant.hp_max}</p>
                  <p>MP: {combatant.mp_current} / {combatant.mp_max}</p>
                  <p>状態: {combatant.state}</p>
                  <p>防御中: {combatant.defend_active ? "はい" : "いいえ"}</p>
                  <p>防御タグ: {combatant.defend_used_tags_json}</p>
                  <p>行動済み: {combatant.has_acted_this_turn ? "はい" : "いいえ"}</p>
                  <p>距離帯: {combatant.range_band}</p>
                  <p>位置タグ: {combatant.position_tags_json}</p>
                  <p>現在指示: {combatant.current_order_text || "なし"}</p>
                  <p>skill_keys: {combatant.available_skill_keys_json}</p>
                  <p>spell_keys: {combatant.available_spell_keys_json}</p>
                  <p>equipped_items: {combatant.equipped_item_keys_json}</p>

                  <button
                    onClick={() => loadAiProfile(combatant.combatant_id)}
                    disabled={loading}
                    style={{ marginTop: "8px" }}
                  >
                    AIプロファイル確認
                  </button>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p>まだ読み込まれていません。</p>
        )}
      </section>

      <section style={{ marginTop: "24px" }}>
        <h2>行動順</h2>
        {turnOrder.length > 0 ? (
          <div style={{ display: "grid", gap: "8px" }}>
            {turnOrder.map((item, index) => (
              <div
                key={item.combatant_id}
                style={{
                  border: "1px solid #ccc",
                  borderRadius: "8px",
                  padding: "12px",
                }}
              >
                <p>順番: {index + 1}</p>
                <p>名前: {item.display_name}</p>
                <p>陣営: {item.side}</p>
                <p>SPD: {item.spd}</p>
                <p>状態: {item.state}</p>
                <p>行動済み: {item.has_acted ? "はい" : "いいえ"}</p>
              </div>
            ))}
          </div>
        ) : (
          <p>まだ行動順はありません。</p>
        )}
      </section>

      <section style={{ marginTop: "24px" }}>
        <h2>AIプロファイル</h2>
        {selectedAiProfile ? (
          <div
            style={{
              border: "1px solid #ccc",
              borderRadius: "8px",
              padding: "12px",
              display: "grid",
              gap: "8px",
            }}
          >
            <p>profile_key: {selectedAiProfile.profile_key}</p>
            <p>controller_type: {selectedAiProfile.controller_type}</p>
            <p>combat_role: {selectedAiProfile.combat_role}</p>
            <p>behavior_mode: {selectedAiProfile.behavior_mode}</p>
            <p>combat_experience: {selectedAiProfile.combat_experience}</p>
            <p>tactical_judgment: {selectedAiProfile.tactical_judgment}</p>
            <p>command_obedience: {selectedAiProfile.command_obedience}</p>
            <p>command_comprehension: {selectedAiProfile.command_comprehension}</p>
            <p>teamwork_skill: {selectedAiProfile.teamwork_skill}</p>
            <p>morale: {selectedAiProfile.morale}</p>
            <p>panic_action_rate: {selectedAiProfile.panic_action_rate}</p>
            <p>hesitation_rate: {selectedAiProfile.hesitation_rate}</p>
            <p>misplay_tendency: {selectedAiProfile.misplay_tendency}</p>
            <p>communication_method: {selectedAiProfile.communication_method}</p>
            <p>noise_tolerance: {selectedAiProfile.noise_tolerance}</p>
            <p>
              requires_line_of_sight_for_command:{" "}
              {selectedAiProfile.requires_line_of_sight_for_command ? "true" : "false"}
            </p>
            <p>current_order_text: {selectedAiProfile.current_order_text || "なし"}</p>
            <p>current_order_priority: {selectedAiProfile.current_order_priority}</p>

            <div>
              <p>base_traits_json:</p>
              <pre style={{ whiteSpace: "pre-wrap" }}>
                {parseJsonText(selectedAiProfile.base_traits_json)}
              </pre>
            </div>

            <div>
              <p>dynamic_traits_json:</p>
              <pre style={{ whiteSpace: "pre-wrap" }}>
                {parseJsonText(selectedAiProfile.dynamic_traits_json)}
              </pre>
            </div>

            <div>
              <p>growth_stats_json:</p>
              <pre style={{ whiteSpace: "pre-wrap" }}>
                {parseJsonText(selectedAiProfile.growth_stats_json)}
              </pre>
            </div>

            <div>
              <p>relationship_modifiers_json:</p>
              <pre style={{ whiteSpace: "pre-wrap" }}>
                {parseJsonText(selectedAiProfile.relationship_modifiers_json)}
              </pre>
            </div>

            <div>
              <p>temporary_state_tags_json:</p>
              <pre style={{ whiteSpace: "pre-wrap" }}>
                {parseJsonText(selectedAiProfile.temporary_state_tags_json)}
              </pre>
            </div>
          </div>
        ) : (
          <p>まだAIプロファイルは読み込まれていません。</p>
        )}
      </section>

      <section style={{ marginTop: "24px" }}>
        <h2>戦闘ログ</h2>
        {logs.length > 0 ? (
          <div style={{ display: "grid", gap: "12px" }}>
            {logs.map((log) => (
              <div
                key={log.action_log_id}
                style={{
                  border: "1px solid #ccc",
                  borderRadius: "8px",
                  padding: "12px",
                }}
              >
                <p>log_id: {log.action_log_id}</p>
                <p>turn: {log.turn_no}</p>
                <p>行動者: {log.actor_name}（ID: {log.actor_combatant_id}）</p>
                <p>
                  対象: {log.target_name ?? "なし"}
                  {log.target_combatant_id ? `（ID: ${log.target_combatant_id}）` : ""}
                </p>
                <p>結果: {log.result_type}</p>
                <p>命中: {log.hit_success ? "true" : "false"}</p>
                <p>クリティカル: {log.crit_success ? "true" : "false"}</p>
                <p>防御軽減: {log.guard_success ? "true" : "false"}</p>
                <p>回避: {log.evade_success ? "true" : "false"}</p>
                <p>ダメージ: {log.damage_value}</p>
                <p>対象HP残量: {log.hp_after}</p>
                <p>戦術宣言: {log.declared_tactic_text || "なし"}</p>
                <p>タグ: {log.used_tags_json}</p>
                <p>演出: {log.narrative_result}</p>
                <p>AI理由: {log.ai_reason_summary || "なし"}</p>
                <p>適用命令: {log.order_applied_text || "なし"}</p>
              </div>
            ))}
          </div>
        ) : (
          <p>まだログはありません。</p>
        )}
      </section>
    </main>
  );
}
