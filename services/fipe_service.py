import requests
import difflib
import unicodedata
import re

import requests
import difflib
import unicodedata
import re

# Cache em memória para a execução atual
_fipe_cache = {
    'marcas': None,
    'modelos_por_marca': {}
}


def obter_valor_fipe(modelo, versao, ano_modelo):
    """
    Tenta obter o Valor FIPE para o veículo informado.
    modelo, versao: strings (ex: 'ETIOS', '1.5')
    ano_modelo: ano como inteiro ou string (ex: 2016)
    Retorna dict com 'valor' e 'fonte' e metadados, ou None se não encontrado.
    """
    try:
        # require at least a model name
        if not modelo:
            return None

        base = 'https://parallelum.com.br/fipe/api/v1/carros'

        def _norm(s):
            if not s:
                return ''
            s = unicodedata.normalize('NFKD', s)
            s = ''.join(c for c in s if not unicodedata.combining(c))
            s = re.sub(r'[^A-Z0-9 ]+', ' ', s.upper())
            return re.sub(r'\s+', ' ', s).strip()

        modelo_norm = _norm(modelo)
        versao_norm = _norm(versao)
        termo_norm = f"{modelo_norm} {versao_norm}".strip()
        ano_str = str(ano_modelo) if ano_modelo is not None else ''

        # carregar marcas (cache)
        if _fipe_cache['marcas'] is None:
            r = requests.get(f'{base}/marcas', timeout=10)
            r.raise_for_status()
            _fipe_cache['marcas'] = r.json()

        marcas = _fipe_cache['marcas'] or []

        max_requests = 120
        req_count = 0

        # 1) Procurar fortemente pelo modelo entre os modelos FIPE (varre marcas até achar)
        for marca in marcas:
            codigo_marca = marca.get('codigo')
            if codigo_marca is None:
                continue

            if codigo_marca not in _fipe_cache['modelos_por_marca']:
                if req_count >= max_requests:
                    break
                r = requests.get(f'{base}/marcas/{codigo_marca}/modelos', timeout=10)
                req_count += 1
                if r.status_code != 200:
                    _fipe_cache['modelos_por_marca'][codigo_marca] = []
                else:
                    _fipe_cache['modelos_por_marca'][codigo_marca] = r.json().get('modelos', [])

            modelos = _fipe_cache['modelos_por_marca'].get(codigo_marca, [])

            for modelo_fipe in modelos:
                nome_modelo_fipe = modelo_fipe.get('nome') or ''
                nome_norm = _norm(nome_modelo_fipe)

                if modelo_norm and (modelo_norm in nome_norm or nome_norm in modelo_norm):
                    codigo_modelo = modelo_fipe.get('codigo')
                    if not codigo_modelo:
                        continue

                    # obter anos disponíveis
                    if req_count >= max_requests:
                        break
                    r_anos = requests.get(f'{base}/marcas/{codigo_marca}/modelos/{codigo_modelo}/anos', timeout=10)
                    req_count += 1
                    if r_anos.status_code != 200:
                        continue
                    anos = r_anos.json()

                    for ano in anos:
                        nome_ano = ano.get('nome', '')
                        codigo_ano = ano.get('codigo')
                        if ano_str and ano_str in nome_ano:
                            fonte_url = f'{base}/marcas/{codigo_marca}/modelos/{codigo_modelo}/anos/{codigo_ano}'
                            if req_count >= max_requests:
                                break
                            r_val = requests.get(fonte_url, timeout=10)
                            req_count += 1
                            if r_val.status_code == 200:
                                detalhe = r_val.json()
                                return {
                                    'valor': detalhe.get('Valor'),
                                    'fonte': fonte_url,
                                    'marca': marca.get('nome'),
                                    'modelo_fipe': modelo_fipe.get('nome'),
                                    'ano_nome': nome_ano,
                                }

        # 2) Fallback: heurística mais ampla (mantida para casos onde modelo não bate exatamente)
        lista_nomes_marcas = [m.get('nome', '').upper() for m in marcas if m.get('nome')]
        candidatos = []
        termo_upper = termo_norm.upper()
        for m in marcas:
            nome_m = (m.get('nome') or '').upper()
            if not nome_m:
                continue
            if nome_m in termo_upper or any(token in nome_m for token in termo_upper.split() if len(token) > 2):
                candidatos.append(m)

        if not candidatos:
            modelos_possiveis = difflib.get_close_matches(termo_upper.split()[0] if termo_upper else '', lista_nomes_marcas, n=5, cutoff=0.6)
            if modelos_possiveis:
                for nm in modelos_possiveis:
                    for m in marcas:
                        if (m.get('nome') or '').upper() == nm:
                            candidatos.append(m)

        if not candidatos:
            candidatos = marcas[:10]

        for marca in candidatos:
            codigo_marca = marca.get('codigo')
            if codigo_marca is None:
                continue
            if codigo_marca not in _fipe_cache['modelos_por_marca']:
                if req_count >= max_requests:
                    break
                r = requests.get(f'{base}/marcas/{codigo_marca}/modelos', timeout=10)
                req_count += 1
                if r.status_code != 200:
                    _fipe_cache['modelos_por_marca'][codigo_marca] = []
                else:
                    _fipe_cache['modelos_por_marca'][codigo_marca] = r.json().get('modelos', [])

            modelos = _fipe_cache['modelos_por_marca'].get(codigo_marca, [])
            for modelo_fipe in modelos:
                nome_modelo_fipe = (modelo_fipe.get('nome') or '').upper()
                if not nome_modelo_fipe:
                    continue
                if termo_upper.strip():
                    termo_tokens = [t for t in termo_upper.split() if len(t) > 1]
                    if not any(tok in nome_modelo_fipe for tok in termo_tokens):
                        continue

                codigo_modelo = modelo_fipe.get('codigo')
                if not codigo_modelo:
                    continue
                if req_count >= max_requests:
                    break
                r_anos = requests.get(f'{base}/marcas/{codigo_marca}/modelos/{codigo_modelo}/anos', timeout=10)
                req_count += 1
                if r_anos.status_code != 200:
                    continue
                anos = r_anos.json()
                for ano in anos:
                    nome_ano = ano.get('nome', '')
                    codigo_ano = ano.get('codigo')
                    if ano_str and ano_str in nome_ano:
                        fonte_url = f'{base}/marcas/{codigo_marca}/modelos/{codigo_modelo}/anos/{codigo_ano}'
                        if req_count >= max_requests:
                            break
                        r_val = requests.get(fonte_url, timeout=10)
                        req_count += 1
                        if r_val.status_code == 200:
                            detalhe = r_val.json()
                            return {
                                'valor': detalhe.get('Valor'),
                                'fonte': fonte_url,
                                'marca': marca.get('nome'),
                                'modelo_fipe': modelo_fipe.get('nome'),
                                'ano_nome': nome_ano,
                            }

        return None
    except Exception:
        return None
