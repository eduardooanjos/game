# Jogo de Rodadas em Python

Projeto simples em Python desenvolvido para a disciplina de **Redes de Computadores**.

O programa simula salas com jogadores, sorteia um valor para cada participante e atualiza o saldo de moedas a cada rodada.

## Como executar

Abra o terminal na pasta do projeto e rode:

```bash
python main.py
```

Se o comando `python` nao funcionar no seu computador, tente:

```bash
py main.py
```

## Como usar

Ao iniciar o programa, ele perguntara:

```text
Abrir nova sala? (s/n)
```

Digite:

- `s` para abrir uma nova sala
- `n` para encerrar o programa

Depois disso, o sistema pedira os nicknames dos jogadores:

```text
Nickname do jogador 1:
Nickname do jogador 2:
...
```

## Regras da entrada de jogadores

- Cada sala aceita ate **4 jogadores**.
- Sao necessarios pelo menos **2 jogadores** para a rodada acontecer.
- Se um jogador ja existir no sistema, ele entra com o saldo que ja possuia.
- Se o nickname ainda nao existir, o jogador sera criado com **100 moedas**.
- Se nao quiser mais adicionar jogadores na sala, basta **pressionar Enter com o nome em branco**.

## Como funciona a rodada

- Cada jogador recebe um numero aleatorio de **1 a 10**.
- Quem tirar o maior valor ganha **100 moedas**.
- Quem perder, perde **50 moedas**.
- Se houver empate no maior valor, todos os empatados vencem a rodada.

## Eliminacao de jogador

Quando o saldo de um jogador chegar a **0 moedas**, o sistema exibira uma mensagem informando a derrota e a conta sera excluida do cadastro.

Exemplo:

```text
Jogador Carlos perdeu, conta excluida!
```

## Observacoes importantes

- O cadastro dos jogadores fica armazenado apenas enquanto o programa estiver aberto.
- Ao fechar o programa, os dados sao perdidos, pois nao existe salvamento em arquivo ou banco de dados.
- O mesmo nickname nao pode entrar duas vezes na mesma sala.
- Depois de cada rodada, o programa mostra o saldo atual dos participantes e o saldo geral dos jogadores ainda cadastrados.

## Estrutura dos arquivos

- `main.py`: controla a abertura das salas e o cadastro dos jogadores
- `rodada.py`: executa a logica de cada rodada
- `jogador.py`: define os atributos e metodos de cada jogador
