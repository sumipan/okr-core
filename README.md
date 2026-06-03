# okr-core

![CI](https://github.com/sumipan/okr-core/actions/workflows/test.yml/badge.svg)

OKR scoring and tracking core library.

## Installation

```bash
pip install okr-core
```

## Quick Start

```python
from okr_core.models import Objective, KeyResult
from okr_core.scoring import score_objective

kr = KeyResult(title="Increase revenue", target=100, current=75)
obj = Objective(title="Grow business", key_results=[kr])
print(score_objective(obj))  # 0.75
```

## Development Setup

```bash
git clone https://github.com/sumipan/okr-core.git
cd okr-core
pip install -e ".[dev]"
pytest
```

## License

MIT License — see [LICENSE](LICENSE) for details.
