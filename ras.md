1. D14 (higiene) — os trade-offs, como você pediu Vou te dar o argumento mais forte contra a sua posição, e depois a
   minha recomendação real — que, spoiler, concorda com você em ~80%.

O risco que o filtro cobriria. Com USE_LLM=true, a prosa dos passos é gerada por LLM. Se o modelo alucinar em um passo
não-injetado (ex.: o Researcher cita um item que não existe na evidência), a trajetória passa a conter duas falhas — a
injetada e a emergente. O juiz pode apontar a emergente, e o seu scoring marca "miss"… sendo que o juiz acertou. Isso
suja a variável dependente.

Por que o risco é menor do que o PRD-08 hoje sugere (argumentos a seu favor):

A contaminação é simétrica por construção. Os dois braços derivam do mesmo trace OTel — a prosa alucinada aparece
idêntica nos dois. A comparação A/B (que é a RQ) sofre menos que as acurácias absolutas. Não é perfeitamente neutro (a
telemetria poderia tornar o erro emergente mais visível num braço), mas o desenho pareado já amortece bastante. As ações
são scriptadas. O LLM só narra; tool calls, argumentos e resultados vêm do código determinístico. A superfície de erro
emergente é só a prosa — bem menor que num agente LLM de verdade. Um filtro automático de "prosa desancorada" é ele
próprio um julgamento. Regras de grounding têm falsos positivos/negativos, e defender o filtro na banca pode dar mais
trabalho que defender a ameaça declarada. O que eu não abriria mão (o ~20% onde te convenço do contrário): não dá para
simplesmente silenciar o tema, porque um examinador vai perguntar "como você sabe que a falha injetada era a única falha
na trajetória?". A resposta precisa existir em disco. E há um jeito de tê-la sem nenhum código no C7:

Opção Custo O que te dá A. Filtro automático completo (grounding + run de controle) alto (módulo novo, testes, defesa do
critério) exclusão automática; era o plano original B. Sem filtro + ameaça declarada + protocolo de auditoria manual
~zero de código os próprios CSVs denunciam os suspeitos: cenário onde os dois braços, nas 3 reps, apontam
consistentemente um passo ≠ injetado é candidato a erro emergente — você audita esses (serão poucos) lendo a trajetória,
e decide caso a caso, registrando no PRD-08 C. Nada zero risco na banca sem resposta preparada Minha recomendação: opção
B. O C7 fica "burro e fiel" como você exigiu (nenhuma coluna de higiene, nenhum julgamento na coleta); a auditoria é um
protocolo documentado (meia página no PRD-07 ou num doc de método), executado por você sobre os CSVs depois do
experimento. Isso exige uma correção no PRD-08: a seção "Consequências de D31" hoje diz que o C7 SHALL implementar o
filtro — essa entrada será supersedida por uma nova decisão ("filtro automático descartado; auditoria manual pareada +
ameaça à validade"), mantendo o histórico como o log manda.

2. I1 — julgamento coluna a coluna do PRD-10 contra o que existe hoje Fiz a checagem de viabilidade de cada campo contra
   os artefatos reais em disco. Veredito geral: tudo é computável hoje, com 5 ajustes pontuais.

runs_long.csv (1 linha por execução do juiz):

Campo (PRD-10) Temos hoje? Origem real scenario_id ✅ run_id do índice (são a mesma coisa — ver nota abaixo) arm ✅ índice
judge_idx ✅ rep do índice pred_step ✅ predicted_step do índice pred_category (int 1–10) ⚠️ ajuste índice tem o nome;
converter pela tabela inversa de scoring.py agentrx_run_name ⚠️ ajuste não existe "run name" do AgentRx — nós
controlamos os run dirs; usar o run_dir relativo (telemetry/q01\_.../rep2), que cumpre a mesma função de rastreio (novo)
raw_failures_json ➕ as failures brutas da rep (do run1.json) — é o que garante a regra de reconstrução do PRD-10 §5 sob
a agregação por pooling (I2 que você aprovou) trajectory_index.csv: tudo disponível. n_steps = contagem de steps no JSON
da trajetória; otel_path = data/internal/otel/\<run_id>.otel.json; sent_at = mtime do run1.json (I7 aprovado). Uma nota:
o PRD-10 traz run_id e scenario_id como campos distintos (exemplo "run_007"), mas o PRD-INDEX define que identificador
de run = id do cenário — no nosso desenho as duas colunas terão o mesmo valor. Recomendo manter as duas (esquema
estável, custo zero) e documentar a coincidência no dicionário.

metricas.csv: todas as fórmulas de §4.3/§4.4 são computáveis do pool das reps. Três pontos de honestidade que o
design.md deve registrar:

n_judge_runs = número de reps ok realmente agregadas (se uma rep está error, a linha sai com n_judge_runs=2, sem juízo
de valor — coletor neutro; quem decide se aceita n\<3 é a análise). category_std replica o compute_stats fielmente
(judge.py:350): é desvio-padrão dos inteiros de failure_case — estatisticamente esquisito (desvio de uma variável
categórica), mas é o que o AgentRx computa; manter por fidelidade e anotar a ressalva no dicionário.
failure_case_accuracy_perrun sob pooling = fração das failures do pool que batem com o GT (é o que o compute_stats faz),
não "fração das n execuções". Nome mantido, semântica documentada. As 4 variantes de categoria
(cat_acc_any/earliest/terminal) colapsam na crítica no MAS (GT tem 1 falha) — já previsto no PRD-07 §6, o coletor as
emite iguais. 3. I6 — o que é o experiment_id, com exemplos reais Ele já existe e é derivado da config, não de timestamp
(config.py:126-134): judge-<backend>-<modelo-slugificado>. Exemplos concretos que a sua máquina já produziu ou
produziria:

JUDGE_BACKEND=stub → judge-stub (sem modelo — o stub é agnóstico) JUDGE_BACKEND=openai,
JUDGE_MODEL=google/gemma-3-27b-it:free → judge-openai-google-gemma-3-27b-it-free JUDGE_BACKEND=codex, JUDGE_MODEL vazio
→ judge-codex (o modelo efetivo, gpt-5.5, fica no manifesto/índice) JUDGE_BACKEND=copilot, JUDGE_MODEL=gpt-5-mini →
judge-copilot-gpt-5-mini Como você vai rodar com 1 juiz, haverá 1 diretório — e se um dia rodar um segundo, nasce um
diretório irmão, sem quebra nenhuma:

data/outputs/ └── judge-copilot-gpt-5-mini/ ← seu experimento ├── runs_long.csv ├── trajectory_index.csv └──
metricas.csv (└── judge-codex/ ← só SE um 2º juiz rodar; nada muda no código) Sobre
data/experiment/results/\<experiment_id>: eu recomendo manter data/outputs/\<experiment_id>/. Motivo: data/outputs/ já é
a casa documentada dos resultados no AGENTS.md, no PRD-01 e no ARCHITECTURE.md — criar data/experiment/ seria uma
mudança estrutural (exigiria ADR + patch em três documentos) para ganhar um sinônimo de "outputs". A semântica que você
quer ("resultados do experimento") é exatamente o que outputs/ significa nesse repo. Se mesmo assim preferir o novo
caminho, é viável — só entra como decisão arquitetural formal na change.

4. O que é o docs/examples/ É uma referência que os PRDs 07 e 10 prometem e nunca foi criada: um exemplo de mesa, feito
   à mão, do tipo:

"Cenário fictício q99, 3 execuções do juiz devolveram (categoria 9, passo 3), (9, 3), (3, 5). Então:
most_common_category=9, step_mean=3.67, step_acc_exact = (round(3.67)=4 == 3?) → 0, step_acc_tol1=1,
avg_step_distance=0.67…"

— com a linha resultante de cada CSV escrita por extenso. Serve para duas coisas: (a) validar o dicionário de dados
antes de codar (você confere as fórmulas no papel); (b) virar o teste golden do coletor — o teste alimenta essas
entradas e exige exatamente aquela linha. Documentação e teste são o mesmo artefato, de graça. É pequeno (1 markdown + 1
fixture) e eu o manteria no escopo.

5. C7 replanejado Escopo: coletor neutro que transforma data/internal/agentrx/\<experiment_id>/ nos 3 CSVs do PRD-10.
   Sem higiene automática (opção B), sem qualquer escolha analítica — nenhum teste estatístico, nenhuma comparação de
   juízes, nenhuma exclusão de linha. Só fórmulas determinísticas do dicionário.

Área Mudança src/agentrx_otel_poc/collect/ novo domínio isolado (seu voto): leitura do índice/run1/GT/trajetórias,
agregação por pooling (fiel ao compute_stats), montagem das linhas, checagens de integridade do PRD-10 §5
scripts/collect_agentrx.py CLI fino (padrão run_judge.py): --experiment <id> (default: todos os experimentos em disco)
Makefile collect + validate-csv (cada passo valida a própria saída) tests/ golden test (docs/examples), paridade
numérica vs fixtures do compute_stats, integridade §5 (reconstrução runs_long→metricas, sem órfãos, faixas), teste de
neutralidade (coletor não lê nada além dos insumos declarados) docs/examples/ exemplo de referência preenchido à mão
PRDs PRD-05 §5 → aponta ao PRD-10; PRD-05 §6 ponteiro corrigido; PRD-07 §8 corrigido (runner = run_judge.py; reuso do
compute_stats removido em favor de reimplementação+fixtures); PRD-10 ganha as colunas ajustadas (int+nome,
raw_failures_json, run_dir) PRD-08 novas entradas: agregação por pooling (I2), fixtures de paridade (I5), layout
data/outputs/\<experiment_id> (I6), supersede do "filtro D14 obrigatório" → auditoria manual pareada + ameaça à validade
Critérios de aceite:

make smoke-judge && make collect produz os 3 CSVs offline (stub) — o caminho inteiro é validável sem juiz real. Todo
campo bate com o PRD-10 atualizado (nome, tipo, faixa); regras de integridade §5 verificadas por teste, incluindo
reconstrução de metricas.csv a partir de runs_long.csv. Paridade numérica com compute_stats/analysis provada por
fixtures versionadas (com a proveniência das fixtures documentada); nenhum import de agentrx em lugar nenhum. Coletor
100% neutro: mesmo experimento em disco → mesmos bytes de CSV em duas execuções; reps error aparecem refletidas em
n_judge_runs, nunca descartadas silenciosamente. Golden test do exemplo de referência passa. make check verde; PRDs
reconciliados; PRD-08 com as 4 decisões novas. Fica faltando você bater o martelo em 2 coisas: (1) D14 — aceita a opção
B (sem filtro no código, protocolo de auditoria manual + supersede no PRD-08)? (2) diretório —
data/outputs/\<experiment_id>/ como recomendo, ou insiste no data/experiment/results/ (aí vira ADR)? Com essas duas
respostas, o plano está fechado e dá para rodar o /opsx:propose do C7.
