"""
TerraChain — SHA-256 기반 불변 감사 체인

FusionCore의 FusionChain과 동일한 해시 패턴을 따른다:
  H_i = SHA-256(str(i) | str(t_s) | payload_json | H_{i-1})
  Genesis = SHA-256("GENESIS|TerraCore|{ship_id}")

이벤트 유형:
  TELEMETRY           — 주기적 상태 기록
  SYNTHESIS_IGNITION  — pp chain 점화 이벤트
  TRIPLE_ALPHA_START  — 삼중 알파 점화 이벤트
  ATMOSPHERE_ALERT    — 대기 경보
  BIOSPHERE_MILESTONE — 바이오매스 목표 달성
  ABORT_EVENT         — 비상 중단 이벤트
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import List


@dataclass
class ChainEntry:
    """감사 체인의 단일 항목."""

    index: int
    t_s: float
    event_type: str
    payload: dict
    prev_hash: str
    entry_hash: str


class TerraChain:
    """SHA-256 기반 불변 감사 체인.

    모든 중요 이벤트를 변조 불가한 체인으로 기록한다.
    """

    EVENT_TELEMETRY = "TELEMETRY"
    EVENT_SYNTHESIS_IGNITION = "SYNTHESIS_IGNITION"
    EVENT_TRIPLE_ALPHA_START = "TRIPLE_ALPHA_START"
    EVENT_ATMOSPHERE_ALERT = "ATMOSPHERE_ALERT"
    EVENT_BIOSPHERE_MILESTONE = "BIOSPHERE_MILESTONE"
    EVENT_ABORT_EVENT = "ABORT_EVENT"

    def __init__(self, ship_id: str = "TERRA-001"):
        self.ship_id = ship_id
        self._entries: List[ChainEntry] = []
        self._genesis_hash = self._compute_genesis(ship_id)
        self._last_hash = self._genesis_hash

    def _compute_genesis(self, ship_id: str) -> str:
        """Genesis 블록 해시 계산."""
        raw = f"GENESIS|TerraCore|{ship_id}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _compute_hash(self, index: int, t_s: float, payload_json: str, prev_hash: str) -> str:
        """블록 해시 계산.

        H_i = SHA-256(str(i) | str(t_s) | payload_json | H_{i-1})
        """
        raw = f"{index}{t_s}{payload_json}{prev_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def record(self, t_s: float, event_type: str, payload: dict) -> ChainEntry:
        """새 이벤트 기록.

        Args:
            t_s: 이벤트 시각 [s]
            event_type: 이벤트 유형 문자열
            payload: 이벤트 데이터

        Returns:
            ChainEntry 객체
        """
        index = len(self._entries)
        payload_json = json.dumps(payload, sort_keys=True, default=str)
        entry_hash = self._compute_hash(index, t_s, payload_json, self._last_hash)

        entry = ChainEntry(
            index=index,
            t_s=t_s,
            event_type=event_type,
            payload=payload,
            prev_hash=self._last_hash,
            entry_hash=entry_hash,
        )
        self._entries.append(entry)
        self._last_hash = entry_hash
        return entry

    def verify(self) -> bool:
        """체인 무결성 검증.

        모든 항목의 해시를 재계산하여 저장된 값과 비교한다.

        Returns:
            체인이 유효하면 True
        """
        prev = self._genesis_hash
        for entry in self._entries:
            payload_json = json.dumps(entry.payload, sort_keys=True, default=str)
            expected = self._compute_hash(entry.index, entry.t_s, payload_json, prev)
            if expected != entry_hash_from_entry(entry):
                return False
            prev = entry.entry_hash
        return True

    def entries(self) -> List[ChainEntry]:
        """전체 감사 항목 반환 (읽기 전용 복사본)."""
        return list(self._entries)

    def genesis_hash(self) -> str:
        """Genesis 해시 반환."""
        return self._genesis_hash

    def last_hash(self) -> str:
        """마지막 블록 해시 반환."""
        return self._last_hash

    def length(self) -> int:
        """체인 길이 반환."""
        return len(self._entries)


def entry_hash_from_entry(entry: ChainEntry) -> str:
    """ChainEntry에서 해시 반환 (검증 헬퍼)."""
    return entry.entry_hash
