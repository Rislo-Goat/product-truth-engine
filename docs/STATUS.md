# État d'avancement & auto-évaluation (spec §76)

Mise à jour : première itération (greenfield → socle fonctionnel testé).

## Phases (spec §72)

| Phase | Sujet | État |
|---|---|---|
| 0 | Audit repo | ✅ (repo vide → greenfield) |
| 1 | Infra + DB | 🟡 API/config/Docker/Railway OK ; modèles Postgres + Alembic = à faire |
| 2 | Supplier connector abstraction | ✅ ABC + registry + manual + aliexpress (honnête) |
| 3 | Product normalization | ✅ fingerprint + matching |
| 4 | Candidate discovery | ✅ multi-requêtes |
| 5 | Evidence engine | ✅ extraction + agrégation par hiérarchie de sources |
| 6 | **Product Truth** | ✅ **moteur critique testé (cas §70)** |
| 7 | Supplier Intelligence | ✅ score + risque (reviews = signaux) |
| 8 | Shipping Intelligence | ✅ delivery confidence |
| 9 | Economics | ✅ marge/profit, coûts UNKNOWN |
| 10 | SEO / KimberlyWexlerSEO | 🔴 connecteur à câbler (URL/API réelle requise) |
| 11 | Market / competitor | 🔴 à faire (données concurrents requises) |
| 12 | Q4 | ✅ date de commande sûre + score |
| 13 | Final scoring | ✅ axes séparés + final + hard blocks |
| 14 | Async jobs | ✅ jobs + fallback in-process (RQ si Redis) |
| 15 | Tool Registry | 🟡 `/capabilities` + registry connecteurs (embryon) |
| 16-19 | JARVIS Planner / Agent loop / Memory / Permissions | 🔴 à venir |
| 20-21 | Dashboard / intégrations réelles | 🔴 à venir |
| 22 | Déploiement Railway | 🟡 Dockerfile + railway.json prêts ; à déployer |
| 23 | Évaluation / optimisation | 🟡 ce document |

Légende : ✅ réel & testé · 🟡 partiel/prêt · 🔴 pas commencé.

## What works / What's mocked / What's unavailable (§76)

- **Works (réel, testé) :** Product Truth (hard blocks matière/corps/variante), extraction,
  normalisation, candidate discovery, économie, livraison/Q4, supplier/risk, scoring, pipeline
  PRODUCT→SUPPLIER, API `/sourcing/analyze` + jobs.
- **Mocked :** rien. Politique no-fake (§71) respectée — les tests utilisent des données
  explicites, pas des mocks de production.
- **Unavailable (documenté) :** API AliExpress/EPROLO (credentials + câblage HTTP),
  KimberlyWexlerSEO (endpoint réel), persistance Postgres, JARVIS Core.

## Prochaines étapes (ordre recommandé)

1. Modèles SQLAlchemy + migration Alembic (§63) → persistance products/suppliers/claims/evidence/scores/jobs.
2. Connecteur KimberlyWexlerSEO (une fois l'URL/API confirmée) → axes SEO/market réels + modes
   KEYWORD→PRODUCT et PRODUCT→KEYWORDS (§6-B/C).
3. Câblage HTTP réel AliExpress (dès credentials) → candidate discovery live.
4. Tool Registry complet + JARVIS Planner + agent loop (§40-§46).
5. Dashboard (§67-§68) consommant les vraies APIs.

## Fragile / à surveiller

- L'extraction d'attributs est à base de règles (lexique reborn dolls) : robuste et
  déterministe, mais à étendre par catégorie et éventuellement à assister par LLM
  (extraction structurée) — sans jamais inférer une matière par la seule image (§18).

## Multi-Model Router (spec §1-§22) — ajouté

| Élément | Module | État |
|---|---|---|
| Model Registry (catalogue vivant + dispo temps réel) | `ai/registry.py`, `ai/catalog.py` | ✅ réel + testé |
| Model Router (scoring par tier/capacités/coût/perf) | `ai/router.py` | ✅ réel + testé |
| Provider abstraction + adapters OpenAI/Anthropic/Gemini | `ai/providers.py` | ✅ (APIs officielles ; AUTH_REQUIRED sans clé) |
| Stratégies single/parallel/critic/ensemble/fallback | `ai/runner.py` | ✅ réel + testé |
| Disagreement engine (résolu par PREUVES, pas au vote) | `ai/disagreement.py` | ✅ réel + testé |
| Perf historique (alimente le router) | `ai/performance.py` | ✅ |
| Benchmark harness | `ai/benchmark.py` | 🟡 réel ; exécution = credentials requis |
| API transparente `/models`, `/models/route`, `/performance`, `/benchmark` | `api/routes_models.py` | ✅ + testé |

Principes tenus : **le LLM n'est pas JARVIS** (moteurs cognitifs interchangeables) ;
**evidence-first** (la vérité vient des données, pas de « le modèle a dit ») ;
**model-agnostic** (ajouter un provider = 1 classe + 1 entrée, aucun agent modifié) ;
**transparent** (le router explique son choix). Ajout d'un modèle/param à chaud via
`MODEL_CATALOG_JSON` ou `ModelRegistry.upsert/update_metadata`.
