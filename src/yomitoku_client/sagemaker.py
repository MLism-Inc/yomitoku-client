import time
from importlib import resources

import boto3
from botocore.exceptions import ClientError, WaiterError

from yomitoku_client.logger import set_logger

logger = set_logger(__name__)


class SagemakerManager:
    """CloudFormationスタックを管理してSageMakerエンドポイントをデプロイするクラス"""

    def __init__(self, region: str | None = None, profile: str | None = None):
        """
        SagemakerManagerを初期化します。

        Args:
            region (str | None): AWSリージョン。
            profile (str | None): AWSプロファイル名。
        """
        self.session = boto3.Session(profile_name=profile, region_name=region)
        self.cf_client = self.session.client("cloudformation")

    def _load_template(self) -> str:
        """パッケージリソースからCloudFormationテンプレートを読み込む"""
        try:
            return resources.read_text(
                "yomitoku_client.resource", "cloudformation.yaml"
            )
        except FileNotFoundError:
            logger.error("パッケージ内のテンプレートファイルが見つかりません。")
            raise
        except Exception as e:
            logger.error(
                "テンプレートファイルの読み込み中にエラーが発生しました: %s", e
            )
            raise

    def _stack_exists(self, endpoint_name: str) -> bool:
        """スタックが存在するかどうかを確認する"""
        try:
            self.cf_client.describe_stacks(StackName=endpoint_name)
            return True
        except ClientError as e:
            if "does not exist" in e.response["Error"]["Message"]:
                return False
            raise

    def deploy(
        self,
        endpoint_name: str,
        instance_type: str,
        model_package_arn: str,
        instance_count: int,
    ) -> bool:
        """スタックをデプロイ（作成または更新）する"""
        logger.info("'%s' スタックのデプロイを開始します...", endpoint_name)
        template_body = self._load_template()

        parameters = [
            {"ParameterKey": "EndpointName", "ParameterValue": endpoint_name},
            {"ParameterKey": "InstanceType", "ParameterValue": instance_type},
            {"ParameterKey": "ModelPackageARN", "ParameterValue": model_package_arn},
            {"ParameterKey": "InstanceCount", "ParameterValue": str(instance_count)},
        ]
        try:
            if self._stack_exists(endpoint_name):
                logger.info("既存のスタック '%s' を更新します。", endpoint_name)
                self.cf_client.update_stack(
                    StackName=endpoint_name,
                    TemplateBody=template_body,
                    Parameters=parameters,
                    Capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
                    Tags=[{"Key": "ManagedBy", "Value": "yomitoku-client"}],
                )
                waiter = self.cf_client.get_waiter("stack_update_complete")
            else:
                logger.info("新しいスタック '%s' を作成します。", endpoint_name)
                self.cf_client.create_stack(
                    StackName=endpoint_name,
                    TemplateBody=template_body,
                    Parameters=parameters,
                    Capabilities=["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM"],
                    Tags=[{"Key": "ManagedBy", "Value": "yomitoku-client"}],
                )
                waiter = self.cf_client.get_waiter("stack_create_complete")

            logger.info(
                "スタックの完了を待っています... (これには数分かかる場合があります)"
            )
            self._watch_events(endpoint_name, action_start_time=int(time.time()))
            waiter.wait(
                StackName=endpoint_name, WaiterConfig={"Delay": 30, "MaxAttempts": 60}
            )
            logger.info("スタック '%s' のデプロイが正常に完了しました。", endpoint_name)
            self.describe(endpoint_name)
            return True

        except ClientError as e:
            if "No updates are to be performed" in str(e):
                logger.info("スタックに変更はありません。デプロイをスキップしました。")
                return True
            logger.error("スタック操作中にエラーが発生しました: %s", e)
            return False
        except WaiterError as e:
            logger.error("スタック操作がタイムアウトまたは失敗しました: %s", e)
            return False

    def _watch_events(self, endpoint_name: str, action_start_time: int):
        """スタックイベントを監視してログに出力する"""
        last_event_id = None
        while True:
            try:
                # Waiterの状態を確認
                res = self.cf_client.describe_stacks(StackName=endpoint_name)
                status = res["Stacks"][0]["StackStatus"]
                if status.endswith(("_COMPLETE", "_FAILED")):
                    break

                events = self.cf_client.describe_stack_events(StackName=endpoint_name)[
                    "StackEvents"
                ]
                new_events = []
                if last_event_id:
                    for i, event in enumerate(events):
                        if event["EventId"] == last_event_id:
                            new_events = events[:i]
                            break
                else:
                    # 初回はアクション開始以降のイベントを取得
                    new_events = [
                        e
                        for e in events
                        if e["Timestamp"].timestamp() > action_start_time
                    ]

                if new_events:
                    last_event_id = new_events[0]["EventId"]
                    for event in reversed(new_events):
                        logger.info(
                            "  %s | %s | %s | %s",
                            event["ResourceType"],
                            event["LogicalResourceId"],
                            event["ResourceStatus"],
                            event.get("ResourceStatusReason", ""),
                        )
            except ClientError:
                # スタック作成直後は describe_stack_events が失敗することがある
                pass
            time.sleep(10)

    def describe(self, endpoint_name: str):
        """スタックの詳細情報を表示する"""
        if not self._stack_exists(endpoint_name):
            logger.warning("スタック '%s' は存在しません。", endpoint_name)
            return

        try:
            response = self.cf_client.describe_stacks(StackName=endpoint_name)
            stack = response["Stacks"][0]
            logger.info("スタック '%s' の詳細:", endpoint_name)
            logger.info("  ステータス: %s", stack["StackStatus"])
            logger.info("  作成日時: %s", stack["CreationTime"])
            if "Outputs" in stack:
                logger.info("  アウトプット:")
                for output in stack["Outputs"]:
                    logger.info(
                        "    %s: %s", output["OutputKey"], output["OutputValue"]
                    )
        except ClientError as e:
            logger.error("スタック詳細の取得中にエラーが発生しました: %s", e)

    def list_stacks(self) -> list[dict]:
        """'ManagedBy: yomitoku-client' タグを持つスタックを一覧表示する"""
        managed_stacks = []
        try:
            paginator = self.cf_client.get_paginator("describe_stacks")
            for page in paginator.paginate():
                for stack in page["Stacks"]:
                    # スタックが削除中の場合など、Tagsキーが存在しないことがある
                    if "Tags" not in stack:
                        continue
                    for tag in stack["Tags"]:
                        if (
                            tag["Key"] == "ManagedBy"
                            and tag["Value"] == "yomitoku-client"
                        ):
                            managed_stacks.append(
                                {
                                    "StackName": stack["StackName"],
                                    "StackStatus": stack["StackStatus"],
                                    "CreationTime": stack["CreationTime"],
                                }
                            )
                            break
            return managed_stacks
        except ClientError as e:
            logger.error("スタック一覧の取得中にエラーが発生しました: %s", e)
            return []

    def delete(self, endpoint_name: str) -> bool:
        """スタックを削除する"""
        if not self._stack_exists(endpoint_name):
            logger.warning(
                "スタック '%s' は存在しないため、削除できません。", endpoint_name
            )
            return True

        logger.info("スタック '%s' の削除を開始します...", endpoint_name)
        try:
            self.cf_client.delete_stack(StackName=endpoint_name)
            waiter = self.cf_client.get_waiter("stack_delete_complete")
            waiter.wait(
                StackName=endpoint_name, WaiterConfig={"Delay": 30, "MaxAttempts": 60}
            )
            logger.info("スタック '%s' の削除が正常に完了しました。", endpoint_name)
            return True
        except (ClientError, WaiterError) as e:
            logger.error("スタック削除中にエラーが発生しました: %s", e)
            return False
