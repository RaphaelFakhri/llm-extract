from __future__ import annotations

from llm_extract.ingest.preprocess import reduce_html


def test_strips_scripts_and_styles():
    html = "<html><body><script>alert(1)</script><style>x{}</style>"
    html += "<h1>Title</h1><p class='price'>$5</p></body></html>"
    out = reduce_html(html)
    assert "alert" not in out
    assert "x{}" not in out
    assert "Title" in out


def test_flattens_table_specs():
    html = """
    <h1>Widget</h1>
    <table><tr><th>Color</th><td>Red</td></tr>
    <tr><th>Weight</th><td>2 kg</td></tr></table>
    """
    out = reduce_html(html)
    assert "Color: Red" in out
    assert "Weight: 2 kg" in out


def test_flattens_definition_lists():
    html = "<h1>X</h1><dl><dt>Material</dt><dd>Oak</dd></dl>"
    out = reduce_html(html)
    assert "Material: Oak" in out


def test_flattens_nested_spec_divs():
    html = '<h1>X</h1><div class="spec"><span>Max Load</span><span>120 kg</span></div>'
    out = reduce_html(html)
    assert "Max Load: 120 kg" in out


def test_respects_max_chars():
    html = "<h1>" + ("a" * 10000) + "</h1>"
    out = reduce_html(html, max_chars=100)
    assert len(out) <= 100
