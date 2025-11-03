# Installation

本パッケージは **Python 3.10〜3.12** に対応しています。

---

## 📦 PyPI からのインストール

PyPI から直接インストールする場合は、以下のコマンドを実行してください。

```bash
pip install yomitoku-client
```

---

## ⚡ uv を使用したインストール

本リポジトリは、次世代の高速パッケージ管理ツール [uv](https://docs.astral.sh/uv/) を採用しています。
`uv` をインストール後、リポジトリをクローンし、以下を実行します。

```bash
uv sync --no-dev
```

依存関係が自動的に解決・インストールされます。

---

## 🧑‍💻 開発者向けセットアップ

開発環境を構築する場合は、開発用依存関係も含めて同期します。

```bash
uv sync
```

本プロジェクトでは、**ジョブランナーとして [tox](https://tox.wiki/en/latest/)** を使用しています。
以下のコマンドで tox をインストールしてください。

```bash
uv tool install tox --with tox-uv
```

---

## 🔧 tox コマンド例

tox により、Lint チェック・フォーマット・テストを一元管理しています。

```bash
# 各Pythonバージョンでユニットテストを実行
tox -p -e py310,py311,py312

# コードフォーマッタの適用 (ruff format)
tox -e format

# Linterチェックと自動修正 (ruff check --fix)
tox -e lint
```

---

## 🪄 pre-commit の設定

コミット時に自動で linter / formatter を適用するために、
`pre-commit` フックをインストールします。

```bash
uvx pre-commit install
```

これにより、コミット前に Ruff などの静的解析・整形処理が自動実行されます。

## 📄 ドキュメントのサービング

ドキュメントはmkdocsを利用して、作成しています。以下のコマンドを実行して、ローカルホストにサービングし、ドキュメントの内容を確認できます。

```bash
uv run mkdocs serve 
```
