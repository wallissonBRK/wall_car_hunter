import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import time
import urllib3
from datetime import datetime, timedelta

# services
from services.fipe_service import obter_valor_fipe
from services.telegram_service import enviar_telegram
from services.supabase_service import SupabaseService as DatabaseService

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CONFIGURAÇÕES - Otimizado para GitHub Actions
VEICULOS_POPULARES = [
    {"nome": "HB20", "query": "hb20", "ano_de": 2015, "preco_ate": 60000},
    {"nome": "Onix", "query": "onix", "ano_de": 2015, "preco_ate": 60000},
    {"nome": "Corolla", "query": "corolla", "ano_de": 2014, "preco_ate": 90000},
    {"nome": "Etios", "query": "etios", "ano_de": 2016, "preco_ate": 65000},
    {"nome": "Civic", "query": "civic", "ano_de": 2014, "preco_ate": 85000},
]

# Limites para reduzir consumo
MAX_RESULTADOS_POR_BUSCA = 15
ENVIAR_TELEGRAM = False  # Desabilitar por padrão
BUSCAR_FIPE_APENAS_NOVOS = True
TIMEOUT_REQUISICAO = 20

URL_BASE = "https://m.autocarro.com.br/autobusca/carros?q={query}&ano_de={ano_de}&preco_ate={preco_ate}&cambio=1&estado=43&sort=1"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

ARQUIVO_MEMORIA = "price_memory.json"


def carregar_memoria():
    if os.path.exists(ARQUIVO_MEMORIA):
        try:
            with open(ARQUIVO_MEMORIA, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def salvar_memoria(dados):
    with open(ARQUIVO_MEMORIA, 'w') as f:
        json.dump(dados, f, indent=4)


def limpar_preco(preco_str):
    try:
        limpo = preco_str.replace('R$', '').replace(
            '.', '').replace(',', '.').strip()
        return float(limpo)
    except:
        return 0.0


def buscar_veiculos(url, headers, db, memoria, nova_memoria):
    """Busca veículos de uma URL e processa os resultados"""
    msgs_para_enviar = []
    
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_REQUISICAO, verify=False)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"    ❌ Erro: {e}")
        return msgs_para_enviar

    soup = BeautifulSoup(response.content, 'html.parser')
    script_tag = soup.find('script', id='__NEXT_DATA__')

    if not script_tag:
        return msgs_para_enviar

    try:
        data_json = json.loads(script_tag.string)
        page_props = data_json.get('props', {}).get('pageProps', {})
        offers = page_props.get('offers', {})
        lista_bruta = offers.get('items', [])
        
        lista_bruta = lista_bruta[:MAX_RESULTADOS_POR_BUSCA]
        
        if not lista_bruta:
            return msgs_para_enviar

        for carro in lista_bruta:
            version = carro.get('version', '').upper()
            model = carro.get('model', '').upper()
            nome_completo = f"{model} {version}".strip()

            if 'SEDAN' in nome_completo:
                continue

            link = carro.get('link')
            car_id = str(carro.get('id', link))
            preco_visual = carro.get('priceCurrency', 'R$ 0')
            preco_float = limpar_preco(preco_visual)
            preco_antigo = memoria.get(car_id)

            # Determinar status
            if car_id not in memoria:
                status_aviso = "🆕 NOVO"
                nova_memoria[car_id] = preco_float
            elif preco_float != preco_antigo:
                diferenca = preco_float - preco_antigo
                status_aviso = "📉 BAIXOU" if diferenca < 0 else "📈 SUBIU"
                nova_memoria[car_id] = preco_float
            else:
                continue  # Ignorar preço mantido

            year_model = carro.get('yearModel')
            
            # Buscar FIPE
            fipe_info = None
            if BUSCAR_FIPE_APENAS_NOVOS:
                try:
                    fipe_info = obter_valor_fipe(model, version, year_model)
                except Exception:
                    pass

            fipe_text = None
            fipe_fonte = None
            marca = None
            modelo_fipe = None
            ano_fipe = None
            
            if fipe_info and isinstance(fipe_info, dict):
                fipe_text = fipe_info.get('valor')
                fipe_fonte = fipe_info.get('fonte')
                marca = fipe_info.get('marca')
                modelo_fipe = fipe_info.get('modelo_fipe')
                ano_fipe = fipe_info.get('ano_nome')

            msg = (
                f"{status_aviso} - {nome_completo}\n"
                f"💰 {preco_visual} | 📅 {year_model}\n"
                f"💸 FIPE: {fipe_text or 'N/D'}\n"
                f"🔗 {link}"
            )
            msgs_para_enviar.append(msg)

            # Salvar no BD
            dados_anuncio = {
                'car_id': car_id,
                'full_name': nome_completo,
                'price_display': preco_visual,
                'price_numeric': preco_float,
                'model_year': year_model,
                'fipe_value': fipe_text,
                'fipe_source': fipe_fonte,
                'brand': marca,
                'fipe_model': modelo_fipe,
                'fipe_year': ano_fipe,
                'city_name': 'Brasil',
                'listing_url': link,
                'status': status_aviso,
                'listing_date': datetime.now()
            }
            db.salvar_anuncio(dados_anuncio)

    except json.JSONDecodeError as e:
        print(f"    ❌ Erro JSON: {e}")
    except Exception as e:
        print(f"    ❌ Erro: {e}")
    
    return msgs_para_enviar


def main():
    print("\n" + "="*60)
    print("🚗 Autocarro - GitHub Actions (Otimizado)")
    print(f"📊 Veículos: {len(VEICULOS_POPULARES)}")
    print("="*60 + "\n")

    try:
        db = DatabaseService()
    except Exception as e:
        print(f"❌ Erro Supabase: {e}")
        return

    memoria = carregar_memoria()
    nova_memoria = memoria.copy()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    todas_msgs = []
    total_processados = 0

    for idx, veiculo in enumerate(VEICULOS_POPULARES, 1):
        print(f"  [{idx}/{len(VEICULOS_POPULARES)}] {veiculo['nome']:12}", end=" ")
        
        url = URL_BASE.format(
            query=veiculo['query'],
            ano_de=veiculo['ano_de'],
            preco_ate=veiculo['preco_ate']
        )
        
        msgs = buscar_veiculos(url, headers, db, memoria, nova_memoria)
        total_processados += len(msgs)
        todas_msgs.extend(msgs)
        
        status = f"✓ {len(msgs)} novidades" if msgs else "⚪ sem novidades"
        print(status)
        
        if idx < len(VEICULOS_POPULARES):
            time.sleep(1)

    salvar_memoria(nova_memoria)

    print("\n" + "="*60)
    print(f"✅ CONCLUÍDO: {total_processados} anúncios relevantes")
    print("="*60 + "\n")

    if ENVIAR_TELEGRAM and len(todas_msgs) > 0 and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        print(f"📤 Enviando {len(todas_msgs)} notificações...")
        
        fuso_brasil = datetime.now() - timedelta(hours=3)
        agora_formatada = fuso_brasil.strftime("%d/%m %H:%M")

        try:
            enviar_telegram(
                f"🏁 Relatório: {agora_formatada}\n✅ Total: {len(todas_msgs)} anúncios",
                TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
            )

            for m in todas_msgs:
                enviar_telegram(m, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
                time.sleep(0.5)
            
            print("✅ Notificações enviadas!\n")
        except Exception as e:
            print(f"⚠️ Erro ao enviar Telegram: {e}\n")


if __name__ == "__main__":
    main()
