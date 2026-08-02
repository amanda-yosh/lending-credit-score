#!/usr/bin/env python3
"""
Aplica triagem T1 nos papers marcados como REVISAR,
usando título + abstract completo.

Uso: python3 triagem_manual.py <entrada.csv> <saida.csv>
"""

import re
import csv
import sys


def classificar_completo(title, abstract):
    t = title.lower()
    a = abstract.lower()

    # ---------- CE-1: crédito não-financeiro ----------

    if re.search(r'carbon[ -]credit|carbon offset|carbon[ -]neutral|carbon emission', t + a[:200]):
        return 'EXCLUIR', 'CE-1', 'Carbon credit (não crédito financeiro)'

    if re.search(r'(university|academic|school|education)\s+credit', t):
        return 'EXCLUIR', 'CE-1', 'Crédito acadêmico'

    if re.search(r'credit\s+bank.{0,40}(school|learn|educat)', t):
        return 'EXCLUIR', 'CE-1', 'Credit bank educacional'

    if re.search(r'letter[ -]of[ -]credit', t):
        return 'EXCLUIR', 'CE-1', 'Letter of Credit (comércio exterior)'

    if re.search(r'credit card', t):
        return 'EXCLUIR', 'CE-1', 'Credit card (não lending protocol)'

    # ---------- CE-2: blockchain em finanças tradicionais ----------

    if re.search(r'board communication|corporate governance', t) and re.search(r'credit risk|banking', t):
        return 'EXCLUIR', 'CE-2', 'Governança corporativa + crédito bancário'

    if re.search(r'insurance|insurer', t) and re.search(r'credit swap|blockchain', t):
        return 'EXCLUIR', 'CE-2', 'Seguro + blockchain (sem lending descentralizado)'

    if re.search(r'trade finance', t) and not re.search(r'defi|decentralized|smart contract', t):
        return 'EXCLUIR', 'CE-2', 'Trade finance (sem componente descentralizado)'

    # ---------- CE-3: credit scoring ML puro ----------

    is_scoring_title = bool(re.search(r'credit scor(e|ing|er)', t))
    has_defi_context = bool(re.search(
        r'defi|decentralized finance|peer.to.peer|p2p lend|smart contract lend|blockchain lend',
        t + ' ' + a
    ))
    has_ml_only = bool(re.search(
        r'machine learning|deep learning|federated learning|neural network|random forest|xgboost|lightgbm',
        a
    ))

    if is_scoring_title and has_ml_only and not has_defi_context:
        return 'EXCLUIR', 'CE-3', 'Credit scoring ML puro (sem sistema de lending)'

    # ---------- CE-4: fraude / privacidade como foco principal ----------

    if re.search(r'fraud detect(ion)?', t):
        return 'EXCLUIR', 'CE-4', 'Detecção de fraude como foco principal'

    if re.search(r'privacy.preserving|privacy preserving', t) and not re.search(r'\blend\b|\bloan\b|\bborrow', t):
        return 'EXCLUIR', 'CE-4', 'Privacy-preserving sem sistema de lending'

    if re.search(r'money laundering|anti.money|\baml\b', t):
        return 'EXCLUIR', 'CE-4', 'Anti-lavagem de dinheiro (fora do escopo)'

    # ---------- CE-5: infraestrutura blockchain genérica ----------

    if re.search(r'consensus algorithm|consensus mechanism|raft consensus|byzantine', t):
        return 'EXCLUIR', 'CE-5', 'Algoritmo de consenso (infraestrutura genérica)'

    if re.search(r'\biot\b|internet of things', t) and not re.search(r'\blend\b|\bloan\b|\bborrow\b|defi', t):
        return 'EXCLUIR', 'CE-5', 'IoT + blockchain (sem lending)'

    if re.search(r'supply chain', t) and not re.search(r'sme|small.and.medium|small business|\blend\b|\bloan\b', t):
        return 'EXCLUIR', 'CE-5', 'Supply chain blockchain (sem lending/SME)'

    if re.search(r'electronic medical|medical record|\bemr\b|healthcare|health record', t):
        return 'EXCLUIR', 'CE-5', 'Blockchain médico (fora do escopo)'

    if re.search(r'agricultural|agriculture', t) and not re.search(r'\blend\b|\bloan\b|sme|small', t):
        return 'EXCLUIR', 'CE-5', 'Blockchain agrícola sem lending'

    if re.search(r'energy trading|smart grid|renewable energy', t):
        return 'EXCLUIR', 'CE-5', 'Energia / smart grid (fora do escopo)'

    if re.search(r'data sharing|data privacy|data marketplace', t) and not re.search(r'\blend\b|\bloan\b|defi', t):
        return 'EXCLUIR', 'CE-5', 'Compartilhamento de dados sem lending'

    # ---------- sinais de INCLUSÃO ----------

    if re.search(r'defi|decentralized finance', t) and re.search(r'\blend\b|\bloan\b|\bborrow\b|credit', t):
        return 'INCLUIR', 'CI-1', 'DeFi + lending/loan/credit no título'

    if re.search(r'smart contract', t) and re.search(r'\blend\b|\bloan\b|\bborrow\b', t):
        return 'INCLUIR', 'CI-1', 'Smart contract + lending no título'

    if re.search(r'defi|decentralized finance', t) and re.search(r'protocol|platform|pool|vault|liquidat', t):
        return 'INCLUIR', 'CI-1', 'Protocolo DeFi com dinâmica de lending'

    # ---------- incerto: manter para revisão humana ----------
    return 'REVISAR', '', ''


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 triagem_manual.py <entrada.csv> <saida.csv>")
        sys.exit(1)

    entrada = sys.argv[1]
    saida   = sys.argv[2]

    with open(entrada, 'r', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))

    fieldnames = list(rows[0].keys())
    contadores = {'INCLUIR': 0, 'EXCLUIR': 0, 'REVISAR': 0}

    for row in rows:
        if row['triagem_t1'] == 'REVISAR':
            triagem, criterio, notas = classificar_completo(row['titulo'], row['resumo'])
            row['triagem_t1'] = triagem
            if criterio:
                row['criterio'] = criterio
            if notas:
                row['notas']    = notas
        contadores[row['triagem_t1']] += 1

    with open(saida, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    print(f"Total:                    {total}")
    print(f"  INCLUIR:                {contadores['INCLUIR']}")
    print(f"  EXCLUIR:                {contadores['EXCLUIR']}")
    print(f"  REVISAR (manual):       {contadores['REVISAR']}")
    print(f"\nArquivo gerado: {saida}")


if __name__ == '__main__':
    main()
