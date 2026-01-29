#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste para verificar a conexão com o Supabase
"""

from services.supabase_service import SupabaseService
from datetime import datetime


def testar_conexao():
    """Testa a conexão básica com o Supabase"""
    print("=" * 60)
    print("🧪 TESTANDO CONEXÃO COM SUPABASE")
    print("=" * 60)
    
    try:
        db = SupabaseService()
        if db.verificar_conexao():
            print("✅ Conexão estabelecida com sucesso!\n")
            return db
        else:
            print("❌ Falha na conexão\n")
            return None
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}\n")
        return None


def testar_insercao(db):
    """Testa a inserção de um registro de teste"""
    print("=" * 60)
    print("🧪 TESTANDO INSERÇÃO DE DADOS")
    print("=" * 60)
    
    dados_teste = {
        'car_id': 'TEST_' + datetime.now().strftime('%Y%m%d_%H%M%S'),
        'full_name': 'TOYOTA ETIOS 1.5 XS TESTE',
        'price_display': 'R$ 45.000',
        'price_numeric': 45000.00,
        'model_year': '2020',
        'fipe_value': 'R$ 48.500',
        'fipe_source': 'https://veiculos.fipe.org.br',
        'brand': 'TOYOTA',
        'fipe_model': 'ETIOS 1.5 XS',
        'fipe_year': '2020',
        'city_name': 'Porto Alegre',
        'listing_url': 'https://exemplo.com/teste',
        'status': '🧪 TESTE',
        'listing_date': datetime.now()
    }
    
    try:
        resultado = db.salvar_anuncio(dados_teste)
        if resultado:
            print("✅ Dados inseridos com sucesso!\n")
            return dados_teste['car_id']
        else:
            print("⚠️ Inserção retornou False (pode ser duplicata)\n")
            return None
    except Exception as e:
        print(f"❌ Erro ao inserir: {e}\n")
        return None


def testar_consultas(db, car_id=None):
    """Testa as consultas no banco"""
    print("=" * 60)
    print("🧪 TESTANDO CONSULTAS")
    print("=" * 60)
    
    # Teste 1: Listar anúncios recentes
    print("📋 Listando últimos 5 anúncios...")
    try:
        anuncios = db.listar_anuncios_recentes(limite=5)
        print(f"   Encontrados: {len(anuncios)} anúncios")
        if anuncios:
            for i, anuncio in enumerate(anuncios[:3], 1):
                print(f"   {i}. {anuncio[1]} - {anuncio[2]}")
        print()
    except Exception as e:
        print(f"   ❌ Erro: {e}\n")
    
    # Teste 2: Estatísticas
    print("📊 Obtendo estatísticas...")
    try:
        stats = db.obter_estatisticas()
        print(f"   Total de anúncios únicos: {stats['total_anuncios']}")
        print(f"   Total de registros: {stats['total_registros']}")
        print(f"   Preço médio: R$ {stats['preco_medio']:,.2f}")
        print(f"   Preço mínimo: R$ {stats['preco_minimo']:,.2f}")
        print(f"   Preço máximo: R$ {stats['preco_maximo']:,.2f}")
        print()
    except Exception as e:
        print(f"   ❌ Erro: {e}\n")
    
    # Teste 3: Histórico de preço (se temos um car_id)
    if car_id:
        print(f"📈 Obtendo histórico do anúncio {car_id}...")
        try:
            historico = db.obter_historico_preco(car_id, limite=5)
            print(f"   Registros encontrados: {len(historico)}")
            for registro in historico:
                print(f"   - {registro[0]}: R$ {registro[1]} ({registro[2]})")
            print()
        except Exception as e:
            print(f"   ❌ Erro: {e}\n")


def main():
    """Função principal de teste"""
    print("\n🚀 Iniciando testes do Supabase...\n")
    
    # Teste 1: Conexão
    db = testar_conexao()
    if not db:
        print("❌ Não foi possível estabelecer conexão. Verifique:")
        print("   1. O arquivo .env existe?")
        print("   2. SUPABASE_URL e SUPABASE_KEY estão corretos?")
        print("   3. A tabela 'listings' foi criada no Supabase?")
        return
    
    # Teste 2: Inserção
    car_id = testar_insercao(db)
    
    # Teste 3: Consultas
    testar_consultas(db, car_id)
    
    print("=" * 60)
    print("✅ TESTES CONCLUÍDOS!")
    print("=" * 60)
    print("\n💡 Dica: Acesse o Supabase Table Editor para visualizar os dados")
    print("   https://app.supabase.com → Table Editor → listings\n")


if __name__ == "__main__":
    main()
