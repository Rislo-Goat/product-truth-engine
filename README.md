# JARVIS Ecommerce OS

Système agentique e-commerce : **Sourcing Intelligence** + **Product Truth** aujourd'hui,
**JARVIS Core** (orchestrateur généraliste) ensuite. Objectif : décider *quel produit,
chez quel fournisseur, à quel prix, pour quel mot-clé* — avec preuves, marges, risques,
Q4 et **zéro hallucination** (spec §79 : ce qui n'est pas vérifié reste `UNKNOWN`).

> Ce dépôt était vide au démarrage ; il est construit de zéro selon le *Master Execution Spec*.
> Priorité (spec §4) : **Sourcing → Product Truth → JARVIS Core → Dashboard**.

## Ce qui fonctionne réellement (testé)

| Domaine | Module | État |
|---|---|---|
| **Product Truth** (moteur critique) | `engines/product_truth.py` | ✅ réel + testé (dont le cas obligatoire §70) |
| Extraction d'attributs + agrégation par hiérarchie de sources | `engines/extract.py` | ✅ réel + testé |
| Normalisation & matching produit | `engines/normalization.py` | ✅ réel |
| Candidate discovery (multi-requêtes) | `engines/candidate_discovery.py` | ✅ réel + testé |
| Économie (marge/profit, coûts UNKNOWN jamais inventés) | `engines/economics.py` | ✅ réel + testé |
| Livraison + Q4 (date de commande sûre) | `engines/shipping.py` | ✅ réel + testé |
| Supplier & Risk intelligence (reviews comme signaux) | `engines/supplier_intelligence.py` | ✅ réel |
| Scoring séparé + final (poids configurables, hard blocks) | `engines/scoring.py` | ✅ réel + testé |
| Pipeline PRODUCT→SUPPLIER explicable | `engines/sourcing_pipeline.py` | ✅ réel + testé |
| API + jobs async (fallback in-process) | `api/`, `jobs/` | ✅ réel + testé |
| **Multi-Model Router** (registry + routing par tâche) | `ai/router.py`, `ai/registry.py` | ✅ réel + testé |
| Providers OpenAI/Anthropic/Gemini (abstraction) | `ai/providers.py` | ✅ (AUTH_REQUIRED sans clé) |
| Stratégies single/critic/ensemble/fallback + disagreement par preuves | `ai/runner.py`, `ai/disagreement.py` | ✅ réel + testé |

**30 tests passent** (`pytest`). Aucune donnée n'est inventée.

## Ce qui est explicitement en attente (honnête — spec §71, §76)

- **Connecteurs API fournisseurs** (`connectors/aliexpress.py`) : structure prête, mais
  **AUTH_REQUIRED** tant que `ALIEXPRESS_APP_KEY/SECRET` ne sont pas fournis. Sans creds,
  le connecteur refuse de fournir des données (jamais de fake). Le connecteur **`manual`**
  permet d'analyser dès maintenant des données fournisseur *réelles* que tu fournis.
- **KimberlyWexlerSEO** : connecteur SEO non encore câblé (nécessite l'URL/API réelle) →
  axes `seo`/`market` = `UNKNOWN` dans le scoring pour l'instant.
- **Postgres/Redis** : optionnels. Sans `DATABASE_URL`/`REDIS_URL`, l'app tourne (jobs
  in-process, pas de persistance). Modèles DB + migrations : prochaine étape (§63).
- **JARVIS Core / Tool Registry / Planner / Dashboard** : phases suivantes (§40+).

## Démarrer

```bash
pip install -r requirements.txt
pytest                                   # 16 tests
cp .env.example .env                     # optionnel (aucun secret requis pour tester)
uvicorn jarvis_os.main:app --reload      # http://localhost:8000/docs
```

Docker / Railway :
```bash
docker compose up --build                # api + worker + postgres + redis
```
Railway build le `Dockerfile` (healthcheck `/health`). Variables : voir `.env.example`.

## API

- `GET /health` · `GET /capabilities` — état, connecteurs, moteurs, poids de scoring
- `POST /sourcing/analyze` — analyse synchrone : `{claim, candidates[], selling_price, destination, target_date}`
- `POST /sourcing/jobs` → `{job_id}` · `GET /sourcing/jobs/{id}` — job asynchrone avec progression

Exemple (bloque un mensonge produit) :
```bash
curl -s localhost:8000/sourcing/analyze -H 'content-type: application/json' -d '{
  "category":"reborn_doll","selling_price":109.99,"destination":"UK",
  "claim":{"source":"shopify:kim","title":"Full Silicone Reborn Boy 50cm"},
  "candidates":[{"supplier":"manual","external_id":"s2","title":"Reborn doll 50cm","price":20,
    "listing":{"source":"supplier:manual#s2","title":"Reborn doll 50cm",
      "specifications":{"material":"vinyl","body":"cloth body"},
      "description":"soft cloth body with vinyl limbs boy"}}]}'
# -> recommendation: REJECT, hard_blocks: ["material","body_type"] (Shopify ment sur la matière)
```

## Architecture (cible, spec §3)

```
JARVIS CORE (à venir) : Memory · Planner · Policy · Tool Registry/Selector · Agent loop
        │  (les engines ci-dessous seront ses "tools")
Sourcing Intelligence ── Product Truth ── SEO/AEO ── Economics ── Shipping/Q4 ── Supplier
```

Principes tenus : scores **séparés** jamais opaques (§32), **hard blocks** prioritaires sur
le score (§16), **explicabilité** (why/unknowns/verify, §33), **UNKNOWN** jamais transformé
en vérité (§13, §79).

Détail de l'état d'avancement : [`docs/STATUS.md`](docs/STATUS.md).
