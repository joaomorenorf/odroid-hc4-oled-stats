# ODROID HC4 OLED Stats

Versao modificada de [tobetter/odroid-homecloud](https://github.com/tobetter/odroid-homecloud)
para mostrar estatisticas do sistema no OLED do ODROID HC4. O historico original
e a licenca MIT foram preservados; veja [LICENSE](./LICENSE).

O repositorio tem outro nome, mas os nomes do pacote
`odroid-homecloud-display`, do comando `odroid_homecloud_display` e do servico
`odroid-homecloud-display` foram mantidos para permitir atualizar a instalacao
anterior. A versao atual e `0.4.0`.

## O que aparece na tela

O programa usa um SSD1306 I2C de 128 x 64 pixels, com quatro linhas por pagina.
Atualiza CPU e RAM aproximadamente a cada segundo e alterna paginas a cada cinco
segundos. As consultas externas podem acrescentar algum atraso.
**Esta versao mostra estatisticas, nao o relogio do projeto original.**

Exemplo ilustrativo da primeira pagina (os valores nao sao dados do seu ODROID):

```text
CPU: 12%  48 C
RAM: 1,2 / 4,0 GB
sd: 8,5 / 31,3 GB
tank: 450,0 / 2000,0 GB
```

- CPU: utilizacao entre duas amostras de `/proc/stat`; temperatura de
  `/sys/class/thermal/thermal_zone0/temp`, ou `N/A` quando indisponivel.
- RAM: memoria usada calculada como `MemTotal - MemAvailable`, e memoria total.
- `sd`: uso do sistema de arquivos montado em `/`, mesmo que ele nao esteja
  em um cartao SD.
- `tank`: valores `used` e `used + available` do dataset ZFS chamado `tank`.
  Nao e uma soma de discos fisicos. ZFS e opcional: sem o comando `zfs` ou sem
  esse dataset, aparece `tank: unavailable`. Nao e necessario instalar ZFS
  apenas para usar o display.
- GB usa base decimal (`1 GB = 1.000.000.000 bytes`), com virgula decimal.
  Linhas maiores que a largura da tela sao comprimidas horizontalmente para
  preservar os numeros.

Em seguida aparecem as paginas de rede, por exemplo:

```text
IPv4: 192.0.2.10
IPv6: eth0
2001:4860:1234:5678:
abcd:ef01:2345:6789
```

O IPv4 acima e um endereco reservado para documentacao e o IPv6 e apenas
ilustrativo. A quebra do IPv6 depende da fonte instalada; o exemplo nao garante
os mesmos pontos de quebra no seu dispositivo. A segunda linha identifica a
interface. O programa inclui IPv4 e somente IPv6 globais, nao temporarios.
Ignora loopback e interfaces com nomes iniciados por `docker`, `br-` e `veth`,
alem de enderecos tentativos ou com falha de DAD.

Cada interface/endereco pode gerar paginas adicionais; o IPv6 e quebrado em
blocos de ate duas linhas. Uma familia sem endereco aparece como `unavailable`.
Sem enderecos elegiveis aparece uma pagina com `IPv4: unavailable` e
`IPv6: unavailable`; se a consulta de rede falhar, aparece `IP: unavailable`.
Depois das paginas de rede, o ciclo volta as estatisticas.

## Construir em outra maquina (Linux ou WSL)

Use Debian/Ubuntu com `debhelper` 13 e `pybuild-plugin-pyproject` disponiveis
(por exemplo, Ubuntu 24.04, usado tambem na pipeline). Nao e preciso ter o OLED,
I2C, systemd em execucao ou a arquitetura ARM na maquina de build.

O pacote contem Python puro e declara `Architecture: all`. Portanto, pode ser
construido em WSL/x86_64 e instalado no ODROID/ARM64. As dependencias nativas
serao resolvidas pelo APT **no ODROID**, usando a arquitetura dele.

### 1. Instalar ferramentas com sudo

Na maquina de build:

```sh
sudo apt update
sudo apt install git build-essential debhelper dh-python \
  pybuild-plugin-pyproject python3-all python3-setuptools \
  python3-wheel
```

Para transferir o pacote por SCP ou SFTP, instale tambem o cliente SSH:

```sh
sudo apt install openssh-client
```

### 2. Clonar sua versao dentro da pasta pessoal

No WSL, use o sistema de arquivos Linux (`~/build`), nao `/mnt/c`, para evitar
problemas de permissoes, desempenho e finais de linha.

```sh
mkdir -p ~/build
cd ~/build
git clone https://github.com/joaomorenorf/odroid-hc4-oled-stats.git
cd odroid-hc4-oled-stats
```

**Nao e mais necessario executar o antigo bloco de atualizacao de arquivos.**
Os ajustes Python 3/pyproject/debhelper ja estao versionados neste fork, inclusive
para WSL. Clonar diretamente `tobetter/odroid-homecloud` nao inclui estes ajustes
nem o seu monitor modificado.

### 3. Gerar o pacote sem sudo

```sh
dpkg-buildpackage -us -uc -b
ls -lh ../odroid-homecloud-display_*.deb
dpkg-deb --field ../odroid-homecloud-display_0.4.0_all.deb Package Version Architecture Depends
```

O resultado desta versao e `../odroid-homecloud-display_0.4.0_all.deb`.
Arquivos `.changes` e `.buildinfo` tambem sao gerados na pasta pai.
Nenhum deles, nem os diretorios temporarios de build, deve ser commitado.
O build nao instala nem inicia o servico na maquina de empacotamento.

### 4. Transferir para o ODROID

Substitua `IP_DO_ODROID` pelo endereco real. O SSH precisa estar habilitado no
ODROID, e a identidade do servidor deve ser conferida na primeira conexao.
Use **uma** das opcoes abaixo. Troque a versao no nome se estiver usando outra.

**SCP:**

```sh
scp ../odroid-homecloud-display_0.4.0_all.deb root@IP_DO_ODROID:/root/
```

**SFTP interativo:**

```sh
sftp root@IP_DO_ODROID
```

No prompt `sftp>`, partindo da pasta do projeto na maquina de build:

```text
lcd ..
cd /root
put odroid-homecloud-display_0.4.0_all.deb
bye
```

Nao e necessario habilitar login SSH de root: se ele estiver desabilitado,
transfira para um usuario comum:

```sh
scp ../odroid-homecloud-display_0.4.0_all.deb USUARIO@IP_DO_ODROID:
```

Para SFTP com usuario comum, conecte com `sftp USUARIO@IP_DO_ODROID`, execute
`lcd ..`, `put odroid-homecloud-display_0.4.0_all.deb` e `bye`; omita `cd /root`.

### 5. Instalar e validar no ODROID

No terminal do ODROID, como root:

```sh
apt update
apt install /root/odroid-homecloud-display_0.4.0_all.deb
systemctl status odroid-homecloud-display --no-pager
```

Ou, se transferiu para um usuario comum, no diretorio pessoal desse usuario:

```sh
sudo apt update
sudo apt install ./odroid-homecloud-display_0.4.0_all.deb
sudo systemctl status odroid-homecloud-display --no-pager
```

O APT instala Pillow, luma e `iproute2` para a arquitetura do ODROID.
Nao use `pip` como root. Se alguma dependencia nao estiver disponivel, confira
os repositorios da distribuicao; no Ubuntu, pode ser necessario habilitar
`universe`. A maquina de destino deve usar uma versao de Debian/Ubuntu que
forneca as dependencias declaradas no pacote.

A instalacao pelo debhelper habilita/inicia o servico, respeitando a politica
local de servicos. Confira o status e a tela fisica: construir o `.deb` no WSL
nao valida hardware, I2C ou o funcionamento real do servico no ODROID.

### Configuracao e diagnostico

A primeira instalacao cria `/etc/default/odroid-homecloud`, sem sobrescrever
uma configuracao existente:

```sh
HOMECLOUD_DISPLAY_PORT=0
HOMECLOUD_DISPLAY_ROTATE=2
HOMECLOUD_DISPLAY_ADDRESS=0x3c
```

Esses valores selecionam o barramento I2C, a rotacao (0 a 3, em passos de 90
graus) e o endereco hexadecimal. Ajuste-os ao seu hardware e reinicie:

```sh
sudo systemctl restart odroid-homecloud-display
sudo systemctl status odroid-homecloud-display --no-pager
sudo journalctl -u odroid-homecloud-display -n 50 --no-pager
ls -l /dev/i2c-*
```

O driver usado nesta versao e `ssd1306`; nao ha selecao automatica de chipset.
Um endereco ou driver incorreto pode impedir o funcionamento do display.

Para obter as linhas reais que o programa prepararia **sem acessar o OLED**,
execute no ODROID depois da instalacao:

```sh
python3 - <<'PY'
import time
from odroid_homecloud_display import clock

previous = clock.cpu_sample()
time.sleep(1)
current = clock.cpu_sample()
total = current[0] - previous[0]
idle = current[1] - previous[1]
cpu = 100 * (1 - idle / total) if total else 0
used, capacity = clock.ram_usage()
pages = [[
    f"CPU: {cpu:.0f}%  {clock.temperature()}",
    f"RAM: {clock.decimal(used / 1e9)} / {clock.decimal(capacity / 1e9)} GB",
    *clock.storage_lines(),
]] + clock.network_pages(128)
for index, lines in enumerate(pages, 1):
    print(f"--- Pagina {index} ---")
    print("\n".join(lines))
PY
```

Esse comando mostra uma amostra pontual das linhas, nao uma captura dos pixels;
os valores variam e as linhas longas podem ser comprimidas ao desenhar.
Se compartilhar a saida, revise antes os enderecos IP e nomes de interfaces.

## Pipeline: gerar o .deb no GitHub

O workflow [Build Debian package](./.github/workflows/build-deb.yml) roda em
Ubuntu 24.04 a cada push e pull request. Tambem pode ser executado manualmente:

1. Abra **Actions > Build Debian package > Run workflow** no seu repositorio.
2. Selecione a branch desejada e execute.
3. Abra a execucao concluida e baixe o artifact
   **odroid-homecloud-display-deb**.
4. Descompacte o ZIP. Ele contem o `.deb` e `SHA256SUMS`.
5. Na pasta extraida, execute `sha256sum -c SHA256SUMS` e transfira o `.deb`
   por SCP ou SFTP conforme as instrucoes anteriores.

Tambem e possivel usar o GitHub CLI:

```sh
gh workflow run build-deb.yml --repo joaomorenorf/odroid-hc4-oled-stats
gh run list --workflow build-deb.yml --repo joaomorenorf/odroid-hc4-oled-stats
gh run download ID_DA_EXECUCAO --repo joaomorenorf/odroid-hc4-oled-stats \
  --name odroid-homecloud-display-deb --dir artifacts
cd artifacts
sha256sum -c SHA256SUMS
```

Substitua `ID_DA_EXECUCAO` pelo ID da execucao bem-sucedida. A pipeline publica
somente artifacts temporarios (30 dias), nao instala nada no ODROID, nao cria
uma Release e nao incrementa a versao automaticamente.
Em forks novos, o GitHub pode pedir que voce habilite Actions primeiro.

### Proximas versoes

Atualize a versao tanto em [setup.py](./setup.py) quanto no topo de
[debian/changelog](./debian/changelog), documente as mudancas e envie um commit.
O proximo push gera um novo pacote com essa versao. Incremente a versao para
que o APT reconheca atualizacoes; o workflow verifica se a versao Debian e a
mesma usada no nome do `.deb`.

## Arquivos publicaveis e artefatos locais

O codigo Python, `pyproject.toml`, `setup.py`, os arquivos-fonte em `debian/`,
a documentacao, a licenca e o workflow pertencem ao repositorio.
[.gitignore](./.gitignore) exclui caches, ambientes virtuais, metadados Python,
staging do debhelper, pacotes e outros resultados de build. Esses arquivos
podem continuar na sua maquina, mas nao entram no fork.

O projeto original continua em
[tobetter/odroid-homecloud](https://github.com/tobetter/odroid-homecloud).
O pacote inclui tambem os creditos e termos MIT em
`/usr/share/doc/odroid-homecloud-display/copyright`.