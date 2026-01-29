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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CONFIGURAÇÕES
URL_BUSCA = "https://m.autocarro.com.br/autobusca/carros?q=etios%201.5&ano_de=2016&preco_ate=65000&cambio=1&estado=43&sort=1"

#TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_TOKEN = "8576961684:AAFC-iDF6_0O09NEnkXXYTnRDCJWY1k7ra8"
#TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
TELEGRAM_CHAT_ID = "7556703507"

ARQUIVO_MEMORIA = "price_memory.json"


# enviar_telegram moved to services/telegram_service.py


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


# Consulta FIPE usando a API pública (parallelum). Há cache em memória para
# reduzir o número de chamadas em uma mesma execução.
# obter_valor_fipe moved to services/fipe_service.py


def main():
    print("--- Iniciando Autocarro (Relatório Completo) ---")

    memoria = carregar_memoria()
    nova_memoria = memoria.copy()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'https://www.google.com/'
    }

    try:
        response = requests.get(
            URL_BUSCA, headers=headers, timeout=30, verify=False)
    except Exception as e:
        print(f"Erro fatal de conexão: {e}")
        sys.exit(1)

    soup = BeautifulSoup(response.content, 'html.parser')
    script_tag = soup.find('script', id='__NEXT_DATA__')

    if not script_tag:
        print("❌ ERRO: Tag __NEXT_DATA__ não encontrada.")
        sys.exit(1)

    try:
        data_json = json.loads(script_tag.string)
        page_props = data_json.get('props', {}).get('pageProps', {})

        mapa_cidades = {}
        try:
            lista_cidades = page_props['search']['filters']['data']['cidades']
            for c in lista_cidades:
                mapa_cidades[c['id_cid']] = c['ds_cid']
            print(f"Mapa de cidades carregado: {len(mapa_cidades)} cidades.")
        except KeyError:
            print("Aviso: Mapa de cidades indisponível.")

        offers = page_props.get('offers', {})
        lista_bruta = offers.get('items', [])

        msgs_para_enviar = []

        for carro in lista_bruta:
            version = carro.get('version', '').upper()
            model = carro.get('model', '').upper()
            nome_completo = f"{model} {version}"

            if 'SEDAN' in nome_completo:
                continue

            link = carro.get('link')
            car_id = str(carro.get('id', link))

            preco_visual = carro.get('priceCurrency', 'R$ 0')
            preco_float = limpar_preco(preco_visual)

            status_aviso = ""
            preco_antigo = memoria.get(car_id)

            if car_id not in memoria:
                status_aviso = "🆕 <b>NOVO ANÚNCIO!</b>"
                nova_memoria[car_id] = preco_float

            elif preco_float != preco_antigo:
                diferenca = preco_float - preco_antigo
                if diferenca < 0:
                    status_aviso = f"📉 <b>BAIXOU!</b> (Era R$ {preco_antigo:,.0f})"
                else:
                    status_aviso = f"📈 <b>SUBIU!</b> (Era R$ {preco_antigo:,.0f})"

                nova_memoria[car_id] = preco_float

            else:
                status_aviso = "⚪ Preço Mantido"

            city_id = carro.get('cityId')
            city_name = mapa_cidades.get(city_id, str(city_id))
            year_model = carro.get('yearModel')

            print(f"-> Preparando envio: {status_aviso} - {nome_completo}")
            # Busca valor FIPE (pode demorar um pouco na primeira execução)
            try:
                fipe_info = obter_valor_fipe(model, version, year_model)
            except Exception:
                fipe_info = None

            # imprimir no console a fonte encontrada para facilitar debug
            if fipe_info and isinstance(fipe_info, dict):
                print(f"   -> FIPE encontrado: {fipe_info.get('valor')} | fonte: {fipe_info.get('fonte')} | marca: {fipe_info.get('marca')} | modelo FIPE: {fipe_info.get('modelo_fipe')} | ano: {fipe_info.get('ano_nome')}")
                fipe_text = f"{fipe_info.get('valor')}"
                fipe_fonte = fipe_info.get('fonte')
            else:
                print("   -> FIPE: N/D")
                fipe_text = None
                fipe_fonte = None

            msg = (
                f"{status_aviso}\n"
                f"🚗 <b>{nome_completo}</b>\n"
                f"💰 {preco_visual} | 📅 {year_model}\n"
                f"💸 FIPE: {fipe_text or 'N/D'}\n"
                f"📍 Local: {city_name}\n"
                f"🔗 <a href='{link}'>Ver Anúncio</a>"
            )
            # se há fonte FIPE, adicionar ao final da mensagem (opcional)
            if fipe_fonte:
                msg = msg + f"\n🔗 Fonte FIPE: {fipe_fonte}"
            msgs_para_enviar.append(msg)

        print(
            f"Bruto: {len(lista_bruta)} | Para Enviar: {len(msgs_para_enviar)}")

        if len(msgs_para_enviar) > 0:
            fuso_brasil = datetime.now() - timedelta(hours=3)
            agora_formatada = fuso_brasil.strftime("%d/%m %H:%M")

            enviar_telegram(
                f"🏁 <b>Relatório Diário:</b> {agora_formatada}\n{'━'*50}", TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

            for m in msgs_para_enviar:
                enviar_telegram(m, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
                time.sleep(1)

            salvar_memoria(nova_memoria)
            print("Memória de preços atualizada com sucesso.")
        else:
            print("Nenhum carro encontrado nos filtros.")

    except Exception as e:
        print(f"❌ Erro ao processar JSON: {e}")


if __name__ == "__main__":
    main()
