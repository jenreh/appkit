# Shared Fixtures

```python
# tests/unit/conftest.py
import pytest
from myapp.state import AppState

@pytest.fixture
def state():
    return AppState()

@pytest.fixture
def state_with_data(state):
    state.items = ["a", "b", "c"]
    return state
```
