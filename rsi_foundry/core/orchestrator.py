"""The Foundry orchestrator — the recursive R&D loop.

Each cycle:
  1. re-anchor the canonical capability reference to the current champion,
  2. read SEAL priors and apply anti-collapse novelty pressure,
  3. generate successors from QD parents via the composed loops
     (AlphaEvolve + DGM self-edits + ADAS design search + periodic Scientist),
  4. run every candidate through the containment + quorum evaluator,
  5. mint assurance from the verification work just performed,
  6. gate each candidate (novelty -> causal -> regression -> HALF-LIFE),
  7. promote only governed improvements; archive diversity; mine failures (SEAL);
     harvest best attributes; reward winning ADAS designs,
  8. coevolve the benchmark (POET) and let the meta-gate adjust the gates,
  9. halt if HALF-LIFE goes BLACK.

It is built to *act the way it works*: generate, sandbox, prove, gate, learn,
repeat — keeping only what survives assurance.
"""
from __future__ import annotations

import random
from typing import Any, Optional

from rsi_foundry.connectors.benchmark_adapters import LocalBinPackBenchmark
from rsi_foundry.core.lineage import LineageGraph
from rsi_foundry.core.rng import RNGHub
from rsi_foundry.core.successor_registry import SuccessorRegistry
from rsi_foundry.core.types import Candidate, CycleRecord, EvalResult
from rsi_foundry.domain import binpack, heuristics
from rsi_foundry.evals.harness import Harness
from rsi_foundry.governance import causal_gate, promotion
from rsi_foundry.governance.half_life import HalfLifeController
from rsi_foundry.governance.meta_gate import MetaGate
from rsi_foundry.governance.promotion import PromotionPolicy
from rsi_foundry.loops.adas_loop import ADASLoop
from rsi_foundry.loops.alphaevolve_loop import AlphaEvolveLoop
from rsi_foundry.loops.base import LoopContext
from rsi_foundry.loops.best_attribute_registry import BestAttributeRegistry
from rsi_foundry.loops.dgm_loop import DGMLoop
from rsi_foundry.loops.novelty_ledger import NoveltyLedger
from rsi_foundry.loops.poet import POET
from rsi_foundry.loops.qd_archive import QDArchive
from rsi_foundry.loops.scientist_loop import ScientistLoop
from rsi_foundry.proposers.base import build_candidate
from rsi_foundry.proposers.llm_proposer import LLMProposer
from rsi_foundry.proposers.mutation_proposer import MutationProposer
from rsi_foundry.sandbox.containment import ContainmentPolicy, make_sandbox
from rsi_foundry.training.seal_loop import SEALLoop

DEFAULTS: dict[str, Any] = {
    "seed": 1234,
    "cycles": 8,
    "per_env_instances": 3,
    "qd_grid": 8,
    "novelty_k": 5,
    "entropy_floor": 0.45,          # below this, raise novelty pressure
    "novelty_pressure": 0.15,
    "scientist_every": 2,
    "benchmark_floor": 0.50,
    "safety_factor": 2.0,
    "assurance_per_check": 0.004,
    "assurance_per_coverage": 0.40,
    "use_llm": False,
    "containment": {"cpu_seconds": 2, "mem_mb": 256, "wall_timeout": 8.0},
    "offspring": {"alphaevolve": 6, "dgm": 3, "adas": 3},
}


def _merge(defaults: dict, override: dict | None) -> dict:
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in defaults.items()}
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    return cfg


class Foundry:
    def __init__(self, config: dict | None = None):
        self.config = _merge(DEFAULTS, config)
        self.hub = RNGHub(self.config["seed"])

        # containment + evaluators (real subprocess quorum + fast in-process ablation)
        cpol = ContainmentPolicy(**self.config["containment"])
        self.quorum_sandbox = make_sandbox("subprocess", cpol)
        self.fast_sandbox = make_sandbox("in_process", cpol)

        # POET environment population
        self.poet = POET(binpack.starter_envs(), self.hub.stream("poet"))
        self._benchmark_version = -1
        self.benchmark: Optional[LocalBinPackBenchmark] = None
        self.harness: Optional[Harness] = None
        self.fast_harness: Optional[Harness] = None

        # proposer (LLM if available, else deterministic mutation)
        if self.config["use_llm"]:
            self.proposer: Any = LLMProposer()
        else:
            self.proposer = MutationProposer()

        # generative loops
        off = self.config["offspring"]
        self.alphaevolve = AlphaEvolveLoop(off["alphaevolve"])
        self.dgm = DGMLoop(off["dgm"])
        self.adas = ADASLoop(off["adas"])
        self.scientist = ScientistLoop()

        # archives + learning
        self.qd = QDArchive(grid=self.config["qd_grid"])
        self.novelty = NoveltyLedger(k=self.config["novelty_k"], grid=self.config["qd_grid"])
        self.best_attr = BestAttributeRegistry()
        self.seal = SEALLoop()

        # governance
        self.policy = PromotionPolicy()
        self.half_life = HalfLifeController(safety_factor=self.config["safety_factor"])
        self.meta_gate = MetaGate(self.policy, self.half_life)
        # Evidence-kernel governance (FEK): a supervening veto over the internal
        # gate. Promotion now also requires externally-checkable evidence
        # (producer != verifier, refutation supremacy, no foundry self-promotion),
        # recorded on an append-only, hash-chained log.
        import tempfile

        from fek.kernel import Kernel
        from rsi_foundry.governance.evidence_gate import EvidenceGate

        gov_root = self.config.get("governance_root") or tempfile.mkdtemp(prefix="rsi-gov-")
        self.evidence_gate = EvidenceGate(Kernel(gov_root))

        # bookkeeping
        self.registry = SuccessorRegistry()
        self.lineage = LineageGraph()
        self.results: dict[str, EvalResult] = {}
        self.candidates: dict[str, Candidate] = {}
        self.cycle_records: list[CycleRecord] = []
        self.reviews: list[dict] = []
        self.all_cids: list[str] = []

    # -- benchmark management (POET-driven) ----------------------------------
    def _refresh_benchmark(self) -> None:
        envs = self.poet.current()
        # stable (process-independent) version hash so replay is deterministic
        import hashlib
        h = hashlib.sha256("|".join(e.name for e in envs).encode()).hexdigest()
        version = int(h[:8], 16)
        if version != self._benchmark_version:
            rng = random.Random(version)
            self.benchmark = LocalBinPackBenchmark(envs, rng,
                                                   per_env=self.config["per_env_instances"])
            self.harness = Harness(self.benchmark, self.quorum_sandbox,
                                   self.config["benchmark_floor"])
            self.fast_harness = Harness(self.benchmark, self.fast_sandbox,
                                        self.config["benchmark_floor"])
            self._benchmark_version = version

    def _record(self, cand: Candidate, res: EvalResult) -> None:
        self.candidates[cand.cid] = cand
        self.results[cand.cid] = res
        self.all_cids.append(cand.cid)
        cand.meta["fitness"] = res.fitness
        self.lineage.add(cand.cid, cand.parents,
                         {"origin": cand.origin, "fitness": res.fitness, "gen": cand.generation})
        self.novelty.add(cand.cid, res.behavior, {"fitness": res.fitness})

    # -- seeding -------------------------------------------------------------
    def _seed(self) -> None:
        self._refresh_benchmark()
        g = heuristics.seed_genome()
        seed = build_candidate(g, [], "seed", 0)
        res = self.harness.evaluate(seed.cid, seed.source)
        self._record(seed, res)
        self.qd.add(seed, res)
        self.best_attr.observe(seed, res)
        self.registry.seed(seed, res)
        self.half_life.set_baseline_capability(res.fitness)

    # -- one recursive cycle -------------------------------------------------
    def _cycle(self, c: int) -> CycleRecord:
        self._refresh_benchmark()
        rng = self.hub.stream(f"cycle{c}")
        rec = CycleRecord(cycle=c)

        # 1. re-anchor capability reference to current champion on this benchmark
        champ = self.registry.champion_candidate()
        champ_res = self.harness.evaluate(champ.cid, champ.source)
        self.half_life.set_baseline_capability(champ_res.fitness)

        # 2. priors + anti-collapse novelty pressure
        priors = self.seal.priors()
        entropy = self.novelty.entropy()
        self.policy.novelty_min = (self.config["novelty_pressure"]
                                   if entropy < self.config["entropy_floor"] else 0.0)

        # 3. generate via composed loops
        ctx = LoopContext(rng=rng, generation=c, proposer=self.proposer,
                          parents=self.qd.parents(rng, 6), champion=champ,
                          champion_result=champ_res, priors=priors,
                          registry=self.best_attr, harness=self.fast_harness,
                          sandbox=self.fast_sandbox, benchmark=self.benchmark)
        proposed: dict[str, Candidate] = {}
        for cand in self.alphaevolve.generate(ctx):
            proposed[cand.cid] = cand
        for cand in self.dgm.generate(ctx):
            proposed.setdefault(cand.cid, cand)
        for cand in self.adas.generate(ctx):
            proposed.setdefault(cand.cid, cand)
        if c % self.config["scientist_every"] == 0:
            for cand in self.scientist.generate(ctx):
                proposed.setdefault(cand.cid, cand)
            if self.scientist.last_review:
                self.reviews.append(self.scientist.last_review)
                rec.notes.append("scientist:" + self.scientist.last_review["conclusion"])

        # 4. evaluate (containment + quorum)
        evaluated: list[tuple[Candidate, EvalResult]] = []
        contained_valid = 0
        cov_before = self.qd.coverage()
        for cand in proposed.values():
            if cand.cid in self.results:
                res = self.results[cand.cid]
            else:
                res = self.harness.evaluate(cand.cid, cand.source)
                self._record(cand, res)
            evaluated.append((cand, res))
            if res.valid:
                contained_valid += 1
                self.qd.add(cand, res)
                self.best_attr.observe(cand, res)
        rec.proposed = [c.cid for c in proposed.values()]

        # 5. mint assurance from verification work performed this cycle
        cov_gain = max(0.0, self.qd.coverage() - cov_before)
        renewal = (self.config["assurance_per_check"] * contained_valid
                   + self.config["assurance_per_coverage"] * cov_gain)
        self.half_life.add_assurance(renewal)

        # 6/7. gate, promote, learn
        promoted_this_cycle = 0
        breach_this_cycle = False
        for cand, res in evaluated:
            parent_res = self._parent_result(cand)
            novelty_score = self.novelty.novelty(res.behavior)
            if res.valid:
                causal = causal_gate.evaluate_causal(
                    cand, res, parent_res, self.fast_harness,
                    min_ablation=self.policy.causal_min_ablation,
                    min_task_frac=self.policy.causal_min_task_frac)
            else:
                causal = {"effect": 0.0, "pass": False, "ablation": {}}

            report = promotion.evaluate(
                cand, res, self.registry.champion_result(), parent_res,
                novelty_score, causal, self.half_life, self.policy, cand.cid)
            # Supervening evidence-kernel veto: files the report as a claim with
            # evidence/refutations and re-decides promotion under FEK policy.
            # `report.promoted` becomes (v0.2 gate) AND (FEK gate).
            report = self.evidence_gate.govern(cand, res, report)
            rec.gate_reports.append(report.to_dict())

            # SEAL: every candidate (esp. failures) becomes training signal
            self.seal.observe(self._parent_genome(cand), cand.genome,
                              parent_res.fitness if parent_res else None,
                              res.fitness, report.promoted, cand.cid)

            if report.promoted:
                self.registry.promote(cand, res, report)
                promoted_this_cycle += 1
                rec.promoted.append(cand.cid)
                if cand.meta.get("design"):
                    self.adas.reward(cand.meta["design"], max(0.0, report.fitness_delta))
            else:
                # A containment breach is a real governance event; a candidate
                # simply scoring worse than the champion is normal evolutionary
                # failure and must NOT tighten the gates.
                if not report.contained:
                    breach_this_cycle = True
                rec.archived.append(cand.cid)

            if self.half_life.should_halt():
                rec.notes.append("HALF-LIFE BLACK: halting")
                break

        # 8. coevolve benchmark (POET) and adjust gates (meta-gate, rate-limited)
        if breach_this_cycle:
            self.meta_gate.on_breach_or_regression("containment")
            rec.notes.append("meta-gate: tightened on containment breach")
        poet_info = self.poet.step(self._score_env_with_champion)
        if poet_info.get("added"):
            rec.notes.append(f"poet:+{poet_info['added']}@{poet_info['score']}")
        self.meta_gate.on_cycle_end(promoted_this_cycle)

        # 9. record cycle state
        rec.half_life_state = self.half_life.state
        rec.capability_index = round(self.half_life.capability, 5)
        rec.assurance_index = round(self.half_life.cumulative_assurance, 5)
        rec.population_entropy = self.novelty.entropy()
        rec.environment = {"envs": [e.name for e in self.poet.current()],
                           "qd_coverage": self.qd.coverage(),
                           "qd_score": self.qd.qd_score()}
        return rec

    # -- helpers -------------------------------------------------------------
    def _parent_genome(self, cand: Candidate) -> dict | None:
        if not cand.parents:
            return None
        p = self.candidates.get(cand.parents[0])
        return p.genome if p else None

    def _parent_result(self, cand: Candidate) -> Optional[EvalResult]:
        if not cand.parents:
            return None
        return self.results.get(cand.parents[0])

    def _score_env_with_champion(self, env: binpack.EnvSpec) -> float:
        champ = self.registry.champion_candidate()
        if champ is None:
            return 0.0
        inst = binpack.make_instance(env, self.hub.stream("poet_eval"))
        out = self.fast_sandbox.run(champ.source, [{"capacity": inst.capacity,
                                                    "items": inst.items}])
        if not out.get("ok"):
            return 0.0
        return binpack.instance_score(inst, out["results"][0]["bins_used"])

    # -- run + export --------------------------------------------------------
    def run(self, cycles: int | None = None) -> dict[str, Any]:
        cycles = cycles if cycles is not None else self.config["cycles"]
        self._seed()
        for c in range(1, cycles + 1):
            rec = self._cycle(c)
            self.cycle_records.append(rec)
            if self.half_life.should_halt():
                break
        return self.export()

    def export(self) -> dict[str, Any]:
        from rsi_foundry.core.runpack_exporter import build_runpack
        return build_runpack(
            config=self.config,
            root_seed=self.config["seed"],
            cycles=[r.to_dict() for r in self.cycle_records],
            registry=self.registry.to_dict(),
            qd=self.qd.to_dict(),
            seal=self.seal.snapshot(),
            half_life={"snapshot": self.half_life.snapshot(),
                       "history": self.half_life.history,
                       "adas_designs": self.adas.to_dict()},
            meta_gate_log=self.meta_gate.log,
            lineage=self.lineage.to_dict(),
            reviews=self.reviews,
            all_cids=self.all_cids,
        )
