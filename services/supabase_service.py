from supabase import create_client, Client
from datetime import datetime
import os
from dotenv import load_dotenv
from pathlib import Path

# Carregar variáveis de ambiente (prioriza .env.staging)
_root = Path(__file__).resolve().parents[1]
load_dotenv(_root / ".env.staging")
load_dotenv(_root / ".env")


class SupabaseService:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError(
                "❌ SUPABASE_URL e SUPABASE_KEY devem estar definidas no arquivo .env.staging ou .env"
            )
        
        self.client: Client = create_client(url, key)
        print("✓ Cliente Supabase inicializado com sucesso.")

    def salvar_anuncio(self, dados):
        try:
            registro = {
                'car_id': dados.get('car_id'),
                'full_name': dados.get('full_name'),
                'price_display': dados.get('price_display'),
                'price_numeric': dados.get('price_numeric'),
                'model_year': dados.get('model_year'),
                'fipe_value': dados.get('fipe_value'),
                'fipe_source': dados.get('fipe_source'),
                'brand': dados.get('brand'),
                'fipe_model': dados.get('fipe_model'),
                'fipe_year': dados.get('fipe_year'),
                'city_name': dados.get('city_name'),
                'listing_url': dados.get('listing_url'),
                'status': dados.get('status'),
                'listing_date': dados.get('listing_date', datetime.now()).isoformat()
            }
            
            response = self.client.table('listings').insert(registro).execute()
            
            print(f"✓ Anúncio {dados.get('car_id')} salvo no Supabase.")
            return True
            
        except Exception as e:
            if 'duplicate key' in str(e).lower():
                print(f"⚠ Anúncio {dados.get('car_id')} já existe no banco.")
                return False
            else:
                print(f"❌ Erro ao salvar anúncio no Supabase: {e}")
                return False

    def obter_historico_preco(self, car_id, limite=10):
        try:
            response = (
                self.client.table('listings')
                .select('created_at, price_numeric, status')
                .eq('car_id', car_id)
                .order('created_at', desc=True)
                .limit(limite)
                .execute()
            )
            
            resultados = [
                (item['created_at'], item['price_numeric'], item['status'])
                for item in response.data
            ]
            
            return resultados
            
        except Exception as e:
            print(f"❌ Erro ao obter histórico: {e}")
            return []

    def obter_estatisticas(self):
        try:
            response = (
                self.client.table('listings')
                .select('car_id, price_numeric')
                .execute()
            )
            
            dados = response.data
            
            if not dados:
                return {
                    'total_anuncios': 0,
                    'total_registros': 0,
                    'preco_medio': 0,
                    'preco_minimo': 0,
                    'preco_maximo': 0
                }
            
            car_ids_unicos = set(item['car_id'] for item in dados)
            precos = [item['price_numeric'] for item in dados if item['price_numeric']]
            
            return {
                'total_anuncios': len(car_ids_unicos),
                'total_registros': len(dados),
                'preco_medio': sum(precos) / len(precos) if precos else 0,
                'preco_minimo': min(precos) if precos else 0,
                'preco_maximo': max(precos) if precos else 0
            }
            
        except Exception as e:
            print(f"❌ Erro ao obter estatísticas: {e}")
            return {
                'total_anuncios': 0,
                'total_registros': 0,
                'preco_medio': 0,
                'preco_minimo': 0,
                'preco_maximo': 0
            }

    def listar_anuncios_recentes(self, limite=20):
        try:
            response = (
                self.client.table('listings')
                .select('car_id, full_name, price_display, city_name, status, created_at')
                .order('created_at', desc=True)
                .limit(limite)
                .execute()
            )
            
            resultados = [
                (
                    item['car_id'],
                    item['full_name'],
                    item['price_display'],
                    item['city_name'],
                    item['status'],
                    item['created_at']
                )
                for item in response.data
            ]
            
            return resultados
            
        except Exception as e:
            print(f"❌ Erro ao listar anúncios: {e}")
            return []

    def verificar_conexao(self):
        try:
            response = self.client.table('listings').select('id').limit(1).execute()
            print("✓ Conexão com Supabase verificada com sucesso.")
            return True
        except Exception as e:
            print(f"❌ Erro na conexão com Supabase: {e}")
            return False
