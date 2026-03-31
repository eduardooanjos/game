# Sala de Apostas em Rede Local

Projeto em Python para a disciplina de **Redes de Computadores**.

## Como executar

1. Instale as dependencias:

```bash
pip install flask
```

2. Inicie o servidor:

```bash
python app.py
```
Se o comando `python` nao funcionar no seu computador, tente:

```bash
py app.py
```

## Como acessar pela rede local

Quando o servidor iniciar, abra no navegador:

```text
http://127.0.0.1:5000
```

## Fluxo do jogador

1. O jogador abre a pagina web.
2. Informa o nickname.
3. Se ainda nao existir, o cadastro e criado.
4. Se ja existir, o saldo e carregado.
5. O jogador entra na sala atual.
6. O servidor executa o sorteio da rodada.

## Regras da rodada

- cada jogador recebe um numero aleatorio de **1 a 10**
- quem tirar o maior valor ganha **100 moedas**
- quem perder, perde **50 moedas**
- em caso de empate no maior valor, todos os empatados vencem
- quem chegar a **0 moedas** e removido do sistema

## Observacoes importantes

- os dados ficam em memoria enquanto o servidor estiver ligado
- ao encerrar o servidor, os cadastros e saldos sao perdidos
- a logica do jogo fica toda no backend
- a interface web serve apenas para os jogadores entrarem e visualizarem a sala

## Estrutura principal

- `app.py`: servidor Flask com as rotas web, sala atual e controle da partida
- `jogador.py`: classe que representa cada jogador e seu saldo
- `rodada.py`: logica do sorteio e atualizacao dos saldos
- `templates/index.html`: pagina principal
- `static/styles.css`: estilo visual da interface
