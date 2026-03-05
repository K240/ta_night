## フォルダ構成

```
ta_night/
├── docs/                 # ドキュメント
├── otls/                 # Houdini デジタルアセット（HDA）
├── python/               # Python スクリプト（USDレイアウト処理など）
│   └── import_usd_layout.py # レイアウトインポート
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

## 環境

- Houdini 21.0.631
- Obsidian
  - ドキュメントは **obsidian** を使用しています。
    - https://obsidian.md/
- Unreal Engine 5.7.3

