from __future__ import annotations
from dataclasses import dataclass, field, replace
from typing import Dict, List, Callable, Tuple, Iterable
from uuid import uuid4
from datetime import datetime
import copy


# ============================================================
# Utility Types
# ============================================================

Timestamp = datetime
WorkspaceID = str
PodID = str
RefID = str
ProposalID = str


def now() -> Timestamp:
    return datetime.utcnow()


# ============================================================
# Refcards Protocol (Knowledge Substrate)
# ============================================================

@dataclass(frozen=True)
class Refcard:
    id: RefID
    title: str
    metadata: Dict[str, str]
    citations: Tuple[RefID, ...] = ()

    def cite(self, other: RefID) -> "Refcard":
        return replace(self, citations=self.citations + (other,))


@dataclass
class ReferenceGraph:
    cards: Dict[RefID, Refcard] = field(default_factory=dict)

    def add(self, card: Refcard) -> None:
        self.cards[card.id] = card

    def density(self) -> float:
        total_edges = sum(len(card.citations) for card in self.cards.values())
        total_nodes = len(self.cards)
        return total_edges / total_nodes if total_nodes else 0.0


# ============================================================
# Modular Operational Pods
# ============================================================

@dataclass
class OperationalPod:
    id: PodID
    name: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    documentation: List[str] = field(default_factory=list)
    reputation: float = 0.0

    def log(self, entry: str) -> None:
        self.documentation.append(f"{now().isoformat()} | {entry}")

    def produce(self, artifact: str) -> None:
        self.outputs.append(artifact)
        self.log(f"Produced artifact: {artifact}")
        self.reputation += 1.0


# ============================================================
# Workspace State (Historiotopic Snapshot)
# ============================================================

@dataclass(frozen=True)
class WorkspaceState:
    id: WorkspaceID
    timestamp: Timestamp
    pods: Dict[PodID, OperationalPod]
    reference_graph: ReferenceGraph
    treasury: float
    documentation_hash: str = ""

    def delta(self, other: "WorkspaceState") -> Dict[str, int]:
        return {
            "pod_delta": len(other.pods) - len(self.pods),
            "ref_delta": len(other.reference_graph.cards) - len(self.reference_graph.cards),
            "treasury_delta": other.treasury - self.treasury,
        }


# ============================================================
# Governance Layer
# ============================================================

@dataclass
class Proposal:
    id: ProposalID
    description: str
    mutation: Callable[[WorkspaceState], WorkspaceState]
    votes_for: int = 0
    votes_against: int = 0

    def vote(self, support: bool) -> None:
        if support:
            self.votes_for += 1
        else:
            self.votes_against += 1

    def approved(self) -> bool:
        return self.votes_for > self.votes_against


# ============================================================
# Historiotopic Engine
# ============================================================

class HistoriothequeDAO:
    def __init__(self, initial_treasury: float = 0.0):
        self.history: List[WorkspaceState] = []
        self.proposals: Dict[ProposalID, Proposal] = {}
        self._initialize(initial_treasury)

    def _initialize(self, treasury: float) -> None:
        genesis = WorkspaceState(
            id=str(uuid4()),
            timestamp=now(),
            pods={},
            reference_graph=ReferenceGraph(),
            treasury=treasury,
        )
        self.history.append(genesis)

    @property
    def current_state(self) -> WorkspaceState:
        return self.history[-1]

    # --------------------------------------------------------
    # Mutation Mechanics (ΔW)
    # --------------------------------------------------------

    def apply_mutation(self, mutation: Callable[[WorkspaceState], WorkspaceState]) -> WorkspaceState:
        new_state = mutation(self.current_state)
        self.history.append(new_state)
        return new_state

    def historiotopic_velocity(self) -> float:
        if len(self.history) < 2:
            return 0.0
        t1 = self.history[-2].timestamp
        t2 = self.history[-1].timestamp
        dt = (t2 - t1).total_seconds()
        if dt == 0:
            return 0.0
        delta = self.history[-2].delta(self.history[-1])
        magnitude = sum(abs(v) for v in delta.values())
        return magnitude / dt

    # --------------------------------------------------------
    # Governance
    # --------------------------------------------------------

    def submit_proposal(self, description: str, mutation: Callable[[WorkspaceState], WorkspaceState]) -> ProposalID:
        pid = str(uuid4())
        self.proposals[pid] = Proposal(pid, description, mutation)
        return pid

    def vote(self, proposal_id: ProposalID, support: bool) -> None:
        self.proposals[proposal_id].vote(support)

    def execute(self, proposal_id: ProposalID) -> WorkspaceState | None:
        proposal = self.proposals.get(proposal_id)
        if proposal and proposal.approved():
            return self.apply_mutation(proposal.mutation)
        return None


# ============================================================
# Functional Mutation Utilities
# ============================================================

def add_pod(name: str) -> Callable[[WorkspaceState], WorkspaceState]:
    def mutation(state: WorkspaceState) -> WorkspaceState:
        new_pods = copy.deepcopy(state.pods)
        pod_id = str(uuid4())
        new_pods[pod_id] = OperationalPod(id=pod_id, name=name)
        return replace(
            state,
            id=str(uuid4()),
            timestamp=now(),
            pods=new_pods
        )
    return mutation


def add_refcard(title: str, metadata: Dict[str, str]) -> Callable[[WorkspaceState], WorkspaceState]:
    def mutation(state: WorkspaceState) -> WorkspaceState:
        graph = copy.deepcopy(state.reference_graph)
        ref = Refcard(id=str(uuid4()), title=title, metadata=metadata)
        graph.add(ref)
        return replace(
            state,
            id=str(uuid4()),
            timestamp=now(),
            reference_graph=graph
        )
    return mutation


def allocate_treasury(amount: float) -> Callable[[WorkspaceState], WorkspaceState]:
    def mutation(state: WorkspaceState) -> WorkspaceState:
        return replace(
            state,
            id=str(uuid4()),
            timestamp=now(),
            treasury=state.treasury + amount
        )
    return mutation


# ============================================================
# Stability Oracle
# ============================================================

def stability_oracle(state: WorkspaceState) -> Dict[str, float]:
    return {
        "archive_density": state.reference_graph.density(),
        "pod_count": len(state.pods),
        "treasury_balance": state.treasury,
    }


# ============================================================
# Example Usage
# ============================================================

if __name__ == "__main__":

    dao = HistoriothequeDAO(initial_treasury=1000.0)

    # Create proposal: add a new pod
    pid = dao.submit_proposal(
        "Create Soundwalk Research Pod",
        add_pod("Soundwalk Research")
    )

    dao.vote(pid, True)
    dao.execute(pid)

    # Add a reference card
    pid2 = dao.submit_proposal(
        "Add Refcard: Psychogeography",
        add_refcard("Psychogeography", {"discipline": "urban theory"})
    )

    dao.vote(pid2, True)
    dao.execute(pid2)

    print("Historiotopic velocity:", dao.historiotopic_velocity())
    print("Stability metrics:", stability_oracle(dao.current_state))
