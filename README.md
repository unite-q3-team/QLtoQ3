# qltoq3
## en
a tiny converter for Quake Live `.pk3` maps to Quake 3: Arena format.

### overview

- works with local `.pk3` files and directories
- works with steam workshop item ids
- works with steam collection ids (auto expands many items)
- converts textures, models and map metadata for quake 3
- runs optional bot navmesh (`aas`) with `bspc`
- restores missing quake-live assets from `pak00.pk3` when available

### install

1) clone:

```bash
git clone https://github.com/unite-q3-team/QLtoQ3
cd QLtoQ3
```

2) install:

```bash
pip install -e .
```

or:

```bash
pip install .
```

optional tools:

- `bspc.exe` for aas (path set by `--bspc`)
- `ffmpeg` for `ogg` -> `wav` (path set by `--ffmpeg`)

### cli usage

show options:

```bash
qltoq3 --help
```

convert a local folder (or file) in `input_dir`:

```bash
qltoq3 --output q3 outdir input_dir
```

convert workshop item(s):

```bash
qltoq3 --output q3 --workshop 111111111 222222222
```

convert collection(s):

```bash
qltoq3 --output q3 --collection 333333333
```

quick run without aas:

```bash
qltoq3 --output q3 input_dir --no-aas
```

all supported options:

- `--lang [en|ru]` — ui language for cli output
- `--output PATH` — output folder (or single target pk3)
- `--yes-always` — convert without confirmation prompts
- `--no-aas` — skip aas generation with bspc
- `--aas-timeout SEC` — timeout for one map aas step
- `--aas-threads N` — `bspc -threads` for one map
- `--no-aas-optimize` — skip bspc `-optimize`
- `--aas-geometry-fast` — shorthand for nocsg + freetree
- `--aas-bspc-nocsg` — pass `-nocsg` to bspc
- `--aas-bspc-freetree` — pass `-freetree` to bspc
- `--aas-bspc-breadthfirst` — pass `-breadthfirst` to bspc
- `--bspc-concurrent N` — max simultaneous bspc jobs
- `--force` — overwrite output files
- `--workshop ID [ID ...]` — convert workshop item ids
- `--collection ID [ID ...]` — expand and convert collection ids
- `--optimize` — convert safe textures to jpeg
- `--bsp-patch-method 1|2` — choose entity patch mode
- `--bspc PATH` — custom path to `bspc.exe`
- `--levelshot PATH` — custom levelshot image
- `--steamcmd PATH` — steamcmd path for workshop download
- `--ffmpeg PATH` — ffmpeg path for ogg->wav
- `--verbose` — print more logs and extra errors
- `--show-skipped` — show every skipped pk3 in log
- `--hide-converted` — hide per-file success lines
- `--skip-mapless` — skip files without any `.bsp`
- `--time-stages` — print timing summary by phase
- `--dry-run` / `--list` — show planned actions only
- `--no-color` — disable ansi colors
- `--no-progress` — disable progress bars
- `--log PATH` — save cleaned logs to file
- `--ql-pak PATH` — path to Quake Live `pak00.pk3`
- `--coworkers N` — concurrent pk3 conversions
- `--pool-max N` — max thread pool size

### gui usage

run:

```bash
qltoq3-gui
```

- local files/folders mode and steam mode are available in the gui
- set dependencies and paths (`bspc`, `ffmpeg`, `steamcmd`)
- tune worker/timeout/bspc options
- watch status and logs while converting

# qltoq3
## ru

это простой конвертер для паков из Quake Live в формат Quake 3: Arena. преобразовывает карты, текстуры и звуки, а недостающие ресурсы ищет в оригинальном паке Quake Live при наличии.

инструмент поддерживает:
- локальные `.pk3` и папки с картами
- айдишники из мастерской Steam через `--workshop`
- айдишники коллекций Steam через `--collection`

### установка

```bash
git clone https://github.com/unite-q3-team/QLtoQ3
cd QLtoQ3
```

```bash
pip install -e .
```

или:

```bash
pip install .
```

### cli usage

```bash
qltoq3 --help
```

локальная конвертация:

```bash
qltoq3 --output q3 outdir input_dir
```

steam workshop:

```bash
qltoq3 --output q3 --workshop 111111111 222222222
```

коллекция:

```bash
qltoq3 --output q3 --collection 333333333
```

без aas:

```bash
qltoq3 --output q3 input_dir --no-aas
```

все флаги:

- `--lang [en|ru]` — язык вывода сообщений
- `--output PATH` — папка вывода (или итоговый pk3)
- `--yes-always` — не спрашивать подтверждения
- `--no-aas` — пропустить генерацию aas
- `--aas-timeout SEC` — максимальное время ожидания генерации AAS на карту
- `--aas-threads N` — количество потоков для одной карты
- `--no-aas-optimize` — пропустить оптимизацию AAS
- `--aas-geometry-fast` — короткая запись для nocsg + freetree
- `--aas-bspc-nocsg` — добавить `-nocsg` в bspc
- `--aas-bspc-freetree` — добавить `-freetree` в bspc
- `--aas-bspc-breadthfirst` — добавить `-breadthfirst` в bspc
- `--bspc-concurrent N` — лимит параллельных bspc задач
- `--force` — перезаписывать уже готовые файлы
- `--workshop ID [ID ...]` — список предметов из мастерской Steam
- `--collection ID [ID ...]` — список коллекций из мастерской Steam
- `--optimize` — пробовать сжимать текстуры в jpeg
- `--bsp-patch-method 1|2` — режим патча entities в карте (второй лучше)
- `--bspc PATH` — путь к `bspc.exe`
- `--levelshot PATH` — путь к кастомному levelshot
- `--steamcmd PATH` — путь к steamcmd для скачивания из мастерской
- `--ffmpeg PATH` — путь к ffmpeg для конверсии ogg->wav
- `--verbose` — больше логов и деталей ошибок
- `--show-skipped` — печатать все пропущенные паки
- `--hide-converted` — не печатать `ok` по каждому pk3
- `--skip-mapless` — пропустить паки без `.bsp`
- `--time-stages` — вывести время по этапам
- `--dry-run` / `--list` — только показ плана конверсии, без записи
- `--no-color` — отключить цвета терминала
- `--no-progress` — без tqdm прогресса (полоска прогресса внизу)
- `--log PATH` — писать лог в файл
- `--ql-pak PATH` — путь к `pak00.pk3` от Quake Live
- `--coworkers N` — число одновременных конверсий паков
- `--pool-max N` — максимальный размер пула потоков

### gui usage

```bash
qltoq3-gui
```
