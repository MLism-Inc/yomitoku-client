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
            self, endpoint_name, instance_type, model_package_arn, instance_count
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


def test_configure_success(runner: CliRunner, mock_home_dir: Path, mock_boto3_session):  # noqa: ARG001
    """
    configure コマンドが正常に Model Package ARN を保存できることをテストする
    """
    valid_arn = "arn:aws:sagemaker:ap-northeast-1:123456789012:model-package/test-model"

    result = runner.invoke(sagemaker, ["configure"], input=f"{valid_arn}\n")

    assert result.exit_code == 0
    assert "Successfully configured Model Package ARN!" in result.output
    assert "ap-northeast-1.console.aws.amazon.com" in result.output

    # 設定ファイルが正しく書き込まれているか確認
    config_path = mock_home_dir / ".yomitoku" / "config.json"
    assert config_path.exists()
    with config_path.open("r") as f:
        config = json.load(f)

    assert config["sagemaker"]["model_package_arn"] == valid_arn


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
    assert "Model Package ARN is not specified" in result.output
