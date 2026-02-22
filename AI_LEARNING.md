# Ako môže AI model „vedieť viac“ – kontext, RAG, fine-tuning

Model **DistilGPT-2** je **predtrénovaný** na veľkom množstve všeobecného textu. Z našej chatovej konverzácie sa **sám od seba nič nenaučí** – každé volanie je samostatné, bez pamäte. Existujú tri hlavné spôsoby, ako mu dať viac informácií alebo ho prispôsobiť:

---

## 1. Kontext konverzácie (v rámci session)

**Čo to je:** Pri každej novej správe pošleme modelu nielen aktuálnu otázku, ale aj **posledných N párov (používateľ → AI)** v texte. Model tak „vidí“ predchádzajúci priebeh rozhovoru a môže naň nadväzovať.

**Výhody:**
- Žiadne trénovanie, žiadna zmena váh modelu
- Rýchla implementácia (formátovanie promptu na BE)
- V rámci jednej session model „pamätá“ predchádzajúce správy

**Nevýhody:**
- Pamäť len počas jednej konverzácie; po odhlásení / novom chate je kontext prázdny
- Obmedzená dĺžka – do promptu sa zmestí len obmedzený počet správ (token limit)

**V tejto demo aplikácii:** BE pri `SendToAi` dostane od FE históriu (posledných N párov) a zloží z nej prompt napr. `User: ...\nAI: ...\nUser: ...\nAI:`, potom zavolá Python s týmto promptom a vráti klientovi len novú časť odpovede (bez opakovania promptu).

---

## 2. RAG (Retrieval-Augmented Generation)

**Čo to je:** Vlastná **znalostná báza** (dokumenty, FAQ, manuály). Pri každej otázke:
1. Otázka sa odošle do **vektorovej databázy** (napr. embeddings z otázky).
2. Vyhľadajú sa **relevantné úryvky** z dokumentov.
3. Tieto úryvky sa **doplnia do promptu** ako kontext (napr. „Podľa nasledujúceho textu: … Odpovedz na otázku: …“).
4. Model generuje odpoveď na základe tohto kontextu – **váhy modelu sa nemenia**.

**Výhody:**
- Model „vie“ z tvojich dokumentov bez trénovania
- Dá sa meniť znalostná báza bez opätovného trénovania
- Vhodné pre firemné know-how, dokumentáciu, FAQ

**Nevýhody:**
- Treba riešiť embedding model, vektorovú DB, chunkovanie dokumentov
- Viac komponentov (indexovanie, vyhľadávanie, formátovanie promptu)

---

## 3. Fine-tuning (natrénovanie na vlastných dátach)

**Čo to je:** Zoberie sa predtrénovaný model a **dotrénuje sa** na vlastnej množine dát (napr. páry otázka–odpoveď, dialógy, špecifická doména). Váhy modelu sa **trvalo zmenia**; uloží sa nový checkpoint a ten sa používa pri inferencii.

**Výhody:**
- Model sa skutočne „naučí“ tvoju doménu / štýl
- Odpovede môžu byť presnejšie a konzistentnejšie s tréningovými dátami

**Nevýhody:**
- Potrebný tréningový dataset (čo najkvalitnejší)
- Výpočtové zdroje (GPU), čas trénovania
- Pri zmenách dát treba znova trénovať alebo použiť ľahšie varianty (LoRA, adaptéry)

---

## Zhrnutie

| Spôsob              | Model sa učí? | Pamäť / znalosť              | Náročnosť      |
|---------------------|---------------|------------------------------|----------------|
| Kontext konverzácie | Nie           | Len v rámci session (prompt) | Nízka          |
| RAG                 | Nie           | Znalostná báza (dokumenty)   | Stredná        |
| Fine-tuning         | Áno           | Natrvalo v váhach modelu     | Vyššia         |

V tejto demo sme implementovali **kontext konverzácie** – FE posiela posledných N správ, BE z nich poskladá prompt a Python vráti odpoveď; model tak v rámci jednej session „pamätá“ predchádzajúci rozhovor.
