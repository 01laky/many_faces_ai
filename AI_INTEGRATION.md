# AI integrácia – čo je pripravené a ako to funguje

## 1. Voľný AI model pre Python

- **Model:** **DistilGPT-2** (Hugging Face: `distilgpt2`)
- **Dôvod výberu:**
  - Beží lokálne na CPU, bez API kľúča a bez externých služieb
  - Malá veľkosť (~82M parametrov, cca 80 MB), vhodný na demo a vývoj
  - Licencia Apache 2.0
  - Knižnica `transformers` + `torch` – štandardný spôsob použitia v Pythone

## 2. Čo bolo pripravené

### 2.1 Služba pre komunikáciu s modelom

- **Súbor:** `services/ai_model_service.py`
- **Trieda:** `AIModelService`
- **Funkcie:**
  - **Lazy loading:** model sa načíta až pri prvom volaní `generate()`, aby server štartoval rýchlo
  - **`generate(prompt, max_new_tokens=50, ...)`** – dopĺňa zadaný text (prompt) a vráti prompt + vygenerované pokračovanie
  - Voliteľné parametre: `do_sample`, `temperature` (ovplyvňujú náhodnosť / kreativitu výstupu)
  - Všetky dôležité časti sú v kóde okomentované (slovensky)

### 2.2 gRPC integrácia

- **Proto:** V `proto/health.proto` boli pridané:
  - **RPC:** `Generate(GenerateRequest) returns (GenerateResponse)`
  - **GenerateRequest:** `prompt` (string), `max_new_tokens` (int32, voliteľné)
  - **GenerateResponse:** `text` (vygenerovaný text), `error` (prípadná chyba)
- **Server:** V `server.py`:
  - Pri štarte sa vytvorí inštancia `AIModelService` (model sa ešte nenačítava)
  - `HealthServiceServicer` má novú metódu `Generate`, ktorá:
    - overí, či je `AIModelService` k dispozícii,
    - zavolá `_ai_service.generate(prompt, max_new_tokens=...)`,
    - vráti `GenerateResponse(text=..., error=...)` alebo chybovú hlášku v `error`
  - Ak `transformers`/`torch` nie sú nainštalované, server beží ďalej, ale `Generate` vráti chybu v `error`

### 2.3 Závislosti a Docker

- **requirements.txt:** pridané `transformers`, `torch`, `accelerate`
- **Dockerfile.dev:** do image sa kopíruje priečinok `services/`
- **Proto:** po úprave `health.proto` je potrebné znovu vygenerovať Python kód (v Dockeri sa robí počas buildu)

## 3. Ako to funguje (tok)

1. **Štart servera**
   - Načíta sa gRPC kód z `proto/` a zaregistruje sa `HealthService` (HealthCheck + Generate).
   - Vytvorí sa `AIModelService()` – model sa zatiaľ nenačítava.

2. **Prvý Generate request**
   - Klient zavolá `Generate(prompt="The weather today is", max_new_tokens=30)`.
   - Server v `Generate` zavolá `_ai_service.generate("The weather today is", max_new_tokens=30)`.
   - V `AIModelService.generate()` sa pri prvom volaní zavolá `_get_pipeline()`:
     - stiahne sa (alebo načíta z cache) model `distilgpt2`,
     - vytvorí sa `transformers` pipeline `text-generation`.
   - Pipeline vygeneruje pokračovanie textu; výsledok sa vráti ako `GenerateResponse.text`.

3. **Ďalšie Generate requesty**
   - Model je už v pamäti, žiadne ďalšie sťahovanie – len inferencia.

4. **Chybové stavy**
   - Prázdny `prompt` → `GenerateResponse(error="prompt is required")`.
   - Chýbajúce `transformers`/`torch` → `GenerateResponse(error="AIModelService not available...")`.
   - Výnimka počas generovania → loguje sa a do klienta sa vráti `GenerateResponse(text="", error=str(e))`.

## 4. Ako to spustiť a otestovať

- **Lokálne (s vygenerovaným proto a nainštalovanými závislosťami):**
  ```bash
  pip install -r requirements.txt
  ./generate_proto.sh   # alebo vygenerovať proto podľa README
  python server.py
  ```
- **V Dockeri (odporúčané):**
  ```bash
  ./rebuild-dev.sh
  ./start-dev.sh
  ```
  Proto sa vygeneruje počas buildu, `services/` sa skopíruje do image.

- **Test Generate RPC (napr. grpcurl):**
  ```bash
  grpcurl -plaintext -d '{"prompt": "The weather today is", "max_new_tokens": 20}' localhost:50051 health.HealthService/Generate
  ```

## 5. Súhrn

| Čo | Kde | Účel |
|----|-----|------|
| Voľný model | DistilGPT-2 (Hugging Face) | Lokálna textová generácia bez API kľúča |
| Služba | `services/ai_model_service.py` | Načítanie modelu, metóda `generate()` |
| gRPC | `proto/health.proto`, `server.py` | RPC `Generate` a jeho obsluha |
| Závislosti | `requirements.txt`, Dockerfile | `transformers`, `torch`, `accelerate` |

Všetko dôležité v kóde je okomentované (slovensky v službe, anglicky/slovensky v serveri a proto).
