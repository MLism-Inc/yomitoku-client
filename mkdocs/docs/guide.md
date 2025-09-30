# ユーザーガイド

## 使い方

YomiToku Clientを利用する前に事前にYomiTokuの出力ファイル(.jsonファイル)が必要です。

### YomiToku Proの使い方

次の手順でYomiToku Proを使うことができます。

1. YomiToku Proをデプロイ
1. YomiToku ProへAPIでアクセス

#### YomiToku Proをデプロイ

YomiToku Proをデプロイするには次の2通りの方法があります。

- AWS Marketplaceを用いてデプロイ
- YomiToku Proのコードを直接デプロイ

各方法の特徴は、以下の表のとおりです。

| 特徴 | AWS Marketplaceを用いてデプロイ | 直接デプロイ |
| :--- | :---: | :---: |
| 容易性 | &#9675; | &#9651; |
| AWS SageMakerでデプロイ可能 | &#9675; | &#9675; |
| AWS CloudFormationでデプロイ可能 | &#9675; | &#9675; |
| オンプレミスでデプロイ可能 | &#10005; | &#9675; |

以下のページでは、各デプロイ方法を説明しています。

- [AWS Marketplaceを用いてデプロイする場合](deploy-aws-marketplace.md)
- [直接デプロイする場合](deploy-direct.md)

#### YomiToku ProへAPIでアクセス

デプロイ先のプラットフォームによってへのアクセス方法が異なります。

以下のページでは、デプロイ先のプラットフォーム毎にAPIアクセス方法を説明しています。

- [AWS SageMakerでデプロイした場合](api-aws-sagemaker.md)
- [AWS CloudFormationでデプロイした場合](api-aws-cloudformation.md)
- [オンプレミスでデプロイした場合](api-on-premises.md)

### YomiToku Clientの使い方
