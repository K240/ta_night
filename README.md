## フォルダ構成

```
ta_night/
├── docs/                 # ドキュメント（本ファイルなど）
├── otls/                 # Houdini デジタルアセット（HDA）
├── python/               # Python スクリプト（USDレイアウト処理など）
│   ├── main.py           # レイアウトエクスポート等のメイン処理
│   ├── import_usd_layout.py
├── usd/                  # USD アセット
│   └── assets/           # 個別アセット（BT_*, Cube, Cylinder, Slope 等）
├── assets.usda           # アセット参照用USD
├── assets_wfc.usda       # WFC用アセット定義
├── layout.hip            # Houdini シーンファイル
├── layout.usda           # レイアウト出力USD
├── layout_wfc.usda       # WFC用レイアウト
├── README.md
└── .gitignore
```

