# O novo código será estruturado com:
# - Comandos do Telegram: /pausar, /retomar, /status, /relatorio
# - Registro de histórico de compras, vendas, lucros em USD
# - Entrada de configurações pelo menu
# - Exibição de saldos BTC e USDT

import os
import time
import logging
import threading
from datetime import datetime
from decimal import Decimal, getcontext, ROUND_DOWN
from binance.client import Client
from dotenv import load_dotenv
import requests
import json
import socket

getcontext().prec = 16

# === CONFIG ===
load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
client = Client(api_key, api_secret)

TELEGRAM_TOKEN = 'INSIRASEUTELEGRANTOKEN'
TELEGRAM_CHAT_ID = 'INSIRASEUCHATIDDOTELEGRAN'
PAUSE_FLAG = False
HISTORICO = []
INICIO = time.time()

VALOR_USDT = Decimal('5')
LUCRO_PCT = Decimal('10')
STOP_LOSS = Decimal('3')
INTERVALO = 1800
ULTIMO_PRECO_COMPRA = None

# === TELEGRAM ===
def enviar_telegram(mensagem):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': mensagem,
        'parse_mode': 'HTML'
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ Erro ao enviar Telegram: {e}")

def obter_ip():
    try:
        return requests.get('https://api.ipify.org').text
    except:
        return 'Desconhecido'

def verificar_comandos():
    global PAUSE_FLAG
    offset = None
    while True:
        try:
            url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates'
            if offset:
                url += f'?offset={offset}'
            response = requests.get(url).json()
            for update in response.get('result', []):
                offset = update['update_id'] + 1
                msg = update['message']['text'].lower()
                if msg == '/pausar':
                    PAUSE_FLAG = True
                    enviar_telegram("⏸️ <b>Robô pausado!</b>")
                elif msg == '/retomar':
                    PAUSE_FLAG = False
                    enviar_telegram("▶️ <b>Robô retomado!</b>")
                elif msg == '/status':
                    uptime = int(time.time() - INICIO)
                    enviar_telegram(f"📡 <b>Status:</b> {'Pausado' if PAUSE_FLAG else 'Ativo'}\nIP: {obter_ip()}\nUptime: {uptime // 60} min")
                elif msg == '/relatorio':
                    compras = sum(op['valor'] for op in HISTORICO if op['tipo'] == 'compra')
                    vendas = sum(op['valor'] for op in HISTORICO if op['tipo'] == 'venda')
                    lucro = vendas - compras
                    enviar_telegram(f"📊 <b>Relatório:</b>\nCompras: ${compras:.2f}\nVendas: ${vendas:.2f}\nLucro: ${lucro:.2f}")
        except Exception as e:
            logging.warning(f"Erro ao verificar comandos Telegram: {e}")
        time.sleep(5)

# === LOGS ===
logging.basicConfig(filename='trade_bot.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# === FUNÇÕES ===
def arredondar_quantidade(qtd, step_size):
    step = Decimal(step_size)
    return (qtd // step) * step

def mostrar_saldo(asset='USDT'):
    try:
        conta = client.get_asset_balance(asset=asset)
        saldo = Decimal(conta['free'])
        return saldo
    except:
        return Decimal('0')

def obter_infos_symbol(symbol='BTCUSDT'):
    info = client.get_symbol_info(symbol)
    step_size = Decimal('0.00000001')
    min_qty = Decimal('0.00000001')
    min_notional = Decimal('10')
    for f in info['filters']:
        if f['filterType'] == 'LOT_SIZE':
            step_size = Decimal(f['stepSize'])
            min_qty = Decimal(f['minQty'])
        if f['filterType'] == 'MIN_NOTIONAL':
            min_notional = Decimal(f['minNotional'])
    return step_size, min_qty, min_notional

def comprar(usdt_amount, step_size, min_qty):
    global ULTIMO_PRECO_COMPRA
    price = Decimal(client.get_symbol_ticker(symbol='BTCUSDT')['price'])
    quantidade = arredondar_quantidade(usdt_amount / price, step_size)
    if quantidade < min_qty:
        print("⚠️ Quantidade calculada abaixo do mínimo para compra.")
        return None, None
    try:
        ordem = client.order_market_buy(symbol='BTCUSDT', quantity=str(quantidade))
        preco_exec = sum(Decimal(fill['price']) * Decimal(fill['qty']) for fill in ordem['fills']) / sum(Decimal(fill['qty']) for fill in ordem['fills'])
        preco_exec = preco_exec.quantize(Decimal('0.01'))
        ULTIMO_PRECO_COMPRA = preco_exec
        enviar_telegram(f"🟢 Compra: {quantidade} BTC a {preco_exec:.2f} USDT")
        HISTORICO.append({'tipo': 'compra', 'valor': float(preco_exec * quantidade), 'hora': str(datetime.now())})
        return quantidade, preco_exec
    except Exception as e:
        print(f"❌ Erro na compra: {e}")
        enviar_telegram(f"❌ Erro ao comprar: {e}")
        return None, None

def vender(quantidade, preco_alvo):
    global PAUSE_FLAG
    step_size, min_qty, _ = obter_infos_symbol('BTCUSDT')
    quantidade = arredondar_quantidade(quantidade, step_size)
    if quantidade < min_qty:
        print(f"⚠️ Quantidade {quantidade} menor que o mínimo permitido {min_qty}. Venda cancelada.")
        enviar_telegram(f"⚠️ Quantidade de venda ({quantidade}) menor que o mínimo permitido.")
        return
    while True:
        if PAUSE_FLAG:
            print("⏸️ Pausado. Aguardando retomada...")
            time.sleep(10)
            continue
        preco_atual = Decimal(client.get_symbol_ticker(symbol='BTCUSDT')['price'])
        print(f"📈 Preço atual: {preco_atual} | 🎯 Meta: {preco_alvo}", end='\r')
        if preco_atual >= preco_alvo or preco_atual <= ULTIMO_PRECO_COMPRA * (1 - STOP_LOSS / 100):
            try:
                ordem = client.order_market_sell(symbol='BTCUSDT', quantity=str(quantidade))
                preco_exec = sum(Decimal(fill['price']) * Decimal(fill['qty']) for fill in ordem['fills']) / sum(Decimal(fill['qty']) for fill in ordem['fills'])
                preco_exec = preco_exec.quantize(Decimal('0.01'))
                HISTORICO.append({'tipo': 'venda', 'valor': float(preco_exec * quantidade), 'hora': str(datetime.now())})
                print(f"\n✅ Venda realizada: {quantidade} BTC a {preco_exec:.2f} USDT")
                enviar_telegram(f"🔴 Venda: {quantidade} BTC a {preco_exec:.2f} USDT")
                return
            except Exception as e:
                print(f"❌ Erro na venda: {e}")
                enviar_telegram(f"❌ Erro ao vender: {e}")
                return
        time.sleep(15)

# === MAIN ===
def main():
    global VALOR_USDT, LUCRO_PCT, STOP_LOSS, INTERVALO
    VALOR_USDT = Decimal(input("💵 Valor em USDT para comprar: "))
    LUCRO_PCT = Decimal(input("📈 % de lucro desejado: "))
    STOP_LOSS = Decimal(input("📉 % de stop loss: "))
    INTERVALO = float(input("⏲️ Intervalo entre operações (min): ")) * 60

    step_size, min_qty, _ = obter_infos_symbol('BTCUSDT')

    threading.Thread(target=verificar_comandos, daemon=True).start()
    enviar_telegram("🤖 Robô iniciado. Use /pausar, /retomar, /status e /relatorio.")

    while True:
        if PAUSE_FLAG:
            print("⏸️ Robô pausado...")
            time.sleep(10)
            continue

        saldo_btc = mostrar_saldo('BTC')
        saldo_usdt = mostrar_saldo('USDT')

        ticker = Decimal(client.get_symbol_ticker(symbol='BTCUSDT')['price'])
        necessario = arredondar_quantidade(VALOR_USDT / ticker, step_size)

        if saldo_btc >= necessario:
            alvo = ULTIMO_PRECO_COMPRA * (1 + LUCRO_PCT / 100)
            print(f"💹 Preço atual: {ticker} | 🎯 Meta de venda: {alvo}")
            vender(saldo_btc, alvo)
        elif saldo_usdt >= VALOR_USDT:
            qtd, preco = comprar(VALOR_USDT, step_size, min_qty)
            if qtd:
                alvo = preco * (1 + LUCRO_PCT / 100)
                print(f"💹 Compra feita. 🎯 Meta de venda: {alvo}")
                vender(qtd, alvo)
        else:
            print(f"⚠️ Saldo insuficiente. BTC: {saldo_btc:.8f} | USDT: {saldo_usdt:.2f}")
            enviar_telegram("⚠️ Saldo insuficiente para operar.")

        print(f"⏳ Aguardando {INTERVALO / 60:.1f} min para nova operação...\n")
        time.sleep(INTERVALO)

if __name__ == "__main__":
    main()
