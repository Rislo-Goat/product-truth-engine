"""Product Truth Engine (spec §10-§16) — le moteur critique.

Question fondamentale : le produit que le Shopify AFFIRME vendre correspond-il
réellement au produit du fournisseur ?

On compare, attribut par attribut (au niveau critique en priorité) :
  claim  = valeur agrégée côté Shopify (revendication)
  evidence = valeur agrégée côté fournisseur (réalité, pondérée par la hiérarchie)

Règles dures (spec §16) :
  - conflit matière / body_type / variante  -> HARD BLOCK
  - attribut critique inconnu                -> pas de scale (can_scale=False)
Un excellent score ne peut jamais annuler un hard block.
"""
from __future__ import annotations

from ..schemas.common import TruthState
from ..schemas.product import Listing, get_category_schema
from ..schemas.truth import AttributeTruth, TruthReport, TruthVerdict
from .extract import aggregate, extract_evidence

_STATE_SCORE = {
    TruthState.VERIFIED: 1.0,
    TruthState.LIKELY: 0.7,
    TruthState.UNKNOWN: 0.3,
    TruthState.CONFLICT: 0.0,
    TruthState.FALSE: 0.0,
}


def assess_truth(claim: Listing, evidence: list[Listing], category: str) -> TruthReport:
    schema = get_category_schema(category)
    report = TruthReport(category=category)
    if schema is None:
        report.notes.append(f"Aucun schéma pour la catégorie '{category}' — vérification limitée.")
        return report

    claim_v = aggregate(extract_evidence(claim, category))
    ev_all: list = []
    for lst in evidence:
        ev_all.extend(extract_evidence(lst, category))
    ev_v = aggregate(ev_all)

    critical_scores: list[float] = []

    # On parcourt tous les attributs du schéma + ceux réellement observés.
    names = set(a.name for a in schema.attributes) | set(claim_v) | set(ev_v)
    for name in sorted(names):
        rule = schema.rule(name)
        critical = bool(rule and rule.critical)
        hard_on_conflict = bool(rule and rule.hard_block_on_conflict)

        cv = claim_v.get(name)
        ev = ev_v.get(name)
        claim_value = cv.value if cv else None
        evidence_value = ev.value if ev else None
        at = AttributeTruth(attribute=name, critical=critical,
                            claim_value=claim_value, evidence_value=evidence_value,
                            evidence=(ev.evidence if ev else []))

        # Détermination de l'état de vérité de la revendication.
        if cv and cv.state == TruthState.CONFLICT:
            at.state = TruthState.CONFLICT
            at.note = "Revendication Shopify elle-même contradictoire."
        elif claim_value is None and evidence_value is None:
            at.state = TruthState.UNKNOWN
        elif claim_value is None and evidence_value is not None:
            # pas de revendication : information fournisseur seulement
            at.state = ev.state
            at.confidence = ev.confidence
            at.note = "Donnée fournisseur sans revendication Shopify correspondante."
        elif claim_value is not None and evidence_value is None:
            at.state = TruthState.UNKNOWN
            at.confidence = 0.0
            at.note = "Revendication non vérifiée (aucune preuve fournisseur)."
        elif claim_value == evidence_value:
            at.confidence = round(min(cv.confidence, ev.confidence), 3)
            at.state = TruthState.VERIFIED if at.confidence >= 0.7 else TruthState.LIKELY
        else:
            # revendication contredite par la preuve
            at.confidence = round(ev.confidence, 3)
            at.state = TruthState.FALSE if ev.confidence >= 0.7 else TruthState.CONFLICT
            at.note = f"Shopify: '{claim_value}' vs fournisseur: '{evidence_value}'."

        # Hard blocks / drapeaux
        if at.state in (TruthState.CONFLICT, TruthState.FALSE):
            report.conflicts.append(name)
            if hard_on_conflict:
                at.hard_block = True
                report.hard_blocks.append(name)
        if critical and at.state == TruthState.UNKNOWN and claim_value is not None:
            report.unknown_critical.append(name)
        elif critical and claim_value is None and evidence_value is None:
            report.unknown_critical.append(name)

        if critical:
            critical_scores.append(_STATE_SCORE.get(at.state, 0.3))
        report.attributes[name] = at

    report.truth_score = round(100 * (sum(critical_scores) / len(critical_scores)), 1) \
        if critical_scores else 0.0
    report.can_scale = not report.unknown_critical and not report.hard_blocks

    # Verdict (un hard block prime sur tout, spec §16)
    if report.hard_blocks:
        report.verdict = TruthVerdict.BLOCK
    elif "package_contents" in report.conflicts:
        report.verdict = TruthVerdict.HIGH_RISK
    elif report.conflicts or report.unknown_critical or report.truth_score < 70:
        report.verdict = TruthVerdict.REVIEW
    else:
        report.verdict = TruthVerdict.OK
    return report
