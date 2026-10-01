"""Tests for DakeraEntityExtractor (AutoGen integration)."""

from unittest.mock import MagicMock, create_autospec, patch

import pytest
from dakera import DakeraClient

from autogen_dakera.entities import DakeraEntityExtractor


@pytest.fixture
def extractor():
    with patch("autogen_dakera.entities.DakeraClient") as MC:
        mock_client = create_autospec(DakeraClient, instance=True)
        MC.return_value = mock_client
        ext = DakeraEntityExtractor(
            api_url="http://localhost:3000", agent_id="test-agent", api_key="test"
        )
        ext._client = mock_client
        yield ext, mock_client


def test_extract_returns_entities(extractor):
    ext, mock_client = extractor
    mock_entity = MagicMock()
    mock_entity.entity_type = "PERSON"
    mock_entity.value = "Alice"
    mock_entity.score = 0.95
    mock_result = MagicMock()
    mock_result.entities = [mock_entity]
    mock_client.extract_entities.return_value = mock_result

    result = ext.extract("Alice went to the store")
    assert len(result) == 1
    assert result[0] == {"type": "PERSON", "value": "Alice", "score": 0.95}
    mock_client.extract_entities.assert_called_once_with(
        "Alice went to the store", entity_types=None
    )


def test_extract_with_type_filter(extractor):
    ext, mock_client = extractor
    mock_result = MagicMock()
    mock_result.entities = []
    mock_client.extract_entities.return_value = mock_result

    ext.extract("text", entity_types=["ORG", "LOC"])
    mock_client.extract_entities.assert_called_once_with("text", entity_types=["ORG", "LOC"])


def test_extract_empty_text(extractor):
    ext, mock_client = extractor
    mock_result = MagicMock()
    mock_result.entities = []
    mock_client.extract_entities.return_value = mock_result

    result = ext.extract("")
    assert result == []


def test_memory_entities(extractor):
    ext, mock_client = extractor
    mock_entity = MagicMock()
    mock_entity.entity_type = "ORG"
    mock_entity.value = "Dakera"
    mock_entity.score = 0.88
    mock_result = MagicMock()
    mock_result.entities = [mock_entity]
    mock_client.memory_entities.return_value = mock_result

    result = ext.memory_entities("mem_123")
    assert result == [{"type": "ORG", "value": "Dakera", "score": 0.88}]
    mock_client.memory_entities.assert_called_once_with("mem_123")


def test_configure_calls_client(extractor):
    ext, mock_client = extractor
    ext.configure(entity_types=["PERSON", "ORG"])
    mock_client.configure_namespace_ner.assert_called_once_with(
        "_dakera_agent_test-agent", extract_entities=True, entity_types=["PERSON", "ORG"]
    )


def test_configure_can_disable_extraction(extractor):
    ext, mock_client = extractor
    ext.configure(extract_entities=False)
    mock_client.configure_namespace_ner.assert_called_once_with(
        "_dakera_agent_test-agent", extract_entities=False, entity_types=None
    )
