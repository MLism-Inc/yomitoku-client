import sys
from dataclasses import dataclass

import boto3
import click
from click.core import ParameterSource

from yomitoku_client.sagemaker import SagemakerManager
from yomitoku_client.utils import load_config, save_config

DEFAULT_REGION = "ap-northeast-1"


@dataclass(frozen=True)
class SagemakerProduct:
    """AWS Marketplaceで提供しているプロダクトごとに異なる情報"""

    display_name: str
    """ユーザーに表示するプロダクト名"""

    marketplace_product_id: str
    """サブスクリプション画面のURL生成に利用するMarketplaceのプロダクトID"""


DEFAULT_PRODUCT = "document-analyzer"
LITE_PRODUCT = "document-analyzer-lite"

# プロダクトを追加する場合はこの辞書にエントリを追加する
PRODUCTS: dict[str, SagemakerProduct] = {
    "document-analyzer": SagemakerProduct(
        display_name="YomiToku-Pro - Document Analyzer",
        marketplace_product_id="prod-o37wuz7bn7kvc",
    ),
    LITE_PRODUCT: SagemakerProduct(
        display_name="YomiToku-Pro - Document Analyzer Lite",
        marketplace_product_id="prod-n6jdf73xzm24m",
    ),
}

INSTANCE_TYPES = [
    "ml.g4dn.xlarge",
    "ml.g5.xlarge",
    "ml.g6.xlarge",
    "ml.c7i.xlarge",
    "ml.c7i.2xlarge",
]


def product_option(func):
    """--product オプションを付与するデコレータ"""
    return click.option(
        "--product",
        type=click.Choice(list(PRODUCTS)),
        default=DEFAULT_PRODUCT,
        show_default=True,
        help="AWS Marketplace product to operate on.",
    )(func)


def _validate_model_package_arn(arn: str):
    """Validate the format of the Model Package ARN."""
    if not arn or not arn.startswith("arn:aws:sagemaker:"):
        click.secho(
            "Error: Invalid Model Package ARN format. It should start with 'arn:aws:sagemaker:'.",
            fg="red",
        )
        sys.exit(1)


def _resolve_lite_flag(product: str) -> str:
    """非推奨の --lite を軽量版プロダクトの指定として解釈する"""
    ctx = click.get_current_context()
    if (
        ctx.get_parameter_source("product") != ParameterSource.DEFAULT
        and product != LITE_PRODUCT
    ):
        click.secho(
            f"Error: --lite conflicts with '--product {product}'. "
            f"Please use '--product {LITE_PRODUCT}' instead of --lite.",
            fg="red",
        )
        sys.exit(1)

    click.secho(
        "Warning: --lite is deprecated. The lite model is now provided as a separate "
        f"AWS Marketplace product, so please use '--product {LITE_PRODUCT}' instead. "
        f"Deploying '{LITE_PRODUCT}'.",
        fg="yellow",
    )
    return LITE_PRODUCT


def _load_model_package_arn(product: str) -> str | None:
    """設定ファイルからプロダクトのModel Package ARNを読み込む"""
    sagemaker_config = load_config().get("sagemaker", {})
    model_package_arn = (
        sagemaker_config.get("products", {}).get(product, {}).get("model_package_arn")
    )
    if model_package_arn:
        return model_package_arn

    if product == DEFAULT_PRODUCT:
        # プロダクト別のキーを導入する前のバージョンで保存された設定との互換
        return sagemaker_config.get("model_package_arn")

    return None


def _save_model_package_arn(product: str, model_package_arn: str) -> None:
    """設定ファイルにプロダクトのModel Package ARNを保存する"""
    config = load_config()
    sagemaker_config = config.setdefault("sagemaker", {})
    products = sagemaker_config.setdefault("products", {})
    products.setdefault(product, {})["model_package_arn"] = model_package_arn

    if product == DEFAULT_PRODUCT:
        # プロダクト別のキーへ移行するため、旧形式のキーは残さない
        sagemaker_config.pop("model_package_arn", None)

    save_config(config)


@click.group("sagemaker")
def sagemaker():
    """Manage SageMaker endpoint deployment with CloudFormation."""


@sagemaker.command("configure")
@product_option
@click.option("--profile", default=None, help="AWS profile name.")
@click.option("--region", default=None, help="AWS region.")
def configure(product, profile, region):
    """
    Configure the Model Package ARN for SageMaker deployment.
    """
    region = (
        boto3.Session(profile_name=profile, region_name=region).region_name
        or DEFAULT_REGION
    )
    product_id = PRODUCTS[product].marketplace_product_id
    destination_url = f"https://{region}.console.aws.amazon.com/sagemaker/home?region={region}#/model-packages/my-subscriptions/{product_id}"
    click.echo(
        f"Product: {PRODUCTS[product].display_name} ({product})",
    )
    click.echo(
        "Please sign-in to AWS Console and open the following URL in your browser to find the Model Package ARN.",
    )

    click.echo("-" * 80)
    click.echo(destination_url)
    click.echo("-" * 80)

    model_package_arn = click.prompt("Please enter the Model Package ARN")
    _validate_model_package_arn(model_package_arn)

    _save_model_package_arn(product, model_package_arn)

    click.secho(
        f"Successfully configured Model Package ARN for '{product}'!", fg="green"
    )


@sagemaker.command("deploy")
@product_option
@click.option(
    "--endpoint-name",
    default="yomitoku-sagemaker",
    show_default=True,
    help="Name for the SageMaker endpoint. This will also be used to generate the stack name.",
)
@click.option(
    "--instance-type",
    type=click.Choice(INSTANCE_TYPES),
    default="ml.g4dn.xlarge",
    show_default=True,
    help="Instance type for the endpoint.",
)
@click.option(
    "--instance-count",
    default=1,
    type=int,
    show_default=True,
    help="Initial instance count for the endpoint.",
)
@click.option(
    "--model-package-arn",
    default=None,
    help="Model Package ARN to deploy. If not provided, it will be loaded from the configuration file.",
)
@click.option(
    "--lite",
    is_flag=True,
    default=False,
    help=f"[Deprecated] Alias for '--product {LITE_PRODUCT}'.",
)
@click.option("--profile", default=None, help="AWS profile name.")
@click.option("--region", default=None, help="AWS region.")
def deploy(
    product,
    endpoint_name,
    instance_type,
    instance_count,
    model_package_arn,
    lite,
    profile,
    region,
):
    """
    Create a new stack or update an existing one.
    """
    if lite:
        product = _resolve_lite_flag(product)

    deploy_model_package_arn = model_package_arn or _load_model_package_arn(product)

    if not deploy_model_package_arn:
        click.secho(
            f"Error: Model Package ARN for '{product}' is not specified. "
            "Please provide it via --model-package-arn option or configure it using "
            f"'yomitoku-client sagemaker configure --product {product}'.",
            fg="red",
        )
        sys.exit(1)

    _validate_model_package_arn(deploy_model_package_arn)

    manager = SagemakerManager(region=region, profile=profile)
    success = manager.deploy(
        endpoint_name=endpoint_name,
        instance_type=instance_type,
        model_package_arn=deploy_model_package_arn,
        instance_count=instance_count,
    )
    if not success:
        sys.exit(1)


@sagemaker.command("delete")
@click.option(
    "--endpoint-name",
    default="yomitoku-sagemaker",
    show_default=True,
    help="Name of the SageMaker endpoint whose stack should be deleted.",
)
@click.option("--profile", default=None, help="AWS profile name.")
@click.option("--region", default=None, help="AWS region.")
def delete(endpoint_name, profile, region):
    """
    Delete a CloudFormation stack associated with an endpoint.
    """
    manager = SagemakerManager(region=region, profile=profile)
    if not manager.delete(endpoint_name):
        sys.exit(1)


@sagemaker.command("describe")
@click.option(
    "--endpoint-name",
    default="yomitoku-sagemaker",
    show_default=True,
    help="Name of the SageMaker endpoint whose stack should be described.",
)
@click.option("--profile", default=None, help="AWS profile name.")
@click.option("--region", default=None, help="AWS region.")
def describe(endpoint_name, profile, region):
    """
    Describe a CloudFormation stack associated with an endpoint.
    """
    manager = SagemakerManager(region=region, profile=profile)
    manager.describe(endpoint_name)


@sagemaker.command("list")
@click.option("--profile", default=None, help="AWS profile name.")
@click.option("--region", default=None, help="AWS region.")
def list_stacks(profile, region):
    """
    List all stacks managed by yomitoku-client.
    """
    manager = SagemakerManager(region=region, profile=profile)
    stacks = manager.list_stacks()

    if not stacks:
        click.echo("No stacks managed by yomitoku-client found.")
        return

    click.echo(f"{'Stack Name':<30} {'Status':<25} {'Creation Time'}")
    click.echo("-" * 80)
    for stack in sorted(stacks, key=lambda s: s["CreationTime"], reverse=True):
        click.echo(
            f"{stack['StackName']:<30} {stack['StackStatus']:<25} {stack['CreationTime'].strftime('%Y-%m-%d %H:%M:%S')}"
        )
