import types

import main

ART = {
    "title": "How to X",
    "html_url": "https://support.example.com/hc/en-us/articles/123-How-to-X",
    "body": '<h2><strong>Step</strong></h2><p>See <a href="/hc/en-us/articles/9">other</a></p>'
    '<pre><code>run --now</code></pre><img src="data:image/png;base64,AAAA" alt="x">'
    '<img src="https://cdn/x.png" alt="shot">',
}


def test_markdown_keeps_structure_and_citation_line():
    md = main.to_markdown(ART)
    assert md.startswith("# How to X\n\nArticle URL: https://support.example.com/hc/en-us/articles/123-How-to-X")
    assert "## Step\n" in md  # bold stripped from heading
    assert "[other](/hc/en-us/articles/9)" in md  # relative link preserved
    assert "run --now" in md
    assert "![shot](https://cdn/x.png)" in md


def test_inline_base64_images_are_dropped():
    assert "base64" not in main.to_markdown(ART)


def test_slug_is_id_prefixed_and_stable():
    assert main.slug(ART) == "123-How-to-X"


def test_remote_state_reads_id_and_hash_from_metadata():
    m = lambda k, v: types.SimpleNamespace(key=k, string_value=v)
    doc = types.SimpleNamespace(name="d/1", custom_metadata=[m("article_id", "1"), m("hash", "h")])
    untagged = types.SimpleNamespace(name="d/2", custom_metadata=None)
    docs = types.SimpleNamespace(list=lambda parent: [doc, untagged])
    client = types.SimpleNamespace(file_search_stores=types.SimpleNamespace(documents=docs))
    assert main.remote_state(client, types.SimpleNamespace(name="s")) == {"1": ("d/1", "h")}
