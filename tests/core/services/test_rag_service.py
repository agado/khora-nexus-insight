from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.core.models import Document
from src.core.services.rag_service import (
    VALID_AUDIENCES,
    RagConnectionError,
    RagQueryError,
    _build_prompt,
    execute_query,
)


class TestExecuteQuery:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def user_admin(self):
        return {
            "sub": "admin",
            "role": "admin",
            "department_id": 1,
            "accessible_departments": [1, 2, 3],
            "user_id": 1,
        }

    def _make_doc(self, id_: int, dept: int, text: str | None = "content") -> Document:
        return Document(
            id=id_,
            filename=f"doc{id_}.pdf",
            sha256=f"sha{id_}",
            content_text=text,
            department_id=dept,
            uploaded_by=1,
        )

    @pytest.mark.asyncio
    async def test_excludes_docs_outside_user_dept(self, mock_db, user_admin):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        user_staff = {**user_admin, "accessible_departments": [2, 3]}

        ollama_response = MagicMock()
        ollama_response.status_code = 200
        ollama_response.json.return_value = {"response": "ok"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = ollama_response
            result = await execute_query(
                mock_db,
                "query",
                [1],
                user_staff,
                "http://ollama:11434",
                "qwen2.5-coder:1.5b",
            )

        assert result["context_used"] == []
        call_stmt = mock_db.execute.call_args[0][0]
        where_clause = str(call_stmt)
        assert "department_id" in where_clause

    @pytest.mark.asyncio
    async def test_returns_answer_and_context(self, mock_db, user_admin):
        docs = [
            self._make_doc(1, 1, "seguridad: no compartir claves"),
            self._make_doc(2, 2, "directrices Q3"),
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = docs
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        ollama_response = MagicMock()
        ollama_response.status_code = 200
        ollama_response.json.return_value = {"response": "No compartir claves"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = ollama_response
            result = await execute_query(
                mock_db,
                "¿normas de seguridad?",
                [1, 2],
                user_admin,
                "http://ollama:11434",
                "qwen2.5-coder:1.5b",
            )

        assert result["answer"] == "No compartir claves"
        assert len(result["context_used"]) == 2
        assert "seguridad: no compartir claves" in result["context_used"][0]

    @pytest.mark.asyncio
    async def test_ollama_timeout_raises_error(self, mock_db, user_admin):
        docs = [self._make_doc(1, 1, "data")]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = docs
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = (
                httpx.TimeoutException("ollama timeout")
            )
            with pytest.raises(RagConnectionError):
                await execute_query(
                    mock_db,
                    "query",
                    [1],
                    user_admin,
                    "http://ollama:11434",
                    "qwen2.5-coder:1.5b",
                )

    @pytest.mark.asyncio
    async def test_prompt_includes_xml_delimiters(self, mock_db, user_admin):
        docs = [self._make_doc(1, 1, "texto importante")]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = docs
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        ollama_response = MagicMock()
        ollama_response.status_code = 200
        ollama_response.json.return_value = {"response": "ok"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = ollama_response
            await execute_query(
                mock_db,
                "mi pregunta",
                [1],
                user_admin,
                "http://ollama:11434",
                "qwen2.5-coder:1.5b",
            )

        call_kwargs = mock_client.return_value.__aenter__.return_value.post.call_args[1]
        prompt = call_kwargs["json"]["prompt"]
        assert "<contexto>" in prompt
        assert "</contexto>" in prompt
        assert "<pregunta>" in prompt
        assert "</pregunta>" in prompt
        assert "mi pregunta" in prompt
        assert "texto importante" in prompt

    @pytest.mark.asyncio
    async def test_audit_log_inserted(self, mock_db, user_admin):
        docs = [self._make_doc(1, 1, "data")]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = docs
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        ollama_response = MagicMock()
        ollama_response.status_code = 200
        ollama_response.json.return_value = {"response": "respuesta"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = ollama_response
            await execute_query(
                mock_db,
                "query",
                [1],
                user_admin,
                "http://ollama:11434",
                "qwen2.5-coder:1.5b",
            )

        assert mock_db.add.called
        log = mock_db.add.call_args[0][0]
        assert log.action == "rag_query"
        assert log.user_id == 1
        assert log.metadata_["query"] == "query"

    @pytest.mark.asyncio
    async def test_ollama_connect_error_raises_rag_connection_error(self, mock_db, user_admin):
        docs = [self._make_doc(1, 1, "data")]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = docs
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.ConnectError(
                "connection refused"
            )
            with pytest.raises(RagConnectionError):
                await execute_query(
                    mock_db,
                    "query",
                    [1],
                    user_admin,
                    "http://ollama:11434",
                    "qwen2.5-coder:1.5b",
                )

    @pytest.mark.asyncio
    async def test_ollama_http_error_raises_rag_query_error(self, mock_db, user_admin):
        docs = [self._make_doc(1, 1, "data")]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = docs
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = (
                httpx.HTTPStatusError(
                    "400 error",
                    request=MagicMock(),
                    response=MagicMock(status_code=400),
                )
            )
            with pytest.raises(RagQueryError):
                await execute_query(
                    mock_db,
                    "query",
                    [1],
                    user_admin,
                    "http://ollama:11434",
                    "qwen2.5-coder:1.5b",
                )

    @pytest.mark.asyncio
    async def test_empty_context_returns_clean_message_without_calling_ollama(
        self, mock_db, user_admin
    ):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch("httpx.AsyncClient") as mock_client:
            result = await execute_query(
                mock_db,
                "mi pregunta",
                [1],
                user_admin,
                "http://ollama:11434",
                "qwen2.5-coder:1.5b",
            )

        mock_client.return_value.__aenter__.return_value.post.assert_not_called()
        assert (
            result["answer"]
            == "No se encontró contenido relevante en los documentos seleccionados."
        )
        assert result["context_used"] == []
        assert mock_db.add.called
        log = mock_db.add.call_args[0][0]
        expected = "empty context — no documents matched or content was null"
        assert log.metadata_.get("note") == expected


class TestBuildPrompt:
    def test_default_audience_is_general(self):
        from src.core.services.rag_service import DEFAULT_AUDIENCE

        assert DEFAULT_AUDIENCE == "general"

    def test_backward_compatible_no_audience(self):
        result = _build_prompt("test", ["context"])
        assert "EXCLUSIVAMENTE" in result
        assert "<contexto>" in result
        assert "<pregunta>" in result

    def test_audience_general_same_as_default(self):
        default = _build_prompt("test", ["context"])
        explicit = _build_prompt("test", ["context"], audience="general")
        assert default == explicit

    def test_audience_tecnico_includes_technical_instruction(self):
        result = _build_prompt("test", ["context"], audience="tecnico")
        assert "vocabulario técnico preciso" in result
        assert "detalles de implementación" in result

    def test_audience_ejecutivo_includes_business_instruction(self):
        result = _build_prompt("test", ["context"], audience="ejecutivo")
        assert "lenguaje de negocio" in result
        assert "impacto, riesgos, costes" in result

    def test_audience_stakeholder_includes_strategic_instruction(self):
        result = _build_prompt("test", ["context"], audience="stakeholder")
        assert "alineación estratégica" in result
        assert "valor de negocio" in result

    def test_each_audience_produces_unique_prompt(self):
        prompts = {}
        for aud in sorted(VALID_AUDIENCES):
            prompts[aud] = _build_prompt("test", ["context"], audience=aud)
        unique = set(prompts.values())
        assert len(unique) == len(VALID_AUDIENCES)

    def test_invalid_audience_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid audience"):
            _build_prompt("test", ["context"], audience="invalid")

    def test_query_and_context_still_present_with_audience(self):
        result = _build_prompt("mi pregunta", ["mi contexto"], audience="tecnico")
        assert "mi pregunta" in result
        assert "mi contexto" in result
