# プロジェクト実行ルール (Agent / 開発者向け)

本プロジェクトにおける実験やスクリプトの実行に関する重要なルールです。
会話セッションが途切れた場合や、新しく開発に参加するAgent・開発者は**必ず**このルールに従ってください。

## 1. 実行環境の強制制限

> [!IMPORTANT]
> **すべてのスクリプト実行、テスト、シミュレーション、結果検証は、必ず Docker コンテナ環境内で実行しなければなりません。**

- ホストマシン（ローカル環境）に直接 Python パッケージをインストールしたり、仮想環境（venv, conda等）を作成して直接スクリプトを実行したりすることは**厳禁**です。
- コマンドを実行する際は、必ず `docker compose run` または `docker compose exec` などの Docker コマンドを経由してください。

## 2. 推奨される実行コマンド

- **シミュレーションの実行**
  ```bash
  docker compose run --rm simulation --config configs/default.yaml
  ```
- **一括実行スクリプトの実行**
  ```bash
  docker compose run --rm simulation bash scripts/run_experiment.sh
  ```

## 3. ルール制定の背景
ローカル環境の差異によるライブラリのバージョン競合や実行エラーを防ぎ、シミュレーション結果の再現性（Reproducibility）を100%保証するためです。
