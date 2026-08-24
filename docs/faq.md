# FAQ

## SageMakerモデルとは何ですか？

AWS MarketplaceでサブスクライブしたYomiToku-Proのモデルパッケージから作成する、Amazon SageMaker AI上のリソースです。リアルタイム推論とBatch Transformのどちらでも、最初にSageMakerモデルを作成します。

SageMakerモデルを作成しただけでは推論インスタンスは起動しません。リアルタイム推論ではエンドポイント、Batch Transformではジョブを作成したときに推論インスタンスが使用されます。

## SageMakerモデルはどのように作成しますか？

[Step 1: SageMakerモデルを作成する](deploy-yomitoku-pro.md#create-sagemaker-model)を参照してください。手順の概要は次のとおりです。

1. AWS MarketplaceでYomiToku-Proをサブスクライブする
2. 使用するソフトウェアバージョンとリージョンを選択する
3. SageMakerモデル名と実行ロールを設定する
4. サブスクライブしたモデルパッケージをコンテナ定義に指定する
5. モデルを作成する

## 軽量版（liteモデル）はどのように作成しますか？

Lite版は通常版とは別のAWS Marketplace製品です。Lite版製品をサブスクライブし、その製品のModel Package ARNを使ってSageMakerモデルを作成します。詳細は[Batch Transformの軽量モード](batch-transform.md#batch-lite-model)を参照してください。

## モデル作成画面に「環境変数」がありません

環境変数の設定は不要です。「モデルパッケージサブスクリプションの選択」で、通常版では通常版製品、Lite版ではLite版製品を選択してください。Marketplace ModelPackageでは購入者による環境変数追加が許可されておらず、AWS CLIやCloudFormationでも追加できません。

## Model Package ARNはどこで取得できますか？

Amazon SageMaker AIコンソールの **AWS Marketplace resources > モデルパッケージ > AWS Marketplaceサブスクリプション**から、通常版またはLite版の対象製品と使用するバージョンを開き、詳細画面の **Model Package ARN**をコピーします。通常版とLite版では別々のARNが必要です。

`configure`のURLから取得できない場合は、MarketplaceからSageMakerモデルを作成し、**Deployments & inference > モデル**のモデル詳細画面から取得できます。既にモデルを作成済みの場合は、`aws sagemaker describe-model`でも確認できます。具体的な手順は[Model Package ARNを取得する](batch-transform.md#get-model-package-arn)を参照してください。

## 作成済みモデルを後からliteモデルへ変更できますか？

いいえ。作成済みのSageMakerモデルではコンテナ定義を変更できません。Lite版製品をサブスクライブし、そのModel Package ARNを使って別のSageMakerモデルを作成してください。

## リアルタイム推論とBatch Transformで別々のモデルが必要ですか？

同じモデル設定を利用する場合は、同じSageMakerモデルを参照できます。ただし、通常版とLite版はModel Package ARNが異なるため、それぞれ別のSageMakerモデルが必要です。

## Batch Transformにエンドポイントは必要ですか？

いいえ。必要なのはSageMakerモデルです。エンドポイント設定とリアルタイムエンドポイントは作成せず、モデル作成後に[Batch Transformを実行する](batch-transform.md)へ進んでください。

## Batch Transformの出力はどこに保存されますか？

Batch Transformジョブで指定したS3出力プレフィックスへ保存されます。各入力オブジェクトの名前に`.out`が付与され、YomiToku-Proの解析結果がJSONとして格納されます。詳しくは[`.out`ファイルを確認・ダウンロードする](batch-transform.md#download-batch-output)を参照してください。

## 図をMarkdownやHTMLへ出力するときに元文書は必要ですか？

必要です。JSONには図の位置情報は含まれますが、切り出す元画像は含まれません。図を画像として出力する場合は、Batch Transformの`.out`と元の画像またはPDFをセットで保管してください。
