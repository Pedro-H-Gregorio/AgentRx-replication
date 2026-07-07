# ADR-0014 — Braço A serializado em JSON estruturado; paridade semântica

- **Status**: Accepted
- **Data**: 2026-07-06
- **Relacionado**: PRD-06, PRD-08 (D40, D41); ADR-0003, ADR-0005, ADR-0006; change `structured-telemetry-arm`

## Contexto

O braço A (telemetria) representava a telemetria como **texto livre** apendado à prosa: emitia só o *nome* dos eventos
(`events=[dependency_call_completed]`, descartando `tool.output.count=2`) e nunca carregava stacktrace (o
`exception.stacktrace` bruto citava `faults/operators.py` e a categoria, então era sanitizado por inteiro). A prévia do
C8 mostrou telemetria ≈ ou < baseline — plausivelmente por um tratamento anêmico. O invariante #3 dizia que os dois
braços "diferem só nos campos de telemetria", pressupondo o **mesmo formato** em A e B.

## Decisão

O `content` do braço A passa a ser uma **string JSON** — os fatos semânticos mais um objeto `telemetry` enriquecido
(atributos de evento e, em passos de erro, um stacktrace limpo na origem). O **braço B permanece prosa**, fiel ao
formato que o artigo AgentRx consome. Com isso, a **paridade** deixa de ser "mesmo formato, só telemetria varia" e passa
a **paridade semântica**: os dois braços carregam os mesmos fatos; A difere por (a) o bloco `telemetry` e (b) o formato
de serialização. A IR segue com só `role`/`content` (invariante #6): o JSON vive **dentro** da string `content` — o
AgentRx só exige que `content` seja `str`, sem impor forma.

## Consequências

- A telemetria ganha uma representação estruturada e mais rica (atributos de evento, stacktrace), dando-lhe uma chance
  justa de ajudar o juiz sem descaracterizar a baseline.
- **Reinterpreta o invariante #3** (paridade): passa a ser semântica, verificada renderizando os fatos de A como prosa e
  comparando com B (não mais por prefixo de linha). O AGENTS.md é atualizado para refletir isso.
- **Ameaça à validade (confound):** formato e conteúdo mudam juntos em A → o tratamento é o *pacote* "telemetria
  estruturada" vs a baseline do artigo; um eventual ganho não se decompõe em "formato" vs "conteúdo" (PRD-08 D40). Um
  braço "JSON sem telemetria" (ou um `mas_id` irmão) decomporia isso em trabalho futuro.
- **Ameaça à validade (stacktrace):** só System Failure crasha → só ele tem stacktrace; a *presença* correlaciona com a
  categoria, por construção da realidade, não por vazamento (o conteúdo é limpo; PRD-08 D41).
- Regenerar as trajetórias invalida vereditos já coletados; exige re-`judge`/`collect` (o usuário re-roda o
  experimento).
- Não altera invariantes #1 (OTel bruto segue fonte; só a geração do stacktrace muda, upstream), #2 (reforçado: token
  `faults.`, `exception.type` reduzido ao nome simples) e #6 (IR intacta).

## Alternativas descartadas

- **JSON nos dois braços (simétrico):** isolaria o efeito de formato do de conteúdo, mas tornaria a baseline (B) infiel
  ao formato que o artigo consome — o usuário priorizou a fidelidade de B ao artigo.
- **Manter o braço A em texto livre:** preserva o formato, mas mantém o tratamento fraco que a prévia do C8 já mostrou
  não ajudar.
- **Adicionar o stacktrace bruto (com frames de `faults/`):** vazaria o ground truth; e o que ele tem de legítimo (tipo
  - mensagem da exceção) já está nos dois braços na linha `Error:`.
- **Fabricar stacktrace para as falhas semânticas** (para igualar a presença entre categorias): seria mentira — elas não
  crasham.
