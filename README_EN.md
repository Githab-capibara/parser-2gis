# Parser2GIS 🌍

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-LGPLv3%2B-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-269%20passed-brightgreen.svg)](testes/)
[![Code Quality](https://img.shields.io/badge/score-95/100-brightgreen.svg)](https://github.com/Githab-capibara/parser-2gis/wiki)
[![GitHub](https://img.shields.io/badge/GitHub-Githab--capibara-orange.svg)](https://github.com/Githab-capibara/parser-2gis)

**Parser2GIS** is a powerful tool for parsing data from the 2GIS service, using Chrome browser to bypass anti-bot protections.

---

## 📋 Table of Contents

- [About](#about)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Operating Modes](#operating-modes)
- [CLI Interface](#cli-interface)
- [Output Formats](#output-formats)
- [Configuration](#configuration)
- [Parallel Parsing](#parallel-parsing)
- [New Features v2.0](#new-features-v20)
- [New Features v2.1](#new-features-v21)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Development](#development)
- [Changelog](#changelog)
- [Code Quality Reports](#code-quality-reports)
- [FAQ](#faq)
- [Support](#support)

---

## 🎯 About

Parser2GIS is a Python application for automated data collection from the 2GIS website. The project allows:

- ✅ Parse organizations by cities and categories
- ✅ Save data in CSV, XLSX, JSON formats
- ✅ Work in CLI and GUI modes
- ✅ Use parallel parsing (up to 20 threads)
- ✅ Configure parameters via config files
- ✅ Cache results (10-100x speedup)
- ✅ Validate data before saving
- ✅ Export work statistics
- ✅ Automatically handle errors and 404 pages
- ✅ Use adaptive limits for cities
- ✅ Monitor browser health with auto-restart

### Technologies

| Component | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.8–3.12 | Main language |
| **Pydantic v2** | Latest | Data validation |
| **Chrome DevTools Protocol** | Latest | Browser control |
| **PySimpleGUI** | Optional | GUI |
| **pytest** | Latest | Testing |
| **SQLite** | Built-in | Result caching |
| **psutil** | Latest | Resource monitoring |
| **tqdm** | Latest | Progress bars |

### Supported OS

- ✅ **Linux Ubuntu** — main supported OS
- ⚠️ **Windows** — limited support (requires additional setup)
- ⚠️ **macOS** — limited support

---

## ✨ Features

### Data Parsing

- ✅ **204 cities** in 18 countries
- ✅ **93 categories** for parsing
- ✅ **1786 rubrics** for precise search
- ✅ Parse firms, bus stops, buildings
- ✅ Extract contact data, reviews, schedules
- ✅ Automatic navigation through pages
- ✅ Pagination handling

### Output Formats

| Format | Description | Advantages |
|--------|----------|------------|
| **CSV** | Delimited tables | Compatibility, speed |
| **XLSX** | Microsoft Excel files | Formatting, filters |
| **JSON** | Structured data | Programmatic parsing |

### Operating Modes

- ✅ **CLI** — command line for automation
- ✅ **GUI** — graphical interface for interactive work
- ✅ **Parallel parsing** — up to 20 threads for speedup

### Settings

- ✅ Flexible JSON configuration
- ✅ Chrome settings (headless, memory, blocking)
- ✅ Parser settings (delays, limits, retry)
- ✅ Output settings (encoding, columns, formatting)

---

## 📦 Installation

### Requirements

| Component | Version | Note |
|-----------|---------|------|
| **Python** | 3.8–3.12 | Required |
| **Google Chrome** | Any latest | For parsing |
| **Git** | Any latest | For repository work |
| **pip** | Latest | Dependency installation |

### Installation from PyPI

```bash
pip install parser-2gis
```

### Installation from Source

```bash
# Clone repository
git clone https://github.com/Githab-capibara/parser-2gis.git
cd parser-2gis

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .[dev]

# Install pre-commit hooks (optional)
pre-commit install
```

### Check Installation

```bash
# Check version
parser-2gis --version

# Check help
parser-2gis --help

# Run via module
python -m parser_2gis --help
```

---

## 🚀 Quick Start

### CLI Mode

#### Basic Example

```bash
# Parse pharmacies in Moscow (5 records)
parser-2gis \
  -i "https://2gis.ru/moscow/search/Аптеки" \
  -o moscow_pharmacies.csv \
  -f csv \
  --parser.max-records 5 \
  --chrome.headless yes
```

#### Parse All City Categories

```bash
# All 93 categories of Omsk (5 threads)
parser-2gis \
  --cities omsk \
  --categories-mode \
  --parallel-workers 5 \
  -o output/omsk_all_categories/ \
  -f csv \
  --chrome.headless yes \
  --chrome.disable-images yes
```

#### Multiple Cities

```bash
# Parse pharmacies in 3 cities
parser-2gis \
  --cities moscow spb kazan \
  --categories-mode \
  -o output/ \
  -f csv
```

#### With New Parameters (v2.1)

```bash
# Parse with adaptive limits and retry
parser-2gis \
  --cities omsk \
  --categories-mode \
  --parallel-workers 3 \
  --parser.stop-on-first-404 yes \
  --parser.max-consecutive-empty-pages 5 \
  --parser.max-retries 3 \
  --parser.retry-on-network-errors yes \
  --chrome.headless yes \
  -o output/omsk_all.csv \
  -f csv
```

### GUI Mode

```bash
# Launch graphical interface
parser-2gis
```

---

## 🎮 Operating Modes

### CLI Mode

Command line for automation and scripts.

**Advantages:**
- ⚡ Fast launch
- 🔧 Easy CI/CD integration
- 📜 Suitable for scripts and automation
- 🎛️ Full control via arguments
- 📊 Beautiful progress bars (via ProgressManager)

### GUI Mode

Graphical interface for interactive work.

**Advantages:**
- 🖼️ User-friendly interface
- 🏙️ Visual city and category selection
- 📈 Real-time progress viewing
- 🎓 No command line knowledge required

---

## 💻 CLI Interface

### Main Arguments

| Argument | Description | Required |
|----------|----------|----------|
| `-i, --url` | URL for parsing | No* |
| `-o, --output` | Output file path | No** |
| `-f, --format` | Output format (csv, xlsx, json) | No |
| `-v, --version` | Program version | No |
| `-h, --help` | Help | No |

*Required if `--cities` not used
**Required if `--categories-mode` used

### Parallel Parsing Arguments

| Argument | Description | Default |
|----------|----------|---------|
| `--cities` | List of cities for parsing | - |
| `--categories-mode` | Category parsing mode | False |
| `--parallel-workers` | Number of threads (1-20) | 3 |

### Chrome Arguments

| Argument | Description | Default |
|----------|----------|---------|
| `--chrome.headless` | Background mode | False |
| `--chrome.disable-images` | Disable images | True |
| `--chrome.memory-limit` | Memory limit (MB) | Auto |
| `--chrome.binary-path` | Path to Chrome | Auto |

### Parser Arguments (v2.0, v2.1)

| Argument | Description | Default |
|----------|----------|---------|
| `--parser.max-records` | Max records count | ∞ |
| `--parser.delay-between-clicks` | Delay between clicks (ms) | 0 |
| `--parser.skip-404-response` | Skip 404 responses | True |
| `--parser.use-gc` | Use garbage collector | False |
| `--parser.gc-pages-interval` | GC interval (pages) | 10 |
| `--parser.stop-on-first-404` | Immediate stop on 404 (v2.1) | False |
| `--parser.max-consecutive-empty-pages` | Consecutive empty pages limit (v2.1) | 3 |
| `--parser.max-retries` | Max retry attempts (v2.1) | 3 |
| `--parser.retry-on-network-errors` | Retry on network errors (v2.1) | True |
| `--parser.retry-delay-base` | Base retry delay in sec (v2.1) | 1.0 |
| `--parser.memory-threshold` | Memory threshold for cleanup in MB (v2.1) | 2048 |

### Full Example

```bash
parser-2gis \
  --cities moscow spb \
  --categories-mode \
  --parallel-workers 5 \
  --chrome.headless yes \
  --chrome.disable-images yes \
  --chrome.memory-limit 512 \
  --parser.max-records 100 \
  --parser.delay-between-clicks 500 \
  --parser.use-gc yes \
  --parser.stop-on-first-404 yes \
  --parser.max-consecutive-empty-pages 5 \
  --parser.max-retries 3 \
  --parser.retry-on-network-errors yes \
  -o output/ \
  -f csv
```

---

## 📊 Output Formats

### CSV

Delimited table.

**Settings:**
- `add_rubrics` — add rubrics (True)
- `add_comments` — add comments (True)
- `columns_per_entity` — columns per entity (1-5, 3)
- `remove_empty_columns` — remove empty columns (True)
- `remove_duplicates` — remove duplicates (True)
- `join_char` — list separator ("; ")

**Configuration Example:**
```json
{
  "writer": {
    "csv": {
      "add_rubrics": true,
      "add_comments": true,
      "columns_per_entity": 3,
      "remove_empty_columns": true,
      "remove_duplicates": true,
      "join_char": "; "
    }
  }
}
```

### XLSX

Microsoft Excel files.

**Advantages:**
- 📊 Cell formatting
- 📏 Automatic column width
- 🔍 Filter support
- 💼 Excel compatibility

### JSON

Structured data.

**Advantages:**
- 🗂️ Full data structure
- 💻 Easy programmatic parsing
- 📦 Nested object support

---

## ⚙️ Configuration

### Create Configuration

```bash
# Auto-create configuration
parser-2gis --config /path/to/config.json
```

### Configuration Structure

```json
{
  "version": "0.1",
  "log": {
    "level": "DEBUG",
    "cli_format": "%(levelname)s - %(message)s",
    "gui_format": "[%(asctime)s] %(levelname)s: %(message)s",
    "gui_datefmt": "%H:%M:%S"
  },
  "writer": {
    "encoding": "utf-8-sig",
    "verbose": true,
    "csv": {
      "add_rubrics": true,
      "add_comments": true,
      "columns_per_entity": 3,
      "remove_empty_columns": true,
      "remove_duplicates": true,
      "join_char": "; "
    }
  },
  "chrome": {
    "binary_path": null,
    "start_maximized": false,
    "headless": false,
    "disable_images": true,
    "silent_browser": true,
    "memory_limit": 1024
  },
  "parser": {
    "max_records": null,
    "delay_between_clicks": 0,
    "skip_404_response": true,
    "use_gc": false,
    "gc_pages_interval": 10,
    "stop_on_first_404": false,
    "max_consecutive_empty_pages": 3,
    "max_retries": 3,
    "retry_on_network_errors": true,
    "retry_delay_base": 1.0,
    "memory_threshold": 2048
  }
}
```

### Use Configuration

```bash
# Use configuration
parser-2gis --config config.json \
  -i "https://2gis.ru/moscow/search/Аптеки" \
  -o output.csv \
  -f csv
```

---

## 🔄 Parallel Parsing

### Category Mode

Parse by categories for a city.

```bash
# All 93 categories of Omsk
parser-2gis \
  --cities omsk \
  --categories-mode \
  --parallel-workers 5 \
  -o output/omsk_all/ \
  -f csv
```

### Multiple Cities

```bash
# Three cities (3 threads)
parser-2gis \
  --cities moscow spb kazan \
  --categories-mode \
  -o output/ \
  -f csv
```

### Custom Categories

```python
# parser_2gis/data/custom_categories.py
CATEGORIES = [
    {"name": "Аптеки", "query": "Аптеки", "rubric_code": "204"},
    {"name": "Супермаркеты", "query": "Супермаркеты", "rubric_code": "350"},
    {"name": "Кафе", "query": "Кафе", "rubric_code": "161"}
]
```

### Optimization

```bash
# Maximum performance
parser-2gis \
  --cities moscow spb \
  --categories-mode \
  --parallel-workers 20 \
  --parser.use-gc yes \
  --parser.gc-pages-interval 10 \
  --parser.stop-on-first-404 yes \
  --parser.max-consecutive-empty-pages 5 \
  --chrome.headless yes \
  --chrome.disable-images yes \
  -o output/ \
  -f csv
```

**Recommendations:**
- ✅ 3-5 threads for normal tasks
- ✅ 10-20 threads for servers with lots of RAM
- ✅ Enable GC for parsing > 10000 records
- ✅ Use headless mode on servers
- ✅ Enable `stop_on_first_404` for small cities
- ✅ Use adaptive limits for different cities

---

## 🎯 New Features (v2.0)

### 1. CacheManager — Result Caching

Cache parsing results in local SQLite database for faster repeated runs.

**Advantages:**
- ⚡ 10-100x speedup for repeated runs
- 🗑️ Automatic stale cache removal
- 📊 Cache usage statistics
- 🧹 Cache cleanup capability

**Usage Example:**

```python
from pathlib import Path
from parser_2gis import CacheManager

# Create cache manager (TTL = 24 hours)
cache = CacheManager(Path('/tmp/parser_cache'), ttl_hours=24)

# Get data from cache
data = cache.get('https://2gis.ru/moscow/search/Аптеки')
if data is None:
    # Cache miss — parse
    data = parse_data(url)
    # Save to cache
    cache.set(url, data)

# Get statistics
stats = cache.get_stats()
print(f"Cache records: {stats['total_records']}")
print(f"Cache size: {stats['cache_size']} bytes")

# Clear expired cache
expired_count = cache.clear_expired()
print(f"Deleted expired records: {expired_count}")

# Full cache clear
cache.clear()
```

### 2. ProgressManager — CLI Progress Bar

Beautiful and informative progress bars for command line using tqdm.

**Advantages:**
- 📊 Double progress bar (pages and records)
- ⏱️ ETA and speed display
- 📈 Final statistics on completion
- 🔕 Ability to disable

**Usage Example:**

```python
from parser_2gis.cli import ProgressManager

# Create progress manager
progress = ProgressManager()

# Start progress bar
progress.start(total_pages=10, total_records=1000)

# Update progress
for page in range(10):
    # Process page...
    progress.update_page()

    for record in range(100):
        # Process record...
        progress.update_record()

# Finish and print statistics
progress.finish()
# Output: "✅ Completed in 45.2 sec (22.1 records/sec)"
```

### 3. DataValidator — Data Validation

Validate and clean data before saving to improve output file quality.

**Advantages:**
- 📞 Phone number formatting
- ✉️ Email validation
- 🔗 URL validation
- 🧹 Text cleanup from extra characters
- ✅ Full record validation

**Usage Example:**

```python
from parser_2gis import DataValidator

validator = DataValidator()

# Phone validation
result = validator.validate_phone('+7 (999) 123-45-67')
if result.is_valid:
    print(result.value)  # '8 (999) 123-45-67'

# Email validation
result = validator.validate_email('TEST@EXAMPLE.COM')
if result.is_valid:
    print(result.value)  # 'test@example.com'

# URL validation
result = validator.validate_url('https://example.com')
if result.is_valid:
    print(result.value)

# Full record validation
record = {
    'name': '  Test Company  ',
    'phone_1': '+79991234567',
    'email_1': 'TEST@EXAMPLE.COM',
    'website_1': 'https://example.com'
}
validated = validator.validate_record(record)
# Result: cleaned and validated record
```

### 4. StatisticsExporter — Statistics Export

Export parser statistics to various formats (JSON, CSV, HTML, TXT).

**Advantages:**
- 📄 Beautiful HTML reports
- 📦 Structured JSON data
- 📊 Readable CSV files
- 📝 Text reports
- 📈 Complete work statistics

**Usage Example:**

```python
from pathlib import Path
from datetime import datetime
from parser_2gis import ParserStatistics, StatisticsExporter

# Create statistics
stats = ParserStatistics()
stats.start_time = datetime.now()
stats.total_urls = 10
stats.total_pages = 50
stats.total_records = 1000
stats.successful_records = 950
stats.failed_records = 50
stats.cache_hits = 800
stats.cache_misses = 200
stats.end_time = datetime.now()

# Export statistics
exporter = StatisticsExporter()

# JSON format
exporter.export_to_json(stats, Path('stats.json'))

# HTML format (beautiful report)
exporter.export_to_html(stats, Path('stats.html'))

# CSV format
exporter.export_to_csv(stats, Path('stats.csv'))

# Text format
exporter.export_to_text(stats, Path('stats.txt'))
```

### 5. FileLogger — Improved Logging

Improved logging with console, file, and rotation support.

**Advantages:**
- 📝 Console and file support
- 🔄 Size and date rotation
- 📋 Message formatting
- 🎚️ Different logging levels
- 🔍 Type filtering

**Usage Example:**

```python
from pathlib import Path
from parser_2gis.logger import FileLogger

# Create logger
logger = FileLogger(
    log_file=Path('parser.log'),
    console_level='INFO',
    file_level='DEBUG',
    max_file_size=10*1024*1024,  # 10 MB
    backup_count=5
)

# Logging
logger.debug('Debug message')
logger.info('Info message')
logger.warning('Warning')
logger.error('Error')

# Close logger
logger.close()
```

---

## 🚀 New Features (v2.1)

### 1. AdaptiveLimits — Adaptive Limits for Different Cities

Automatic city size detection and empty page limit adjustment for parsing optimization.

**Advantages:**
- 🌍 Automatic city classification (small, medium, large, huge)
- 📏 Adaptive empty page limits (2-7)
- ⏱️ Adaptive navigation timeouts (30-120 sec)
- 📊 City size detection based on first pages

**City Classification:**

| Size | Records per Page | Empty Page Limit |
|------|------------------|------------------|
| `small` | ≤ 10 | 2 |
| `medium` | ≤ 50 | 3 |
| `large` | ≤ 200 | 5 |
| `huge` | > 200 | 7 |

**Usage Example:**

```python
from parser_2gis.parser.adaptive_limits import AdaptiveLimits

# Create adaptive limits manager
limits = AdaptiveLimits(base_limit=3)

# Add records count from first pages
limits.add_records_count(10)
limits.add_records_count(15)
limits.add_records_count(20)

# Get adaptive limit for city
adaptive_limit = limits.get_adaptive_limit()
print(f"Adaptive empty page limit: {adaptive_limit}")

# Get city size
city_size = limits.get_city_size()
print(f"City size: {city_size}")  # 'small', 'medium', 'large', 'huge'

# Get statistics
stats = limits.get_stats()
print(f"Average records per page: {stats['avg_records']}")
print(f"Records on first pages: {stats['records_on_first_pages']}")
```

### 2. SmartRetryManager — Intelligent Retry Mechanism

Smart retry system that analyzes error type and context for retry decisions.

**Advantages:**
- 🔍 Error type analysis (502, 503, 504, 404, 403, 500)
- 📚 Context awareness (record count, retry history)
- ⏱️ Exponential backoff between retries
- 🔢 Maximum retry limit

**Retry Logic:**
- 🌐 Network errors (502, 503, 504, Timeout) — always retry
- 📄 404 with records — retry (possible temporary issue)
- ❌ 404 without records — no retry (end of category)
- 🚫 403 (block) — no retry (useless)
- ⚠️ 500 (server error) — retry

**Usage Example:**

```python
from parser_2gis.parser.smart_retry import SmartRetryManager

# Create retry manager
retry = SmartRetryManager(max_retries=3)

# Check if retry needed
if retry.should_retry('502 Bad Gateway', records_on_page=10):
    print("Retrying")

# Add records
retry.add_records(50)

# Get statistics
stats = retry.get_stats()
print(f"Retry count: {stats['retry_count']}")
print(f"Total records: {stats['total_records']}")
```

### 3. EndOfResultsDetector — End of Results Detection

Automatic end of results detection on page for parsing optimization.

**Advantages:**
- 🔍 End of results detection
- 📄 Pagination check
- ⚡ Parsing time optimization
- 🚫 Avoid unnecessary requests

**Usage Example:**

```python
from parser_2gis.parser.end_of_results import EndOfResultsDetector

# Create detector
detector = EndOfResultsDetector(chrome_remote)

# Check if end of results reached
if detector.is_end_of_results():
    print("End of results reached")
    return

# Check pagination presence
if detector.has_pagination():
    print("Pagination exists, continue parsing")
```

### 4. ParallelOptimizer — Parallel Parsing Optimizer

Intelligent parallel parsing task management with priority and resource awareness.

**Advantages:**
- 🎯 Task prioritization
- 💾 Memory usage monitoring
- 📊 Execution statistics
- ⚡ Task distribution optimization

**Usage Example:**

```python
from parser_2gis.parallel_optimizer import ParallelOptimizer

# Create optimizer
optimizer = ParallelOptimizer(max_workers=5, max_memory_mb=4096)

# Add tasks
optimizer.add_task(
    url='https://2gis.ru/moscow/search/Аптеки',
    category_name='Аптеки',
    city_name='Москва',
    priority=1  # High priority
)

# Check resources
available, memory_mb = optimizer.check_resources()
if not available:
    print(f"Waiting for resources. Memory: {memory_mb} MB")

# Get next task
task = optimizer.get_next_task()
if task:
    print(f"Processing task: {task.city_name} - {task.category_name}")

# Get statistics
stats = optimizer.get_stats()
print(f"Progress: {stats['progress']}%")
print(f"Total tasks: {stats['total_tasks']}")
print(f"Completed: {stats['completed']}")
```

### 5. BrowserHealthMonitor — Browser Health Monitor

Continuous browser health monitoring with automatic restart on critical errors.

**Advantages:**
- ❤️ Browser health monitoring
- 🔄 Automatic restart on errors
- 📊 Critical error statistics
- 🛡️ Hang prevention

**Usage Example:**

```python
from parser_2gis.chrome.health_monitor import BrowserHealthMonitor

# Create monitor
monitor = BrowserHealthMonitor(chrome_remote)

# Start monitoring
monitor.start()

# Check health
if not monitor.is_healthy():
    print("Browser unhealthy, restarting...")
    monitor.restart()

# Get statistics
stats = monitor.get_stats()
print(f"Critical errors: {stats['critical_errors']}")
print(f"Restarts: {stats['restarts']}")
```

---

## 📁 Project Structure

```
parser-2gis/
├── parser_2gis/              # Main package
│   ├── chrome/               # Chrome browser module
│   │   ├── patches/          # Patches for pychrome
│   │   ├── browser.py        # Browser wrapper
│   │   ├── remote.py         # Remote debugging
│   │   ├── dom.py            # DOM manipulation
│   │   ├── exceptions.py     # Chrome exceptions
│   │   ├── health_monitor.py # Browser health
│   │   ├── options.py        # Chrome options
│   │   └── utils.py          # Utilities
│   ├── parser/               # Parser module
│   │   ├── parsers/          # Parser implementations
│   │   ├── adaptive_limits.py # Adaptive limits
│   │   ├── smart_retry.py    # Smart retry
│   │   ├── end_of_results.py # End detection
│   │   ├── factory.py        # Parser factory
│   │   ├── options.py        # Parser options
│   │   └── utils.py          # Parser utilities
│   ├── writer/               # Writer module
│   │   ├── models/           # Data models
│   │   ├── writers/          # Writer implementations
│   │   ├── factory.py        # Writer factory
│   │   └── options.py        # Writer options
│   ├── logger/               # Logging module
│   │   ├── logger.py         # Main logger
│   │   ├── file_handler.py   # File handler
│   │   ├── options.py        # Logger options
│   │   └── visual_logger.py  # Visual logger
│   ├── cli/                  # CLI module
│   │   ├── app.py            # CLI app
│   │   └── progress.py       # Progress manager
│   ├── tui/                  # TUI module
│   │   ├── app.py            # TUI app
│   │   └── components.py     # UI components
│   ├── runner/               # Runner module
│   │   ├── runner.py         # Main runner
│   │   └── cli.py            # CLI runner
│   ├── data/                 # Data files
│   │   ├── cities.json       # Cities list
│   │   ├── rubrics.json      # Rubrics list
│   │   └── categories_93.py  # 93 categories
│   ├── cache.py              # Cache manager
│   ├── common.py             # Common utilities
│   ├── config.py             # Configuration
│   ├── exceptions.py         # Base exceptions
│   ├── main.py               # Entry point
│   ├── parallel_parser.py    # Parallel parser
│   ├── parallel_optimizer.py # Parallel optimizer
│   ├── paths.py              # Path utilities
│   ├── statistics.py         # Statistics
│   ├── validator.py          # Data validator
│   └── version.py            # Version info
├── testes/                   # Tests
│   ├── test_*.py             # Test files
│   └── conftest.py           # Pytest config
├── scripts/                  # Utility scripts
│   ├── update_cities_list.py
│   └── update_rubrics_list.py
├── output/                   # Output directory
├── logs/                     # Log files
├── venv/                     # Virtual environment
├── README.md                 # Russian documentation
├── README_EN.md              # English documentation
├── CHANGELOG.md              # Changelog
├── LICENSE                   # License
└── pyproject.toml            # Project config
```

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest testes/ -v

# Run specific test
pytest testes/test_parser.py -v

# Run with coverage
pytest testes/ --cov=parser_2gis -v

# Run specific test class
pytest testes/test_parser.py::TestParser -v
```

### Test Coverage

Current coverage: ~60%

| Module | Coverage | Status |
|--------|----------|--------|
| **parser/** | 65% | ✅ Good |
| **chrome/** | 60% | ✅ Good |
| **writer/** | 70% | ✅ Good |
| **logger/** | 55% | ⚠️ Medium |
| **cli/** | 50% | ⚠️ Medium |

---

## 🛠️ Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/Githab-capibara/parser-2gis.git
cd parser-2gis

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install
```

### Code Style

```bash
# Format code
black parser_2gis/

# Check style
flake8 parser_2gis/

# Type checking
mypy parser_2gis/
```

### Build Package

```bash
# Build wheel
python -m build

# Install locally
pip install -e .
```

---

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for full history.

### Latest Version: 1.2.2 (2026-03-12)

**Fixes:**
- Fixed logical error in wait_until_finished decorator
- Fixed potential XSS vulnerability in chrome/remote.py
- Fixed access to non-existent timeout attribute
- Fixed code style in validator.py
- Translated comments to Russian
- Removed unused code from common.py

**Improvements:**
- Added JavaScript code validation
- Improved error handling
- Optimized memory management
- Improved type hints

---

## 📊 Code Quality Reports

> Code quality reports are available in the [project wiki](https://github.com/Githab-capibara/parser-2gis/wiki).

---

## ❓ FAQ

### Q: How to parse multiple cities?

A: Use `--cities` argument with multiple city names:

```bash
parser-2gis --cities moscow spb kazan --categories-mode -o output/ -f csv
```

### Q: How to increase parsing speed?

A: Use parallel parsing with more threads:

```bash
parser-2gis --cities omsk --categories-mode --parallel-workers 10 -o output/ -f csv
```

### Q: How to parse only first N records?

A: Use `--parser.max-records` argument:

```bash
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" --parser.max-records 100 -o output.csv -f csv
```

### Q: How to enable headless mode?

A: Use `--chrome.headless yes` argument:

```bash
parser-2gis -i "URL" --chrome.headless yes -o output.csv -f csv
```

### Q: Where are results saved?

A: By default, results are saved to the specified output file or directory. Use `-o` argument to set path.

---

## 📞 Support

### Documentation

- 📖 [Russian README](README.md)
- 📝 [Changelog](CHANGELOG.md)
- 📊 [Code Quality Reports](https://github.com/Githab-capibara/parser-2gis/wiki)

### Issues

- 🐛 [Report a bug](https://github.com/Githab-capibara/parser-2gis/issues)
- 💡 [Request a feature](https://github.com/Githab-capibara/parser-2gis/issues)

### Community

- 💬 [Discussions](https://github.com/Githab-capibara/parser-2gis/discussions)
- 📧 Email: support@parser-2gis.ru

---

## 📄 License

Distributed under LGPLv3+ license. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Original project by [@interlark](https://github.com/interlark/parser-2gis)
- Maintained by [@Githab-capibara](https://github.com/Githab-capibara)
- Thanks to all contributors!

---

**Version:** 1.2.2  
**Last Updated:** 2026-03-12  
**Language:** English (en)
