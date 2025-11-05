# Yomitoku-ClientのAWS認証設定ガイド

このドキュメントは、Yomitoku-Clientを利用するために必要なAWSの認証設定について、初心者の方にも分かりやすく解説します。

## はじめに：どの認証方法を選べばいい？

まず、あなたの状況に合った認証方法を選びましょう。

| 利用シーン | おすすめの認証方法 | 特徴 |
| :--- | :--- | :--- |
| 👤 **個人のPCで手軽に試したい** | [IAMユーザーとアクセスキー](#iam) | 最も基本的な方法です。手順に沿って設定すればOK。 |
| 🏢 **会社のセキュリティルールでMFAが必須** | [IAMロールを利用する (AssumeRole)](#iam-assumerole) | MFA（多要素認証）を使って一時的に権限を借ります。少し複雑です。 |
| ☁️ **EC2などAWS環境で実行したい** | [EC2インスタンスプロファイルを利用する](#ec2) | 最も簡単です。EC2に設定済みのロールを使います。 |

---

## IAMユーザーとアクセスキーを利用する

個人のPCからYomitoku-Clientを実行するための、最も基本的な設定方法です。

### ステップ1: 専用の権限ポリシーを作成する

まず、Yomitoku-Clientに「SageMakerというAIサービスを使っても良い」という許可を与えるための権限ルール（ポリシー）を作成します。

1. AWSマネジメントコンソールにログインし、サービス検索で「**IAM**」と入力して選択します。
2. 左側のメニューから「**ポリシー**」をクリックします。
3. 「**ポリシーを作成**」ボタンをクリックします。
4. 「**JSON**」タブを選択し、既存のテキストをすべて削除してから、以下のJSONコードを貼り付けます。

    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                  "sagemaker:DescribeEndpoint",
                  "sagemaker:InvokeEndpoint"
                ],
                "Resource": "*"
            }
        ]
    }
    ```

5. 「**次へ**」をクリックします。
6. **ポリシー名**に `YomitokuClientSageMakerInvokePolicy` のような分かりやすい名前を付けます。
7. 「**ポリシーを作成**」ボタンをクリックして完了です。

### ステップ2: 専用のIAMユーザーを作成する

次に、Yomitoku-Clientが使う専用のIAMユーザーを作成します。

1. IAMダッシュボードの左側メニューから「**ユーザー**」をクリックします。
2. 「**ユーザーを作成**」ボタンをクリックします。
3. **ユーザー名**に `yomitoku-client-user` のような分かりやすい名前を入力し、「**次へ**」をクリックします。
4. **許可の設定**画面で、「**ポリシーを直接アタッチする**」を選択します。
5. 検索ボックスに、先ほど作成したポリシー名（`YomitokuClientSageMakerInvokePolicy`）を入力して検索します。
6. 表示されたポリシーのチェックボックスをオンにし、「**次へ**」をクリックします。
7. 設定内容を確認し、「**ユーザーを作成**」ボタンをクリックして完了です。

### ステップ3: アクセスキーを取得する

作成したユーザーがプログラムからAWSにアクセスするための「IDとパスワード」にあたる、アクセスキーを発行します。

1. ユーザーリストから、作成したユーザー（`yomitoku-client-user`）をクリックします。
2. 「**セキュリティ認証情報**」タブを開きます。
3. 「**アクセスキー**」セクションまでスクロールし、「**アクセスキーを作成**」ボタンをクリックします。
4. ユースケースで「**ローカルコード**」を選択し、確認のチェックボックスにチェックを入れて「**次へ**」をクリックします。
5. （任意）説明タグは空欄のままで構いません。「**アクセスキーを作成**」をクリックします。
6. **重要:** ここで表示される以下の2つの情報を、必ず安全な場所にコピーして保存してください。
    * **アクセスキーID** (例: `AKIAXXXXXXXXXXXXXXX`)
    * **シークレットアクセスキー** (例: `TEST/EXAMPLE/KEY/XXXXXXXXXXXXXXXXXX`)

!!! warning
    シークレットアクセスキーはこの画面でしか表示されません。もし紛失した場合は、再度アクセスキーを作成し直してくだい。
    この情報はパスワードと同じです。絶対に他人に教えたり、Gitなどにコミットしたりしないでください

---

### ステップ4: PCにAWS認証情報を設定する

最後に、お使いのPCに、取得したアクセスキーを「プロファイル」として設定します。プロファイルとは、認証情報につける「名前」のようなものです。ここでは `yomitoku-client` という名前で設定します。

**前提:** PCに [AWS CLI](https://aws.amazon.com/jp/cli/) がインストールされている必要があります。[AWS公式ドキュメント](https://docs.aws.amazon.com/ja_jp/cli/latest/userguide/getting-started-install.html)にある手順に従ってインストールしてください。

1. ターミナル（コマンドプロンプト）を開きます。
2. 以下のコマンドを実行します。

    ```bash
    aws configure --profile yomitoku-client
    ```

3. コマンドを実行すると、いくつか質問されます。先ほど取得したキー情報を入力してください。
    * **AWS Access Key ID:** `[ステップ3でコピーしたアクセスキーIDを貼り付け]`
    * **AWS Secret Access Key:** `[ステップ3でコピーしたシークレットアクセスキーを貼り付け]`
    * **Default region name:** `[SageMakerエンドポイントがあるリージョン名を入力 (例: ap-northeast-1)]`
    * **Default output format:** `[json と入力 (推奨)]`

これで `yomitoku-client` という名前のプロファイル設定が完了しました。

### ステップ5: 設定を確認する

設定が正しくできたか、以下のコマンドで確認しましょう。

1. ターミナルで、`--profile`オプションを付けて以下のコマンドを実行します。

    ```bash
    aws sts get-caller-identity --profile yomitoku-client
    ```

2. 以下のように、作成したユーザーの情報（Arn）が返ってくれば成功です。

    ```json
    {
        "UserId": "AIDACKCEVS45EXAMPLEUSER",
        "Account": "123456789012",
        "Arn": "arn:aws:iam::123456789012:user/yomitoku-client-user"
    }
    ```

## YomiToku-Clientの実行方法 {id="yomitoku-execution-manual"}

!!!note
    YomiToku-Proのデプロイがまだ完了していない場合、[YomiToku-Proのデプロイの手順](./deploy-yomitoku-pro.md)に従ってください。

---

上記で設定したプロファイルを使って、Yomitoku-Clientを実行する方法です。

### CLIでプロファイルを指定する場合

コマンドのオプションとして `--profile` でプロファイル名を指定します。

```bash
yomitoku-client notebooks/sample/image.pdf \
  --endpoint your-endpoint-name \
  --profile yomitoku-client
```

### 環境変数でプロファイルを指定する場合

`AWS_PROFILE` 環境変数にプロファイル名を設定しておくと、コマンド実行のたびに `--profile` を指定する必要がなくなり便利です。

```bash
export AWS_PROFILE=yomitoku-client
yomitoku-client notebooks/sample/image.pdf --endpoint your-endpoint-name
```

### コードでプロファイルを指定する場合

`YomitokuClient` の初期化時に `profile` 引数でプロファイル名を指定します。以下は非同期で実行するコード例です。

```python
import asyncio
from yomitoku_client import YomitokuClient

ENDPOINT_NAME = "your-endpoint-name"
PROFILE_NAME = "yomitoku-client" # ここで設定したプロファイル名を指定
target_file = "notebooks/sample/image.pdf"

async def main():
    async with YomitokuClient(
        endpoint=ENDPOINT_NAME,
        profile=PROFILE_NAME,
    ) as client:
        result = await client.analyze_async(target_file)
        # (結果を処理するコード)
        print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## IAMロールを利用する (AssumeRole)

MFA（多要素認証）が必須の環境で、一時的にYomitoku-Client用の権限を持つロールに切り替わって（AssumeRoleして）実行する方法です。

### ステップ1: スイッチ先となるIAMロールを作成する

1. IAMコンソールの左メニューから「**ロール**」を選択し、「**ロールを作成**」をクリックします。
2. **信頼できるエンティティの種類**で「**カスタム信頼ポリシー**」を選択します。
3. JSONエディタに以下のポリシーを貼り付けます。`[アカウントID]` はご自身のAWSアカウントIDに置き換えてください。

    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::[アカウントID]:root"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "Bool": {
                        "aws:MultiFactorAuthPresent": "true"
                    }
                }
            }
        ]
    }
    ```

4. 「**次へ**」をクリックし、許可ポリシーの選択画面で、以前作成した `YomitokuClientSageMakerInvokePolicy` を検索してチェックを入れます。
5. 「**次へ**」をクリックし、**ロール名**に `YomitokuClientRole` のような分かりやすい名前を付けて、「**ロールを作成**」をクリックします。

### ステップ2: スイッチ元ユーザーの前提条件を確認する

AssumeRoleを行う大元となる、ご自身のIAMユーザーが以下の状態であることを確認します。

1. **アクセスキーが設定済みであること**
    ご自身のIAMユーザーの「セキュリティ認証情報」タブを開き、「アクセスキー」セクションに有効なアクセスキーが作成されていることを確認します。このアクセスキーが、お使いのPCの `~/.aws/credentials` ファイルにプロファイルとして設定されている必要があります。

2. **MFAデバイスが有効であること**
    同じく「セキュリティ認証情報」タブで、「割り当てられたMFAデバイス」を確認します。MFAデバイスのARN（例: `arn:aws:iam::123456789012:mfa/your-username`）が表示されていることを確認してください。このARNは後のステップで使います。

### ステップ3: スイッチ元ユーザーに必要な許可を与える

ご自身のIAMユーザーに、ステップ1で作成したロールへのAssumeRoleを許可します。

1. ご自身のIAMユーザーの「許可」タブを開き、「インラインポリシーを作成」をクリックし、「JSON」タブに以下のポリシーを貼り付けます。`[アカウントID]` はご自身のAWSアカウントIDに置き換えてください。

    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Resource": "arn:aws:iam::[アカウントID]:role/YomitokuClientRole"
            }
        ]
    }
    ```

3. ポリシーに `AllowAssumeYomitokuClientRole` のような名前を付けて保存し、ご自身のIAMユーザーにアタッチします。

### ステップ4: PCのAWSコンフィグファイルを編集する

PCの `~/.aws/config` ファイルに、MFAとロールの情報を追記します。

1. `~/.aws/config` ファイルを開きます。（なければ作成してください）
2. 以下の内容を追記します。`[アカウントID]`、`your-name`、`your-profile-name` はご自身の環境に合わせて変更してください。

    ```ini
    # [profile your-profile-name] はご自身の既存のプロファイル名に合わせる
    [profile your-profile-name]
    region = ap-northeast-1
    output = json

    # --- ここから追記 ---
    [profile yomitoku-client]
    region = ap-northeast-1
    output = json
    role_arn = arn:aws:iam::[アカウントID]:role/YomitokuClientRole
    source_profile = your-profile-name
    mfa_serial = arn:aws:iam::[アカウントID]:mfa/your-name
    ```

    * `role_arn`: ステップ1で作成したロールのARN
    * `source_profile`: スイッチ元のIAMユーザーのプロファイル名
    * `mfa_serial`: ステップ2で確認したMFAデバイスのARN

これで、`yomitoku-client` プロファイルを使うと、MFA認証後に自動で `YomitokuClientRole` にスイッチするようになります。

---

## MFAを利用する場合のYomiToku-Clientの実行方法

!!!note
    YomiToku-Proのデプロイがまだ完了していない場合、[YomiToku-Proのデプロイの手順](./deploy-yomitoku-pro.md)に従ってください。

### プロファイル名を指定して実行する

[YomiToku-Clientの実行方法](#yomitoku-execution-manual)と同様に、`--profile yomitoku-client` を指定して実行します。するとMFAコードが求められるため、MFAデバイスで生成された6桁のコードを入力してください。

```bash
yomitoku-client notebooks/sample/image.pdf \
  --endpoint your-endpoint-name \
  --profile yomitoku-client
Enter MFA code for arn:aws:iam::123456789012:mfa/your-name:
```

### 一時的な認証情報を取得して実行する

`profile`を指定して実行する場合、MFAコードの有効期限が切れるたびに再入力を求められます。以下のスクリプトを使うと、有効期間が長めの一時的な認証情報を取得し、環境変数に設定することができます。これにより、MFAコードの再入力を減らすことができます。

`MFA_CODE`にはMFAデバイスで生成された6桁のコードを入力してください。

```bash
PROFILE=yomitoku-client
MFA_CODE=012345

SESSION_NAME=yomitoku-client-session
ROLE_ARN=$(aws configure get "profile.$PROFILE.role_arn")
SOURCE_PROFILE=$(aws configure get "profile.$PROFILE.source_profile")
MFA_SERIAL=$(aws configure get "profile.$PROFILE.mfa_serial")
eval $(aws sts assume-role \
    --role-arn $ROLE_ARN \
    --role-session-name $SESSION_NAME \
    --serial-number $MFA_SERIAL \
    --token-code $MFA_CODE \
    --profile $SOURCE_PROFILE \
    | jq -r '.Credentials | "export AWS_ACCESS_KEY_ID=\(.AccessKeyId)\\nexport AWS_SECRET_ACCESS_KEY=\(.SecretAccessKey)\\nexport AWS_SESSION_TOKEN=\(.SessionToken)" ')
```

スクリプト実行後、`aws sts get-caller-identity` コマンドで、`assumed-role` を含むARNが返ってくれば成功です。このターミナルセッション中は、`yomitoku-client`コマンド等がMFAなしで実行できます。

---

## EC2インスタンスプロファイルを利用する

EC2インスタンス上でYomitoku-Clientを実行する場合、インスタンスに付与されたIAMロール（インスタンスプロファイル）の権限が自動的に使われるため、設定が最も簡単です。

### ステップ1: EC2のIAMロールに権限を追加する

1. Yomitoku-Clientを実行するEC2インスタンスにアタッチされているIAMロールを確認します。
2. そのIAMロールの「許可」タブを開き、「許可を追加」 > 「ポリシーをアタッチ」を選択します。
3. `YomitokuClientSageMakerInvokePolicy` を検索してチェックを入れ、アタッチします。

これだけで準備は完了です。

### ステップ2: コマンドを実行する

!!!note
    YomiToku-Proのデプロイがまだ完了していない場合、[YomiToku-Proのデプロイの手順](./deploy-yomitoku-pro.md)に従ってください。

EC2インスタンスにログインし、`--profile` などの認証情報を指定せずにコマンドを実行します。

```bash
# EC2インスタンスのターミナルで実行
yomitoku-client [引数...]
```

SDKが自動でEC2のロール情報を読み込んでくれるため、特別な認証設定は不要です。
