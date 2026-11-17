"""Scoped light report colors, independent of the surrounding editor theme."""

# Lưu kiểu hiển thị dùng chung để màu chữ và nền dễ đọc.
REPORT_CSS = """<style>
:is(.pc-comparison,.plan-architecture,.q17-extension,.q17-estimation,.q6-view,.tpch-data-scale) {
    --tpch-report-fg:#202b33;
    --tpch-report-bg:#ffffff;
    --tpch-report-muted:#485763;
    color:var(--tpch-report-fg);
    background:var(--tpch-report-bg);
    color-scheme:light;
    opacity:1;
}
:is(.pc-comparison,.q17-extension,.q17-estimation,.q6-view,.tpch-data-scale) {
    padding:16px;box-sizing:border-box;max-width:100%;min-width:0
}
:is(.pc-comparison,.plan-architecture,.q17-extension,.q17-estimation,.q6-view,.tpch-data-scale)
:is(h3,h4,p,summary,th,td,pre,code,figcaption,li,strong,span) {color:inherit;opacity:1}
:is(.pc-comparison,.plan-architecture,.q17-extension,.q17-estimation,.q6-view,.tpch-data-scale) a {
    color:#155b91;text-decoration:underline;text-underline-offset:3px
}
:is(.pc-comparison,.plan-architecture,.q17-extension,.q17-estimation,.q6-view,.tpch-data-scale) pre {
    color:#202b33;background:#f2f5f7;border-color:#c7d0d7
}
:is(.pc-comparison,.plan-architecture,.q17-extension,.q17-estimation,.q6-view,.tpch-data-scale) thead {
    color:#202b33;background:#edf2f5
}
:is(.pc-comparison,.plan-architecture,.q17-extension,.q17-estimation,.q6-view,.tpch-data-scale) details {
    border-color:#b5c0c9
}
:is(.pc-comparison,.plan-architecture,.q17-extension,.q17-estimation,.q6-view,.tpch-data-scale) summary:focus-visible {
    outline:2px solid #155b91;outline-offset:3px
}
:is(.pc-comparison,.plan-architecture,.q17-extension,.q17-estimation,.q6-view,.tpch-data-scale) ::selection {
    color:#102331;background:#cce5f6
}
.pc-comparison .pc-muted {color:var(--tpch-report-muted);opacity:1}
.q6-view {font:15px/1.65 system-ui,sans-serif}
.q6-view h3 {font-size:20px;line-height:1.4;margin:0 0 18px}
.q6-view h4 {font-size:16px;margin:24px 0 12px}
.q6-view table {table-layout:fixed;border-collapse:collapse;width:100%}
.q6-view th,.q6-view td {
    border:1px solid #bfcbd4;padding:12px;text-align:left;vertical-align:top;
    overflow-wrap:anywhere;font-variant-numeric:tabular-nums
}
.q6-view thead th {color:#ffffff;background:#25485c;font-weight:650}
.q6-view tbody th {color:#202b33;background:#f1f5f7;font-weight:600}
.q6-view tbody td {color:#202b33;background:#ffffff}
.q6-view tbody tr:nth-child(even) td {background:#f5f8fa}
.q6-view td code {color:#164d72;background:#eaf2f7;padding:2px 4px;border-radius:3px}
.q6-view pre code {background:transparent}
.q6-view .bar {background:#2b6a91}
.q6-view summary {color:#25485c;padding:6px 0}
.q6-view pre {color:#202b33;background:#f2f5f7}
.tpch-data-scale .lead {border-color:#39749b}
@media(max-width:800px) {
    :is(.pc-comparison,.q17-extension,.q17-estimation,.q6-view,.tpch-data-scale) {padding:12px}
    .q6-view th,.q6-view td {padding:8px}
}
</style>"""
