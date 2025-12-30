from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

DATA_DIR = Path("data/akinator")
DATA_DIR.mkdir(parents=True, exist_ok=True)

ENTITIES_FILE = DATA_DIR / "entities.json"
QUESTIONS_FILE = DATA_DIR / "questions.json"

ANSWER_WEIGHTS = {
    "yes": (True, 2.0),
    "probably": (True, 1.0),
    "idk": (None, 0.0),
    "probably_not": (False, 1.0),
    "no": (False, 2.0),
}


class Entity:
    def __init__(self, name: str, category: str, traits: Dict[str, bool]):
        self.name = name
        self.category = category
        self.traits = traits
        self.score = 0.0

    def apply(self, trait: str, value: Optional[bool], weight: float):
        if value is None or trait not in self.traits:
            return
        self.score += weight if self.traits[trait] == value else -weight


class Question:
    def __init__(self, trait: str, text: str):
        self.trait = trait
        self.text = text


class AkinatorEngine:
    def __init__(self, domain: Optional[str] = None):
        self.entities = self._load_entities(domain)
        self.questions = self._load_questions()
        self.asked: set[str] = set()
        self.steps = 0

    # ---------------- IO ----------------

    def _load_entities(self, domain: Optional[str]) -> List[Entity]:
        if not ENTITIES_FILE.exists():
            return []
        data = json.loads(ENTITIES_FILE.read_text())
        ents = [
            Entity(e["name"], e["category"], e["traits"])
            for e in data
            if domain is None or e["category"] == domain
        ]
        return ents

    def _save_entity(self, entity: Entity):
        data = []
        if ENTITIES_FILE.exists():
            data = json.loads(ENTITIES_FILE.read_text())

        data.append({
            "name": entity.name,
            "category": entity.category,
            "traits": entity.traits,
        })

        ENTITIES_FILE.write_text(json.dumps(data, indent=2))

    def _load_questions(self) -> List[Question]:
        if not QUESTIONS_FILE.exists():
            return []
        data = json.loads(QUESTIONS_FILE.read_text())
        return [Question(q["trait"], q["question"]) for q in data]

    # ---------------- Logic ----------------

    def next_question(self) -> Optional[Question]:
        remaining = [
            q for q in self.questions if q.trait not in self.asked
        ]
        if not remaining:
            return None

        best = max(remaining, key=lambda q: self._entropy(q.trait))
        self.asked.add(best.trait)
        self.steps += 1
        return best

    def _entropy(self, trait: str) -> float:
        t = sum(1 for e in self.entities if e.traits.get(trait) is True)
        f = sum(1 for e in self.entities if e.traits.get(trait) is False)
        return min(t, f)

    def apply_answer(self, trait: str, answer: str):
        val, weight = ANSWER_WEIGHTS[answer]
        for e in self.entities:
            e.apply(trait, val, weight)

    def best_guess(self) -> Optional[Entity]:
        if not self.entities:
            return None
        return max(self.entities, key=lambda e: e.score)

    def should_guess(self) -> bool:
        if self.steps >= 20:
            return True
        top = self.best_guess()
        return top and top.score >= 8.0

    # ---------------- Learning ----------------

    def learn(self, name: str, category: str, traits: Dict[str, bool]):
        entity = Entity(name=name, category=category, traits=traits)
        self._save_entity(entity)
