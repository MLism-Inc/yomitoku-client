import json
from pathlib import Path
from unittest.mock import MagicMock

import boto3
import pytest
from click.testing import CliRunner

import yomitoku_client.cli.sagemaker as sagemaker_cli_module
from yomitoku_client.cli.sagemaker import sagemaker


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_sagemaker_manager(monkeypatch):
    """SagemakerManager をモックし、deploy メソッドが呼ばれた際の引数を記録する"""
    record = {}

    class MockSagemakerManager:
        def __init__(self, region=None, profile=None):
            record["init_args"] = {"region": region, "profile": profile}

        def deploy(
            self,
            endpoint_name,
            instance_type,
            model_package_arn,
            instance_count,
        ):
            record["deploy_args"] = {
                "endpoint_name": endpoint_name,
                "instance_type": instance_type,
                "model_package_arn": model_package_arn,
                "instance_count": instance_count,
            }
            return True  # 成功をシミュレート

    monkeypatch.setattr(sagemaker_cli_module, "SagemakerManager", MockSagemakerManager)
    return record


@pytest.fixture(autouse=True)
def mock_home_dir(monkeypatch, tmp_path: Path):
    """
    pathlib.Path.home を tmp_path に差し替えて、設定ファイルが一時ディレクトリに作られるようにする
    """
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home_dir)
    return home_dir


@pytest.fixture
def mock_boto3_session(monkeypatch):
    """boto3.Sessionをモックして、デフォルトリージョンを返すようにする"""
    mock_session = MagicMock()
    mock_session.region_name = "ap-northeast-1"
    monkeypatch.setattr(boto3, "Session", lambda **kwargs: mock_session)  # noqa: ARG005


def _read_config(home_dir: Path) -> dict:
    config_path = home_dir / ".yomitoku" / "config.json"
    assert config_path.exists()
    with config_path.open("r") as f:
        return json.load(f)


def test_configure_success(runner: CliRunner, mock_home_dir: Path, mock_boto3_session):  # noqa: ARG001
    """
    configure コマンドが正常に Model Package ARN を保存できることをテストする
    """
    valid_arn = "arn:aws:sagemaker:ap-northeast-1:123456789012:model-package/test-model"

    result = runner.invoke(sagemaker, ["configure"], input=f"{valid_arn}\n")

    assert result.exit_code == 0
    assert "Successfully configured Model Package ARN" in result.output
    assert "ap-northeast-1.console.aws.amazon.com" in result.output
    # デフォルトプロダクトのサブスクリプション画面が案内される
    assert "prod-o37wuz7bn7kvc" in result.output

    # 設定ファイルが正しく書き込まれているか確認
    config = _read_config(mock_home_dir)
    assert (
        config["sagemaker"]["products"]["document-analyzer"]["model_package_arn"]
        == valid_arn
    )


def test_configure_lite_product(
    runner: CliRunner,
    mock_home_dir: Path,
    mock_boto3_session,  # noqa: ARG001
):
    """
    configure --product document-analyzer-lite が軽量版プロダクトの設定を保存することをテストする
    """
    lite_arn = "arn:aws:sagemaker:ap-northeast-1:123456789012:model-package/lite-model"

    result = runner.invoke(
        sagemaker,
        ["configure", "--product", "document-analyzer-lite"],
        input=f"{lite_arn}\n",
    )

    assert result.exit_code == 0
    # 軽量版プロダクトのサブスクリプション画面が案内される
    assert "prod-n6jdf73xzm24m" in result.output

    config = _read_config(mock_home_dir)
    assert (
        config["sagemaker"]["products"]["document-analyzer-lite"]["model_package_arn"]
        == lite_arn
    )
    # 別プロダクトの設定が従来のキーを上書きしないこと
    assert "model_package_arn" not in config["sagemaker"]


def test_configure_migrates_legacy_config(
    runner: CliRunner,
    mock_home_dir: Path,
    mock_boto3_session,  # noqa: ARG001
):
    """
    旧形式のキーを持つ設定ファイルが、configure によりプロダクト別のキーへ移行されることをテストする
    """
    new_arn = "arn:aws:sagemaker:ap-northeast-1:123456789012:model-package/new-model"

    config_dir = mock_home_dir / ".yomitoku"
    config_dir.mkdir()
    with (config_dir / "config.json").open("w") as f:
        json.dump({"sagemaker": {"model_package_arn": "arn:aws:sagemaker:old"}}, f)

    result = runner.invoke(sagemaker, ["configure"], input=f"{new_arn}\n")

    assert result.exit_code == 0
    config = _read_config(mock_home_dir)
    assert (
        config["sagemaker"]["products"]["document-analyzer"]["model_package_arn"]
        == new_arn
    )
    assert "model_package_arn" not in config["sagemaker"]


def test_configure_keeps_other_product_arn(
    runner: CliRunner,
    mock_home_dir: Path,
    mock_boto3_session,  # noqa: ARG001
):
    """
    configure を別プロダクトで実行しても既存プロダクトの ARN が保持されることをテストする
    """
    arn = "arn:aws:sagemaker:ap-northeast-1:123456789012:model-package/model"
    lite_arn = "arn:aws:sagemaker:ap-northeast-1:123456789012:model-package/lite-model"

    runner.invoke(sagemaker, ["configure"], input=f"{arn}\n")
    runner.invoke(
        sagemaker,
        ["configure", "--product", "document-analyzer-lite"],
        input=f"{lite_arn}\n",
    )

    products = _read_config(mock_home_dir)["sagemaker"]["products"]
    assert products["document-analyzer"]["model_package_arn"] == arn
    assert products["document-analyzer-lite"]["model_package_arn"] == lite_arn


def test_configure_invalid_arn(runner: CliRunner, mock_boto3_session):  # noqa: ARG001
    """
    configure コマンドで不正な ARN を入力した場合にエラー終了することをテストする
    """
    invalid_arn = "this-is-not-an-arn"

    result = runner.invoke(
        sagemaker, ["configure"], input=f"{invalid_arn}\n", catch_exceptions=False
    )
    assert result.exit_code == 1
    assert "Invalid Model Package ARN format" in result.output


def test_deploy_with_cli_option(runner: CliRunner, mock_sagemaker_manager):
    """
    deploy コマンドで --model-package-arn オプションが渡された場合に、それが使われることをテストする
    """
    cli_arn = "arn:aws:sagemaker:us-west-2:111122223333:model-package/cli-model"
    instance_type = "ml.g4dn.xlarge"
    endpoint_name = "test-endpoint"

    result = runner.invoke(
        sagemaker,
        [
            "deploy",
            "--endpoint-name",
            endpoint_name,
            "--model-package-arn",
            cli_arn,
            "--instance-type",
            instance_type,
        ],
    )
    assert result.exit_code == 0

    # SagemakerManager.deploy が正しい引数で呼ばれたか確認
    deploy_args = mock_sagemaker_manager["deploy_args"]
    assert deploy_args["model_package_arn"] == cli_arn
    assert deploy_args["instance_type"] == instance_type
    assert deploy_args["endpoint_name"] == endpoint_name
    assert deploy_args["instance_count"] == 1  # Default value


def test_deploy_uses_product_specific_config(
    runner: CliRunner, mock_sagemaker_manager, mock_home_dir: Path
):
    """
    deploy コマンドが --product で指定されたプロダクトの ARN を設定ファイルから読むことをテストする
    """
    arn = "arn:aws:sagemaker:ap-northeast-1:444455556666:model-package/model"
    lite_arn = "arn:aws:sagemaker:ap-northeast-1:444455556666:model-package/lite-model"

    config_dir = mock_home_dir / ".yomitoku"
    config_dir.mkdir()
    with (config_dir / "config.json").open("w") as f:
        json.dump(
            {
                "sagemaker": {
                    "model_package_arn": arn,
                    "products": {
                        "document-analyzer": {"model_package_arn": arn},
                        "document-analyzer-lite": {"model_package_arn": lite_arn},
                    },
                }
            },
            f,
        )

    result = runner.invoke(
        sagemaker,
        ["deploy", "--product", "document-analyzer-lite"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    deploy_args = mock_sagemaker_manager["deploy_args"]
    assert deploy_args["model_package_arn"] == lite_arn
    # エンドポイント名はプロダクトに依存しない
    assert deploy_args["endpoint_name"] == "yomitoku-sagemaker"


def test_deploy_lite_flag_is_treated_as_lite_product(
    runner: CliRunner, mock_sagemaker_manager, mock_home_dir: Path
):
    """
    非推奨の --lite が --product document-analyzer-lite として扱われることをテストする
    """
    lite_arn = "arn:aws:sagemaker:ap-northeast-1:444455556666:model-package/lite-model"

    config_dir = mock_home_dir / ".yomitoku"
    config_dir.mkdir()
    with (config_dir / "config.json").open("w") as f:
        json.dump(
            {
                "sagemaker": {
                    "products": {
                        "document-analyzer-lite": {"model_package_arn": lite_arn}
                    }
                }
            },
            f,
        )

    result = runner.invoke(sagemaker, ["deploy", "--lite"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "--lite is deprecated" in result.output
    assert mock_sagemaker_manager["deploy_args"]["model_package_arn"] == lite_arn


def test_deploy_lite_flag_conflicting_with_product_fails(
    runner: CliRunner,
    mock_sagemaker_manager,  # noqa: ARG001
):
    """
    --lite と別プロダクトの --product を同時に指定した場合にエラー終了することをテストする
    """
    result = runner.invoke(
        sagemaker,
        ["deploy", "--product", "document-analyzer", "--lite"],
        catch_exceptions=False,
    )

    assert result.exit_code == 1
    assert "--lite conflicts with" in result.output


def test_deploy_legacy_config_is_not_used_for_other_product(
    runner: CliRunner,
    mock_sagemaker_manager,  # noqa: ARG001
    mock_home_dir: Path,
):
    """
    従来のキーのみが設定されている場合に、別プロダクトのデプロイでは流用されないことをテストする
    """
    config_dir = mock_home_dir / ".yomitoku"
    config_dir.mkdir()
    with (config_dir / "config.json").open("w") as f:
        json.dump(
            {
                "sagemaker": {
                    "model_package_arn": "arn:aws:sagemaker:ap-northeast-1:444455556666:model-package/model"
                }
            },
            f,
        )

    result = runner.invoke(
        sagemaker,
        ["deploy", "--product", "document-analyzer-lite"],
        catch_exceptions=False,
    )

    assert result.exit_code == 1
    assert "document-analyzer-lite" in result.output
    assert "is not specified" in result.output


def test_deploy_default_endpoint_name(
    runner: CliRunner, mock_sagemaker_manager, mock_home_dir: Path
):
    """
    --endpoint-name 未指定時に従来のデフォルトエンドポイント名が使われることをテストする
    """
    arn = "arn:aws:sagemaker:ap-northeast-1:444455556666:model-package/model"

    config_dir = mock_home_dir / ".yomitoku"
    config_dir.mkdir()
    with (config_dir / "config.json").open("w") as f:
        json.dump({"sagemaker": {"model_package_arn": arn}}, f)

    result = runner.invoke(sagemaker, ["deploy"], catch_exceptions=False)

    assert result.exit_code == 0
    assert (
        mock_sagemaker_manager["deploy_args"]["endpoint_name"] == "yomitoku-sagemaker"
    )


def test_deploy_with_config_file(
    runner: CliRunner, mock_sagemaker_manager, mock_home_dir: Path
):
    """
    deploy コマンドでオプションが無く、設定ファイルに ARN がある場合に、それが使われることをテストする
    """
    config_arn = (
        "arn:aws:sagemaker:eu-central-1:444455556666:model-package/config-model"
    )
    endpoint_name = "test-endpoint"

    # ダミーの設定ファイルを作成
    config_dir = mock_home_dir / ".yomitoku"
    config_dir.mkdir()
    config_path = config_dir / "config.json"
    with config_path.open("w") as f:
        json.dump({"sagemaker": {"model_package_arn": config_arn}}, f)

    # The choice of instance types is now enforced by click.
    # We will use a valid one for the test to pass the CLI validation.
    valid_instance_type = "ml.g4dn.xlarge"
    result = runner.invoke(
        sagemaker,
        [
            "deploy",
            "--endpoint-name",
            endpoint_name,
            "--instance-type",
            valid_instance_type,
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    deploy_args = mock_sagemaker_manager["deploy_args"]
    assert deploy_args["model_package_arn"] == config_arn
    assert deploy_args["instance_type"] == valid_instance_type
    assert deploy_args["endpoint_name"] == endpoint_name


def test_deploy_no_arn_fails(runner: CliRunner):
    """
    deploy コマンドでオプションも設定ファイルも無い場合にエラー終了することをテストする
    """
    result = runner.invoke(
        sagemaker,
        ["deploy", "--endpoint-name", "test-endpoint"],
        catch_exceptions=False,
    )

    assert result.exit_code == 1
    assert "Model Package ARN for 'document-analyzer' is not specified" in result.output
