# Calculation-of-Graduation-Credits-tool

成績データを使って、卒業要件の不足単位を確認するローカル実行用ツールです。

主な処理は次の2つです。

- 成績PDFをCSVに変換する
- CSVとSQLiteデータベースを照合して卒業要件を判定する

## 現在の構成

```text
.
├── py/
│   ├── graduation.py      # 卒業要件を判定するメイン処理
│   └── pdf-to-csv.py      # 成績PDFをCSVへ変換する処理
├── database/
│   ├── database.py        # graduation.db を作成する処理
│   ├── database_delete.py # graduation.db を削除する補助処理
│   └── csv/               # DB作成用の元データ
├── graduation.db          # 卒業要件データベース
├── grades/                # 変換したい成績PDFを置く場所
└── output/                # 変換後CSVの出力先
```

`grades/` と `output/` はローカル作業用フォルダです。個人の成績データを置く場所なので、Git管理からは外しています。

## 卒業要件を判定する

判定には、履修済み科目のCSVと `graduation.db` を使います。

```bash
python3 py/graduation.py --csv output/me3.csv
```

別のDBを使う場合は `--db` で指定できます。

```bash
python3 py/graduation.py --csv output/me3.csv --db graduation.db
```

判定用CSVには、少なくとも次の列が必要です。

```csv
category_big,category_mid,3rd,subject,credits,grade,year
```

`grade` が `0` または `1` の科目は、単位取得済みとして扱いません。

## 成績PDFをCSVに変換する

成績PDFを変換する場合は、PDFを `grades/` に置いてから次を実行します。

```bash
python3 py/pdf-to-csv.py
```

この処理は現在、次のPDF名を対象にしています。

- `grades/haru.pdf`
- `grades/kage.pdf`
- `grades/me.pdf`
- `grades/moza.pdf`
- `grades/ize.pdf`

実行すると、`output/` に中間CSVと判定用CSVが作成されます。卒業判定で使うのは `output/*3.csv` です。

## データベースを作り直す

`database/csv/` の元データから `graduation.db` を作り直す場合は、リポジトリのルートで次を実行します。

```bash
python3 database/database.py
```

使用するCSVは次の5つです。

- `database/csv/cs_subject.csv`
- `database/csv/subject_flags.csv`
- `database/csv/requirement_groups.csv`
- `database/csv/graduation_credits.csv`
- `database/csv/type.csv`

## メモ

- 通常の卒業判定だけなら、`py/graduation.py`、`graduation.db`、判定対象CSVがあれば動きます。
- PDF変換も使う場合は、`py/pdf-to-csv.py`、`grades/`、`output/` が必要です。
- DBを再作成する可能性がある場合は、`database/csv/` を残しておくと安心です。
