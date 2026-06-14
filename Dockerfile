FROM python:3.10-slim

# 作業ディレクトリの設定
WORKDIR /app

# 必要なシステムパッケージのインストール（コンパイル等に備える）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# requirements.txtのコピーと依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# プロジェクトファイルをコンテナ内にコピー
COPY . .

# デフォルト実行コマンド
CMD ["python", "src/simulation.py", "--config", "configs/default.yaml"]
