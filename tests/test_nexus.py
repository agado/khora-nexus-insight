import subprocess
from unittest.mock import MagicMock, patch

import pytest

import nexus


class TestParseArgs:
    def test_dev_parses(self):
        args = nexus.parse_args(["dev"])
        assert args.command == "dev"

    def test_down_parses(self):
        args = nexus.parse_args(["down"])
        assert args.command == "down"

    def test_prod_parses(self):
        args = nexus.parse_args(["prod"])
        assert args.command == "prod"

    def test_test_parses(self):
        args = nexus.parse_args(["test"])
        assert args.command == "test"

    def test_cov_parses(self):
        args = nexus.parse_args(["cov"])
        assert args.command == "cov"

    def test_seed_parses(self):
        args = nexus.parse_args(["seed"])
        assert args.command == "seed"

    def test_migrate_parses(self):
        args = nexus.parse_args(["migrate"])
        assert args.command == "migrate"

    def test_no_args_returns_none(self):
        args = nexus.parse_args([])
        assert args.command is None

    def test_help_flag(self):
        args = nexus.parse_args(["--help"])
        assert args.help is True

    def test_help_short_flag(self):
        args = nexus.parse_args(["-h"])
        assert args.help is True

    def test_invalid_command_exits(self):
        with pytest.raises(SystemExit):
            nexus.parse_args(["invalid"])


class TestBanner:
    def test_contains_project_name(self):
        assert "Khora Nexus Insight" in nexus.BANNER

    def test_contains_version(self):
        assert nexus.VERSION in nexus.BANNER

    def test_contains_tagline(self):
        assert "Donde los datos encuentran su alma" in nexus.BANNER


class TestPreflightDocker:
    def test_exits_when_docker_not_found(self):
        with patch("nexus.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(SystemExit):
                nexus.preflight_docker()

    def test_exits_when_docker_times_out(self):
        exc = subprocess.TimeoutExpired(cmd="docker", timeout=10)
        with patch("nexus.subprocess.run", side_effect=exc):
            with pytest.raises(SystemExit):
                nexus.preflight_docker()

    def test_exits_when_docker_fails(self):
        with patch("nexus.subprocess.run", side_effect=subprocess.CalledProcessError(1, "docker")):
            with pytest.raises(SystemExit):
                nexus.preflight_docker()

    def test_passes_when_docker_ok(self):
        with patch("nexus.subprocess.run") as mock:
            try:
                nexus.preflight_docker()
            except SystemExit:
                pytest.fail("preflight_docker raised SystemExit when docker is available")
        mock.assert_called_once()


class TestPreflightPytest:
    def test_exits_when_pytest_not_found(self):
        with patch("nexus.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(SystemExit):
                nexus.preflight_pytest()

    def test_exits_when_pytest_cov_not_found(self):
        with patch("nexus.subprocess.run") as mock:
            mock.side_effect = [MagicMock(), FileNotFoundError]
            with pytest.raises(SystemExit):
                nexus.preflight_pytest()

    def test_passes_when_both_ok(self):
        with patch("nexus.subprocess.run") as mock:
            try:
                nexus.preflight_pytest()
            except SystemExit:
                pytest.fail("preflight_pytest raised SystemExit when everything is available")
        assert mock.call_count == 2


class TestRunCommands:
    def test_run_dev_executes_compose_up(self):
        with patch("nexus.preflight_docker"):
            with patch("nexus.subprocess.run") as mock_run:
                with patch("nexus.webbrowser.open"):
                    with pytest.raises(SystemExit):
                        nexus.run_dev()
        mock_run.assert_called_once_with(["docker", "compose", "up", "--build"])

    def test_run_dev_interrupt_exits_cleanly(self):
        with patch("nexus.preflight_docker"):
            with patch("nexus.subprocess.run", side_effect=KeyboardInterrupt):
                with pytest.raises(SystemExit) as exc:
                    nexus.run_dev()
        assert exc.value.code == 0

    def test_run_down_executes_compose_down(self):
        with patch("nexus.preflight_docker"):
            with patch("nexus.subprocess.run") as mock_run:
                nexus.run_down()
        assert mock_run.call_count == 2
        mock_run.assert_any_call(["docker", "compose", "down"])
        mock_run.assert_any_call(["docker", "compose", "-f", "docker-compose.prod.yml", "down"])

    def test_run_down_interrupt_exits_cleanly(self):
        with patch("nexus.preflight_docker"):
            with patch("nexus.subprocess.run", side_effect=KeyboardInterrupt):
                with pytest.raises(SystemExit) as exc:
                    nexus.run_down()
        assert exc.value.code == 0

    def test_run_prod_exits_when_missing_prod_vars(self):
        with patch("nexus.preflight_docker"):
            with patch("nexus.load_dotenv"):
                with patch("nexus.subprocess.run"):
                    with patch.dict(nexus.os.environ, {}, clear=True):
                        with pytest.raises(SystemExit):
                            nexus.run_prod()

    def test_run_prod_with_existing_prod_vars(self):
        with patch("nexus.preflight_docker"):
            with patch("nexus.subprocess.run"):
                with patch.dict(
                    nexus.os.environ,
                    {
                        "PROD_DB_USER": "prod_user",
                        "PROD_DB_PASSWORD": "prod_pass",
                        "PROD_DB_NAME": "prod_db",
                        "PROD_JWT_SECRET": "prod_secret",
                        "PROD_MODEL_NAME": "llama3:8b",
                    },
                    clear=True,
                ):
                    nexus.run_prod()
                    assert nexus.os.environ["PROD_DB_USER"] == "prod_user"
                    assert nexus.os.environ["PROD_DB_PASSWORD"] == "prod_pass"
                    assert nexus.os.environ["PROD_DB_NAME"] == "prod_db"
                    assert nexus.os.environ["PROD_JWT_SECRET"] == "prod_secret"
                    assert nexus.os.environ["PROD_MODEL_NAME"] == "llama3:8b"


class TestMain:
    def test_main_no_args_shows_banner(self):
        with patch("nexus.print_banner") as mock_banner:
            with patch("nexus.clear_screen"):
                with patch("builtins.print"):
                    nexus.main([])
        mock_banner.assert_called_once()

    def test_main_help_shows_banner_without_clear(self):
        with patch("nexus.print_banner") as mock_banner:
            with patch("nexus._build_parser") as mock_parser:
                nexus.main(["--help"])
        mock_banner.assert_called_once_with(clear=False)
        mock_parser.return_value.print_help.assert_called_once()

    def test_main_dev_invokes_run_dev(self):
        with patch("nexus.run_dev") as mock_run:
            nexus.main(["dev"])
        mock_run.assert_called_once()

    def test_main_down_invokes_run_down(self):
        with patch("nexus.run_down") as mock_run:
            nexus.main(["down"])
        mock_run.assert_called_once()

    def test_main_test_invokes_run_test(self):
        with patch("nexus.run_test") as mock_run:
            nexus.main(["test"])
        mock_run.assert_called_once()

    def test_main_cov_invokes_run_cov(self):
        with patch("nexus.run_cov") as mock_run:
            nexus.main(["cov"])
        mock_run.assert_called_once()

    def test_main_prod_invokes_run_prod(self):
        with patch("nexus.run_prod") as mock_run:
            nexus.main(["prod"])
        mock_run.assert_called_once()

    def test_main_seed_invokes_run_seed(self):
        with patch("nexus.run_seed") as mock_run:
            nexus.main(["seed"])
        mock_run.assert_called_once()

    def test_main_migrate_invokes_run_migrate(self):
        with patch("nexus.run_migrate") as mock_run:
            nexus.main(["migrate"])
        mock_run.assert_called_once()

    def test_main_upload_invokes_run_upload(self):
        with patch("nexus.run_upload") as mock_run:
            nexus.main(["upload", "test.pdf", "--token", "x"])
        mock_run.assert_called_once_with(filepath="test.pdf", department_id=None, token="x")

    def test_main_document_get_invokes_run_document_get(self):
        with patch("nexus.run_document_get") as mock_run:
            nexus.main(["document", "get", "5", "--token", "x"])
        mock_run.assert_called_once_with(document_id=5, token="x")

    def test_main_document_list_invokes_run_document_list(self):
        with patch("nexus.run_document_list") as mock_run:
            nexus.main(["document", "list", "--token", "x"])
        mock_run.assert_called_once_with(token="x", skip=0, limit=50)

    def test_main_document_list_with_skip_limit(self):
        with patch("nexus.run_document_list") as mock_run:
            nexus.main(["document", "list", "--token", "x", "--skip", "5", "--limit", "10"])
        mock_run.assert_called_once_with(token="x", skip=5, limit=10)


class TestCLIParsing:
    def test_upload_filepath_and_token(self):
        args = nexus.parse_args(["upload", "doc.pdf", "--token", "abc123"])
        assert args.command == "upload"
        assert args.filepath == "doc.pdf"
        assert args.token == "abc123"
        assert args.department_id is None

    def test_upload_with_department_id(self):
        args = nexus.parse_args(["upload", "doc.pdf", "--department-id", "2", "--token", "x"])
        assert args.department_id == 2

    def test_document_get_parses(self):
        args = nexus.parse_args(["document", "get", "42", "--token", "xyz"])
        assert args.command == "document"
        assert args.document_command == "get"
        assert args.id == 42
        assert args.token == "xyz"

    def test_document_list_parses(self):
        args = nexus.parse_args(["document", "list", "--token", "abc"])
        assert args.command == "document"
        assert args.document_command == "list"
        assert args.token == "abc"
        assert args.skip == 0
        assert args.limit == 50

    def test_document_list_with_skip_limit(self):
        args = nexus.parse_args(
            ["document", "list", "--token", "x", "--skip", "10", "--limit", "5"]
        )
        assert args.skip == 10
        assert args.limit == 5

    def test_document_no_subcommand_exits_in_main(self):
        with patch("builtins.print"):
            with pytest.raises(SystemExit):
                nexus.main(["document"])


class TestRunUpload:
    def test_file_not_found_exits(self):
        with pytest.raises(SystemExit):
            nexus.run_upload(filepath="/nonexistent/file.pdf", department_id=None, token="x")

    def test_api_error_returns_error(self):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 409
        mock_response.json.return_value = {"detail": "Documento duplicado"}
        mock_file = MagicMock()
        mock_file.__enter__.return_value = MagicMock()

        with patch("nexus.Path.is_file", return_value=True):
            with patch("nexus.Path.open", return_value=mock_file):
                with patch("nexus.requests.post", return_value=mock_response):
                    with pytest.raises(SystemExit) as exc:
                        nexus.run_upload("test.pdf", department_id=1, token="x")
        assert exc.value.code == 1

    def test_api_success_prints_document(self):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": 1,
            "filename": "test.pdf",
            "sha256": "abc123",
            "department_id": 1,
            "uploaded_by": 1,
            "created_at": "2026-07-18T12:00:00+00:00",
        }
        mock_file = MagicMock()
        mock_file.__enter__.return_value = MagicMock()

        with patch("nexus.Path.is_file", return_value=True):
            with patch("nexus.Path.open", return_value=mock_file):
                with patch("nexus.requests.post", return_value=mock_response):
                    with patch("builtins.print") as mock_print:
                        nexus.run_upload("test.pdf", department_id=1, token="x")
        mock_print.assert_any_call("Documento subido: id=1 filename=test.pdf")


class TestRunDocumentGet:
    def test_api_error_returns_error(self):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Document not found"}

        with patch("nexus.requests.get", return_value=mock_response):
            with pytest.raises(SystemExit) as exc:
                nexus.run_document_get(99, token="x")
        assert exc.value.code == 1

    def test_api_success_prints_document(self):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": 5,
            "filename": "auditoria.pdf",
            "sha256": "def456",
            "department_id": 2,
            "uploaded_by": 3,
            "created_at": "2026-07-18T12:00:00+00:00",
        }

        with patch("nexus.requests.get", return_value=mock_response):
            with patch("builtins.print") as mock_print:
                nexus.run_document_get(5, token="x")
        mock_print.assert_any_call("Documento: id=5")
        mock_print.assert_any_call("  Nombre: auditoria.pdf")


class TestRunDocumentList:
    def test_empty_list_prints_message(self):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"documents": [], "total": 0}

        with patch("nexus.requests.get", return_value=mock_response):
            with patch("builtins.print") as mock_print:
                nexus.run_document_list(token="x")
        mock_print.assert_any_call("No hay documentos disponibles.")

    def test_list_with_documents(self):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "documents": [
                {
                    "id": 1,
                    "filename": "a.pdf",
                    "department_id": 1,
                    "created_at": "2026-07-18T12:00:00+00:00",
                },
                {
                    "id": 2,
                    "filename": "b.pdf",
                    "department_id": 2,
                    "created_at": "2026-07-17T10:00:00+00:00",
                },
            ],
            "total": 2,
        }

        with patch("nexus.requests.get", return_value=mock_response):
            with patch("builtins.print") as mock_print:
                nexus.run_document_list(token="x")
        mock_print.assert_any_call("Documentos (2 en total):")
        mock_print.assert_any_call("  [1] a.pdf — Depto 1 — 2026-07-18")
        mock_print.assert_any_call("  [2] b.pdf — Depto 2 — 2026-07-17")

    def test_api_error_returns_error(self):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Not authenticated"}

        with patch("nexus.requests.get", return_value=mock_response):
            with pytest.raises(SystemExit):
                nexus.run_document_list(token="x")


class TestConnectionErrorHandling:
    def test_upload_connection_error(self):
        with patch("nexus.Path.is_file", return_value=True):
            with patch("nexus.Path.open"):
                with patch("nexus.requests.post", side_effect=nexus.ReqConnectionError("test")):
                    with pytest.raises(SystemExit) as exc:
                        nexus.run_upload("test.pdf", department_id=1, token="x")
        assert exc.value.code == 1

    def test_document_get_connection_error(self):
        with patch("nexus.requests.get", side_effect=nexus.ReqConnectionError("test")):
            with pytest.raises(SystemExit) as exc:
                nexus.run_document_get(1, token="x")
        assert exc.value.code == 1

    def test_document_list_connection_error(self):
        with patch("nexus.requests.get", side_effect=nexus.ReqConnectionError("test")):
            with pytest.raises(SystemExit) as exc:
                nexus.run_document_list(token="x")
        assert exc.value.code == 1
