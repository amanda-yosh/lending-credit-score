#!/usr/bin/env python3
"""
Gera CSV de triagem a partir de export BibTeX do Scopus.
Aplica pré-classificação automática por título (primeira passagem).

Uso: python3 gerar_triagem.py <arquivo.bib> <saida.csv>
"""

import re
import csv
import sys


def extract_field(entry_text, field):
    """Extrai valor de um campo BibTeX respeitando chaves aninhadas."""
    pattern = rf'^\t{re.escape(field)}\s*=\s*\{{'
    m = re.search(pattern, entry_text, re.IGNORECASE | re.MULTILINE)
    if not m:
        return ''
    start = m.end() - 1
    depth = 0
    i = start
    while i < len(entry_text):
        if entry_text[i] == '{':
            depth += 1
        elif entry_text[i] == '}':
            depth -= 1
            if depth == 0:
                value = entry_text[start + 1:i]
                return re.sub(r'\s+', ' ', value).strip()
        i += 1
    return ''


def classificar(title):
    """
    Pré-classificação automática por título.
    Retorna (triagem_t1, criterio, notas).
    Conservadora: só exclui o que é inequivocamente fora do escopo.
    """
    t = title.lower()

    # CE-1 — Carbon credit
    if re.search(r'carbon[ -]credit|carbon offset|carbon[ -]neutral', t):
        return 'EXCLUIR', 'CE-1', 'Carbon credit (não crédito financeiro)'

    # CE-1 — Crédito acadêmico / escolar
    if re.search(r'(university|academic|school)\s+credit', t):
        return 'EXCLUIR', 'CE-1', 'Crédito acadêmico'
    if re.search(r'credit\s+(transfer|bank).{0,30}(school|universit|learn|educat)', t):
        return 'EXCLUIR', 'CE-1', 'Crédito acadêmico (bank/transfer)'
    if re.search(r'(school|universit|learn|educat).{0,30}credit\s+(transfer|bank)', t):
        return 'EXCLUIR', 'CE-1', 'Crédito acadêmico (bank/transfer)'

    # CE-1 — Letter of Credit (comércio exterior)
    if re.search(r'letter[ -]of[ -]credit', t):
        return 'EXCLUIR', 'CE-1', 'Letter of Credit (comércio exterior)'

    # CE-1 — Credit card (detecção de fraude, não lending)
    if re.search(r'credit card', t):
        return 'EXCLUIR', 'CE-1', 'Credit card (fraude, não lending protocol)'

    # CE-5 — Blockchain médico (EMR, saúde)
    if re.search(r'\bemr\b|electronic medical record|electronic health record', t):
        return 'EXCLUIR', 'CE-5', 'Blockchain médico (fora do escopo)'

    # CE-5 — Cadeia agrícola
    if re.search(r'agricultural quality|agriculture.*credit|carbon.*agricultur', t):
        return 'EXCLUIR', 'CE-5', 'Crédito agrícola / supply chain agrícola'

    return 'REVISAR', '', ''


def parse_bibtex(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    entries = []
    parts = re.split(r'\n(?=@)', content)

    for part in parts:
        part = part.strip()
        if not part or not part.startswith('@'):
            continue

        m = re.match(r'@(\w+)\{([^,]+),', part)
        if not m:
            continue

        entry_type = m.group(1).upper()
        key = m.group(2).strip()

        title   = extract_field(part, 'title')
        author  = extract_field(part, 'author')
        year    = extract_field(part, 'year')
        journal = extract_field(part, 'journal')

        # Primeiro autor (sobrenome)
        primeiro_autor = ''
        if author:
            primeiro_autor = author.split(',')[0].strip()

        resumo = extract_field(part, 'abstract')

        triagem, criterio, notas = classificar(title)

        entries.append({
            'id':             key,
            'titulo':         title,
            'primeiro_autor': primeiro_autor,
            'ano':            year,
            'tipo':           entry_type,
            'periodico':      journal,
            'qualis':         '',
            'resumo':         resumo,
            'triagem_t1':     triagem,
            'criterio':       criterio,
            'notas':          notas,
        })

    return entries


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 gerar_triagem.py <arquivo.bib> <saida.csv>")
        sys.exit(1)

    bib_path = sys.argv[1]
    csv_path = sys.argv[2]

    entries = parse_bibtex(bib_path)

    fieldnames = ['id', 'titulo', 'primeiro_autor', 'ano', 'tipo',
                  'periodico', 'qualis', 'resumo', 'triagem_t1', 'criterio', 'notas']

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(entries)

    excluir = sum(1 for e in entries if e['triagem_t1'] == 'EXCLUIR')
    revisar = sum(1 for e in entries if e['triagem_t1'] == 'REVISAR')

    print(f"Total de entradas:         {len(entries)}")
    print(f"  EXCLUIR (automático):    {excluir}")
    print(f"  REVISAR (triagem manual): {revisar}")
    print(f"\nArquivo gerado: {csv_path}")


if __name__ == '__main__':
    main()
