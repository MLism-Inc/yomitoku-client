import sys

import boto3
import click

from yomitoku_client.sagemaker import SagemakerManager
from yomitoku_client.utils import load_config, save_config

YOMITOKU_PRODUCT_ID = "prod-o37wuz7bn7kvc"
DEFAULT_REGION = "ap-northeast-1"


def _validate_model_package_arn(arn: str):
    """Validate the format of the Model Package ARN."""
    if not arn or not arn.startswith("arn:aws:sagemaker:"):
        click.secho(
            "Error: Invalid Model Package ARN format. It should start with 'arn:aws:sagemaker:'.",
            fg="red",
        )
        sys.exit(1)


@click.group("sagemaker")
def sagemaker():
    """Manage SageMaker endpoint deployment with CloudFormation."""


@sagemaker.command("configure")
@click.option("--profile", default=None, help="AWS profile name.")
@click.option("--region", default=None, help="AWS region.")
def configure(profile, region):
    """
    Configure the Model Package ARN for SageMaker deployment.
    """
    region = (
        boto3.Session(profile_name=profile, region_name=region).region_name
        or DEFAULT_REGION
    )
    destination_url = f"https://{region}.console.aws.amazon.com/sagemaker/home?region={region}#/model-packages/my-subscriptions/{YOMITOKU_PRODUCT_ID}"
    click.echo(
        "Please sign-in to AWS Console and open the following URL in your browser to find the Model Package ARN.",
    )

    click.echo("-" * 80)
    click.echo(destination_url)
    click.echo("-" * 80)

    model_package_arn = click.prompt("Please enter the Model Package ARN")
    _validate_model_package_arn(model_package_arn)

    config = load_config()
    if "sagemaker" not in config:
        config["sagemaker"] = {}
    config["sagemaker"]["model_package_arn"] = model_package_arn

    save_config(config)

    click.secho("Successfully configured Model Package ARN!", fg="green")


@sagemaker.command("deploy")
@click.option(
    "--endpoint-name",
    default="yomitoku-sagemaker",
    show_default=True,
    help="Name for the SageMaker endpoint. This will also be used to generate the stack name.",
)
@click.option(
    "--instance-type",
    type=click.Choice(["ml.g4dn.xlarge", "ml.g5.xlarge", "ml.g6.xlarge"]),
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
@click.option("--profile", default=None, help="AWS profile name.")
@click.option("--region", default=None, help="AWS region.")
def deploy(
    endpoint_name,
    instance_type,
    instance_count,
    model_package_arn,
    profile,
    region,
):
    """
    Create a new stack or update an existing one.
    """
    if model_package_arn:
        deploy_model_package_arn = model_package_arn
    else:
        config = load_config()
        deploy_model_package_arn = config.get("sagemaker", {}).get("model_package_arn")

    if not deploy_model_package_arn:
        click.secho(
            "Error: Model Package ARN is not specified. "
            "Please provide it via --model-package-arn option or configure it using 'yomitoku-client sagemaker configure'.",
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
