from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError, WaiterError

from yomitoku_client.sagemaker import SagemakerManager


@pytest.fixture
def mock_boto3_session():
    """boto3.Session をモックするフィクスチャ"""
    with patch("boto3.Session") as mock_session_constructor:
        mock_session = MagicMock()
        mock_cf_client = MagicMock()
        mock_session.client.return_value = mock_cf_client
        mock_session_constructor.return_value = mock_session
        yield mock_session, mock_cf_client


@pytest.fixture
def manager(mock_boto3_session):  # noqa: ARG001
    """テスト用の SagemakerManager インスタンスを生成する"""
    return SagemakerManager(region="us-east-1", profile="test-profile")


@pytest.fixture
def mock_stack_response():
    """describe_stacks用の詳細なモックレスポンス"""
    return {
        "Stacks": [
            {
                "StackName": "test-endpoint",
                "StackStatus": "CREATE_COMPLETE",
                "CreationTime": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "Outputs": [
                    {"OutputKey": "Endpoint", "OutputValue": "test-endpoint-url"}
                ],
            }
        ]
    }


def test_init(mock_boto3_session):
    """SagemakerManagerの初期化をテストする"""
    mock_session, mock_cf_client = mock_boto3_session
    manager = SagemakerManager(region="us-east-1", profile="test-profile")

    boto3.Session.assert_called_once_with(
        region_name="us-east-1", profile_name="test-profile"
    )
    mock_session.client.assert_called_once_with("cloudformation")
    assert manager.session == mock_session
    assert manager.cf_client == mock_cf_client


def test_load_template(manager):
    """_load_templateが正しくテンプレートを読み込むかテストする"""
    with patch(
        "importlib.resources.read_text", return_value="template_content"
    ) as mock_read_text:
        template = manager._load_template()
        mock_read_text.assert_called_once_with(
            "yomitoku_client.resource", "cloudformation.yaml"
        )
        assert template == "template_content"


def test_deploy_create_stack_success(
    manager: SagemakerManager, mock_boto3_session, mock_stack_response
):
    """新しいスタックを正常に作成するケースをテストする"""
    _, mock_cf_client = mock_boto3_session

    # 1回目の呼び出し（_stack_exists）ではエラー、その後は成功を返す side_effect 関数
    call_count = 0

    def describe_stacks_side_effect(*args, **kwargs):  # noqa: ARG001
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ClientError(
                {"Error": {"Message": "Stack with id test-endpoint does not exist"}},
                "DescribeStacks",
            )
        # waiter と最後の describe の呼び出しのために、常に成功レスポンスを返す
        return mock_stack_response

    mock_cf_client.describe_stacks.side_effect = describe_stacks_side_effect

    mock_waiter = MagicMock()
    mock_cf_client.get_waiter.return_value = mock_waiter

    with patch.object(manager, "_watch_events") as mock_watch:
        result = manager.deploy(
            endpoint_name="test-endpoint",
            instance_type="ml.g4dn.xlarge",
            model_package_arn="test-arn",
            instance_count=1,
        )

    assert result is True
    assert call_count > 1
    mock_cf_client.create_stack.assert_called_once()
    mock_cf_client.get_waiter.assert_called_once_with("stack_create_complete")
    mock_waiter.wait.assert_called_once()
    mock_watch.assert_called_once()


def test_deploy_update_stack_success(
    manager: SagemakerManager, mock_boto3_session, mock_stack_response
):
    """既存のスタックを正常に更新するケースをテストする"""
    _, mock_cf_client = mock_boto3_session
    # describe_stacksが常に成功を返すように設定
    mock_cf_client.describe_stacks.return_value = mock_stack_response
    mock_waiter = MagicMock()
    mock_cf_client.get_waiter.return_value = mock_waiter

    with patch.object(manager, "_watch_events") as mock_watch:
        result = manager.deploy(
            endpoint_name="test-endpoint",
            instance_type="ml.g4dn.xlarge",
            model_package_arn="test-arn",
            instance_count=1,
        )

    assert result is True
    mock_cf_client.update_stack.assert_called_once()
    mock_cf_client.get_waiter.assert_called_once_with("stack_update_complete")
    mock_waiter.wait.assert_called_once()
    mock_watch.assert_called_once()


def test_deploy_no_updates(manager: SagemakerManager, mock_boto3_session):
    """スタックに変更がないケースをテストする"""
    _, mock_cf_client = mock_boto3_session
    mock_cf_client.describe_stacks.return_value = {"Stacks": [{}]}
    mock_cf_client.update_stack.side_effect = ClientError(
        {"Error": {"Message": "No updates are to be performed."}}, "UpdateStack"
    )

    result = manager.deploy(
        endpoint_name="test-endpoint",
        instance_type="ml.g4dn.xlarge",
        model_package_arn="test-arn",
        instance_count=1,
    )

    assert result is True


def test_deploy_client_error(manager: SagemakerManager, mock_boto3_session):
    """デプロイ中にClientErrorが発生するケースをテストする"""
    _, mock_cf_client = mock_boto3_session
    mock_cf_client.describe_stacks.return_value = {"Stacks": [{}]}
    mock_cf_client.update_stack.side_effect = ClientError(
        {"Error": {"Message": "Some AWS error"}}, "UpdateStack"
    )

    result = manager.deploy(
        endpoint_name="test-endpoint",
        instance_type="ml.g4dn.xlarge",
        model_package_arn="test-arn",
        instance_count=1,
    )

    assert result is False


def test_deploy_waiter_error(manager: SagemakerManager, mock_boto3_session):
    """Waiterがタイムアウトするケースをテストする"""
    _, mock_cf_client = mock_boto3_session
    mock_cf_client.describe_stacks.return_value = {"Stacks": [{}]}
    mock_waiter = MagicMock()
    mock_waiter.wait.side_effect = WaiterError(
        name="waiter", reason="timeout", last_response={}
    )
    mock_cf_client.get_waiter.return_value = mock_waiter

    with patch.object(manager, "_watch_events"):
        result = manager.deploy(
            endpoint_name="test-endpoint",
            instance_type="ml.g4dn.xlarge",
            model_package_arn="test-arn",
            instance_count=1,
        )

    assert result is False


def test_describe_success(
    manager: SagemakerManager, mock_boto3_session, mock_stack_response
):
    """describeが成功するケースをテストする"""
    _, mock_cf_client = mock_boto3_session
    mock_cf_client.describe_stacks.return_value = mock_stack_response

    manager.describe("test-endpoint")
    mock_cf_client.describe_stacks.assert_called_with(StackName="test-endpoint")


def test_describe_not_exists(manager: SagemakerManager, mock_boto3_session):
    """describeでスタックが存在しないケースをテストする"""
    _, mock_cf_client = mock_boto3_session
    mock_cf_client.describe_stacks.side_effect = ClientError(
        {"Error": {"Message": "Stack with id test-endpoint does not exist"}},
        "DescribeStacks",
    )
    manager.describe("test-endpoint")
    # エラーではなく警告ログが出て正常終了することを確認（ここでは例外が出ないことを確認）


def test_list_stacks_success(manager: SagemakerManager, mock_boto3_session):
    """list_stacksがyomitoku-client管理下のスタックのみを正しくフィルタリングして返すことをテストする"""
    _, mock_cf_client = mock_boto3_session
    mock_paginator = MagicMock()
    mock_page = {
        "Stacks": [
            # 1. 管理対象のスタック
            {
                "StackName": "yomitoku-stack-1",
                "StackStatus": "CREATE_COMPLETE",
                "CreationTime": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "Tags": [{"Key": "ManagedBy", "Value": "yomitoku-client"}],
            },
            # 2. タグがないスタック (除外対象)
            {
                "StackName": "no-tags-stack",
                "StackStatus": "CREATE_COMPLETE",
                "CreationTime": datetime(2024, 1, 2, tzinfo=timezone.utc),
                "Tags": [],
            },
            # 3. 別のツールで管理されているスタック (除外対象)
            {
                "StackName": "other-tool-stack",
                "StackStatus": "UPDATE_COMPLETE",
                "CreationTime": datetime(2024, 1, 3, tzinfo=timezone.utc),
                "Tags": [{"Key": "ManagedBy", "Value": "other-tool"}],
            },
            # 4. ManagedBy以外のタグを持つスタック (除外対象)
            {
                "StackName": "other-tags-stack",
                "StackStatus": "CREATE_COMPLETE",
                "CreationTime": datetime(2024, 1, 4, tzinfo=timezone.utc),
                "Tags": [{"Key": "Project", "Value": "yomitoku"}],
            },
            # 5. もう一つの管理対象のスタック
            {
                "StackName": "yomitoku-stack-2",
                "StackStatus": "CREATE_COMPLETE",
                "CreationTime": datetime(2024, 1, 5, tzinfo=timezone.utc),
                "Tags": [{"Key": "ManagedBy", "Value": "yomitoku-client"}],
            },
        ]
    }
    mock_paginator.paginate.return_value = [mock_page]
    mock_cf_client.get_paginator.return_value = mock_paginator

    stacks = manager.list_stacks()

    assert len(stacks) == 2
    stack_names = [s["StackName"] for s in stacks]
    assert "yomitoku-stack-1" in stack_names
    assert "yomitoku-stack-2" in stack_names
    assert "no-tags-stack" not in stack_names
    assert "other-tool-stack" not in stack_names
    assert "other-tags-stack" not in stack_names


def test_list_stacks_empty(manager: SagemakerManager, mock_boto3_session):
    """管理対象スタックがない場合に空のリストを返すことをテストする"""
    _, mock_cf_client = mock_boto3_session
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [{"Stacks": []}]
    mock_cf_client.get_paginator.return_value = mock_paginator

    stacks = manager.list_stacks()
    assert stacks == []


def test_delete_success(
    manager: SagemakerManager, mock_boto3_session, mock_stack_response
):
    """deleteが成功するケースをテストする"""
    _, mock_cf_client = mock_boto3_session
    mock_cf_client.describe_stacks.return_value = mock_stack_response
    mock_waiter = MagicMock()
    mock_cf_client.get_waiter.return_value = mock_waiter

    result = manager.delete("test-endpoint")

    assert result is True
    mock_cf_client.delete_stack.assert_called_once_with(StackName="test-endpoint")
    mock_cf_client.get_waiter.assert_called_once_with("stack_delete_complete")
    mock_waiter.wait.assert_called_once()


def test_delete_not_exists(manager: SagemakerManager, mock_boto3_session):
    """deleteでスタックが存在しないケースをテストする"""
    _, mock_cf_client = mock_boto3_session
    mock_cf_client.describe_stacks.side_effect = ClientError(
        {"Error": {"Message": "Stack with id test-endpoint does not exist"}},
        "DescribeStacks",
    )

    result = manager.delete("test-endpoint")
    assert result is True
    mock_cf_client.delete_stack.assert_not_called()
