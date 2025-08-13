# robobtcv1
Robo Cripto em Ptyhon - Compra e Venda Simples ( Binance )

Estrutura da Lógica :

    VALOR_USDT = Decimal(input("💵 Valor em USDT para comprar: ")) Aqui voce deve inserir a compra em USDT, sempre em USDT
    LUCRO_PCT = Decimal(input("📈 % de lucro desejado: "))  Aqui voce consegue inserir o lucro que deseja ter 
    STOP_LOSS = Decimal(input("📉 % de stop loss: ")) Aqui voce pode colocar um stop loos, ou seja, se pelo menos tiver a porcentagem inserida aqui ele vende para dar lucro, e nao ter percas severas
    INTERVALO = float(input("⏲️ Intervalo entre operações (min): ")) * 60  ( Aqui voce deve inserir o intervalo para ele ficar monitirando o mercado, EX: 0,30 quer dizer: 30 minutos, o recomendado é a cada 04 horas )


# - Comandos do Telegram: /pausar, /retomar, /status, /relatorio
# - Registro de histórico de compras, vendas, lucros em USD
# - Entrada de configurações pelo menu
# - Exibição de saldos BTC e USDT
# - O robo contem um Log em txt , 
Para iniciar o robo, apenas acesse o diretorio dele via CMD, e digite python main.py  ou pode compilar um .exe desejado

Código Open Source - Usem a vontade .
