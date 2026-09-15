# HANDOFF — JARVIS Ecommerce OS (product-truth-engine)

Brief de passation pour une autre session Claude Code. Tout le contexte pour
reprendre le développement sans rien redécouvrir.

## Où est le code
- **Repo GitHub** : `Rislo-Goat/product-truth-engine`
- **Branche de travail** : `claude/jarvis-vocal-enhanced-v7pw51` (PR draft **#1** vers `main`)
- `main` = commit fondation ; la branche porte tout le reste.
- Alternative offline : `git clone jarvis-ecommerce-os.bundle` (bundle fourni).

## Ce que c'est
Système agentique e-commerce (dropshipping SEO multi-boutiques) construit selon un
« Master Execution Spec » (85 sections). Priorité : **Sourcing Intelligence →
Product Truth → Multi-Model Router → JARVIS Core → Dashboard**.
Principes NON négociables :
- **Evidence-first** : la vérité vient des données/preuves, pas du LLM.
- **No-fake (§71/§79)** : rien d'inventé ; ce qui n'est pas prouvé reste `UNKNOWN`.
- **Hard blocks (§16)** prioritaires sur tout score.
- **Transparence (§18)** : le routing de modèles s'explique.

## Démarrer (aucune clé requise pour tester)
```bash
pip install -r requirements.txt
pytest                                   # 34 tests, tous verts
uvicorn jarvis_os.main:app --reload      # http://localhost:8000/  (dashboard) et /docs
```

## Carte des modules (`jarvis_os/`)
```
config.py                  # settings env (pydantic-settings), db/redis optionnels
main.py                    # FastAPI : monte les routers + sert le dashboard à /
schemas/                   # Pydantic : common(enums truth/risk), evidence, product,
                           #   sourcing, truth, api, audit
engines/
  extract.py               # extraction d'attributs (règles reborn) + agrégation par
                           #   hiérarchie de sources -> AttributeVerdict
  product_truth.py         # MOTEUR CRITIQUE : claim Shopify vs preuve fournisseur,
                           #   hard blocks matière/corps/variante (cas §70 testé)
  normalization.py         # fingerprint + matching (EXACT..DIFFERENT)
  candidate_discovery.py   # expansion multi-requêtes d'un mot-clé/niche
  economics.py             # marge/profit ; coûts manquants = UNKNOWN
  shipping.py              # delivery confidence + date de commande sûre Q4
  supplier_intelligence.py # score fournisseur + risque (reviews = signaux)
  scoring.py               # scores séparés + final (poids configurables, hard block)
  sourcing_pipeline.py     # orchestre PRODUCT->SUPPLIER -> ProductOpportunity explicable
  store_audit.py           # audit boutique temps réel (litiges/fiches trompeuses)
connectors/
  base.py, registry.py     # SupplierConnector (ABC) + registre
  manual.py                # ingère des données fournisseur réelles fournies (pas d'API)
  aliexpress.py            # structure prête ; AUTH_REQUIRED sans credentials (jamais de fake)
  shopify.py               # lit les boutiques EN DIRECT (SHOPIFY_STORES) -> Listing
ai/                        # MULTI-MODEL ROUTER (spec §1-§22)
  types.py, catalog.py     # ModelInfo + catalogue vivant (MODEL_CATALOG_JSON override)
  registry.py              # ModelRegistry + disponibilité temps réel (health providers)
  providers.py             # AIProvider (ABC) + OpenAI/Anthropic/Gemini (APIs officielles)
  router.py                # scoring par tier/capacités/coût/perf -> ModelSelection + reason
  runner.py                # stratégies single/parallel/critic/ensemble/fallback
  disagreement.py          # divergence tranchée par les PREUVES, jamais au vote (§5)
  performance.py, benchmark.py
api/                       # routes_health, routes_sourcing, routes_models, routes_stores
jobs/                      # store (jobs in-process), worker (RQ si REDIS_URL)
web/dashboard.html         # UI connectée : liste boutiques -> "Analyser en direct"
tests/                     # 34 tests (product_truth, engines, model_router, store_audit, api)
```

## API (voir /docs)
- `GET /` dashboard · `GET /info` · `GET /health` · `GET /capabilities`
- `POST /sourcing/analyze` {claim, candidates[], selling_price, destination, target_date}
- `POST /sourcing/jobs` -> {job_id} · `GET /sourcing/jobs/{id}`
- `GET /models` · `POST /models/route` (transparent, sans exécuter) · `/models/performance` · `/models/benchmark`
- `GET /stores` · `GET /stores/{name}/products` · `POST /stores/{name}/audit` (audit temps réel)

## Déploiement Railway (état actuel + piège résolu)
- Builder = Dockerfile. Services `web` (uvicorn) et `worker` (RQ, optionnel).
- **PIÈGE 502 « Application failed to respond »** = le domaine public ciblait un
  port ≠ de celui où l'app écoutait. Corrigé : le Dockerfile **fige le port 8000**.
  → Le domaine Railway doit cibler **8000** (Settings → Networking → port cible = 8000).
- Le `worker` affiche « Completed » sans Redis (normal : il sort proprement ; les jobs
  tournent in-process dans `web`). Pour l'activer : ajouter Redis + `REDIS_URL`.
- Variables (secrets Railway, jamais dans le repo) :
  - `SHOPIFY_STORES` = `[{"name","domain":"xxx.myshopify.com","token":"shpat_...","category":"reborn_doll"}]`
  - `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` (exécution des modèles ; sinon routing seul)
  - `ALIEXPRESS_APP_KEY/SECRET`, `EPROLO_API_KEY` (découverte fournisseur live)
  - `DATABASE_URL`, `REDIS_URL` (optionnels ; rien ne s'y connecte encore côté DB)

## Ce qui MARCHE (réel + testé)
Product Truth (hard blocks), extraction/evidence, normalisation, candidate discovery,
économie, livraison/Q4, supplier/risk, scoring, pipeline PRODUCT→SUPPLIER, audit
boutique temps réel, Multi-Model Router complet (registry/router/providers/runner/
disagreement/perf/benchmark), API + dashboard. **34 tests verts.**

## Ce qui est EN ATTENTE (honnête, ne pas simuler — §76)
1. **Persistance** : modèles SQLAlchemy + migration Alembic (§63). `DATABASE_URL` est lu
   mais AUCUN code ne s'y connecte encore.
2. **KimberlyWexlerSEO connector** : câbler l'endpoint SEO réel → axes `seo`/`market`
   (aujourd'hui `UNKNOWN`) + modes KEYWORD→PRODUCT / PRODUCT→KEYWORDS (§6-B/C).
3. **Supplier API** (AliExpress/EPROLO) : implémenter le HTTP réel dans `connectors/`
   (signature, endpoints) une fois les credentials fournis → découverte de candidats live.
4. **Product Truth complet dans le dashboard** : aujourd'hui l'audit boutique = qualité/
   litige (côté Shopify seul). Attacher la preuve fournisseur (via `manual`/API) pour la
   comparaison complète claim vs supplier par produit.
5. **JARVIS Core (§40-§62)** : Tool Registry (engines + connecteurs + modèles = tools),
   Planner, agent loop (perceive→plan→select→execute→observe→validate→critique), Memory,
   Policy/permissions. Le Multi-Model Router est déjà prêt à être branché dessous.
6. **Q4 opportunity score, competitor intelligence, price intelligence** : à enrichir.
7. **Dashboard** : pages /sourcing, /truth, /opportunities, /suppliers (§67-§68).

## Ordre recommandé pour la suite (spec §23/§72)
Persistance DB → KWSEO connector → Supplier API → Tool Registry → JARVIS Planner →
Agent loop → Memory → pages dashboard.

## Rappels catégorie
Schéma de catégorie extensible dans `schemas/product.py` (reborn_doll d'abord :
attributs critiques material/body_type/gender/variant avec hard_block_on_conflict).
Ne JAMAIS inférer une matière par la seule apparence d'une image (§18).
