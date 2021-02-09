import pytest

from doctr.documents import elements


def _mock_words(size=(1., 1.), offset=(0, 0), confidence=0.9):
    return [
        elements.Word("hello", confidence, [
            (offset[0], offset[1]),
            (size[0] / 2 + offset[0], size[1] / 2 + offset[1])
        ]),
        elements.Word("world", confidence, [
            (size[0] / 2 + offset[0], size[1] / 2 + offset[1]),
            (size[0] + offset[0], size[1] + offset[1])
        ])
    ]


def _mock_artefacts(size=(1, 1), offset=(0, 0), confidence=0.8):
    sub_size = (size[0] / 2, size[1] / 2)
    return [
        elements.Artefact("qr_code", confidence, [
            (offset[0], offset[1]),
            (sub_size[0] + offset[0], sub_size[1] + offset[1])
        ]),
        elements.Artefact("qr_code", confidence, [
            (sub_size[0] + offset[0], sub_size[1] + offset[1]),
            (size[0] + offset[0], size[1] + offset[1])
        ]),
    ]


def _mock_lines(size=(1, 1), offset=(0, 0)):
    sub_size = (size[0] / 2, size[1] / 2)
    return [
        elements.Line(_mock_words(size=sub_size, offset=offset)),
        elements.Line(_mock_words(size=sub_size, offset=(offset[0] + sub_size[0], offset[1] + sub_size[1]))),
    ]


def _mock_blocks(size=(1, 1), offset=(0, 0)):
    sub_size = (size[0] / 4, size[1] / 4)
    return [
        elements.Block(
            _mock_lines(size=sub_size, offset=offset),
            _mock_artefacts(size=sub_size, offset=(offset[0] + sub_size[0], offset[1] + sub_size[1]))
        ),
        elements.Block(
            _mock_lines(size=sub_size, offset=(offset[0] + 2 * sub_size[0], offset[1] + 2 * sub_size[1])),
            _mock_artefacts(size=sub_size, offset=(offset[0] + 3 * sub_size[0], offset[1] + 3 * sub_size[1])),
        ),
    ]


def _mock_pages(block_size=(1, 1), block_offset=(0, 0)):
    return [
        elements.Page(_mock_blocks(block_size, block_offset), 0, (300, 200),
                       {"value": 0., "confidence": 1.}, {"value": "EN", "confidence": 0.8}),
        elements.Page(_mock_blocks(block_size, block_offset), 1, (500, 1000),
                       {"value": 0.15, "confidence": 0.8}, {"value": "FR", "confidence": 0.7}),
    ]


def test_word():
    word_str = "hello"
    conf = 0.8
    geom = ((0, 0), (1, 1))
    word = elements.Word(word_str, conf, geom)

    # Attribute checks
    assert word.value == word_str
    assert word.confidence == conf
    assert word.geometry == geom

    # Render
    assert word.render() == word_str

    # Export
    assert word.export() == {"value": word_str, "confidence": conf, "geometry": geom}


def test_line():
    geom = ((0, 0), (0.5, 0.5))
    words = _mock_words(size=geom[1], offset=geom[0])
    line = elements.Line(words)

    # Attribute checks
    assert len(line.words) == len(words)
    assert all(isinstance(w, elements.Word) for w in line.words)
    assert line.geometry == geom

    # Render
    assert line.render() == "hello world"

    # Export
    assert line.export() == {"words": [w.export() for w in words], "geometry": geom}


def test_artefact():
    artefact_type = "qr_code"
    conf = 0.8
    geom = ((0, 0), (1, 1))
    artefact = elements.Artefact(artefact_type, conf, geom)

    # Attribute checks
    assert artefact.type == artefact_type
    assert artefact.confidence == conf
    assert artefact.geometry == geom

    # Render
    assert artefact.render() == "[QR_CODE]"

    # Export
    assert artefact.export() == {"type": artefact_type, "confidence": conf, "geometry": geom}


def test_block():
    geom = ((0, 0), (1, 1))
    sub_size = (geom[1][0] / 2, geom[1][0] / 2)
    lines = _mock_lines(size=sub_size, offset=geom[0])
    artefacts = _mock_artefacts(size=sub_size, offset=sub_size)
    block = elements.Block(lines, artefacts)

    # Attribute checks
    assert len(block.lines) == len(lines)
    assert len(block.artefacts) == len(artefacts)
    assert all(isinstance(w, elements.Line) for w in block.lines)
    assert all(isinstance(a, elements.Artefact) for a in block.artefacts)
    assert block.geometry == geom

    # Render
    assert block.render() == "hello world\nhello world"

    # Export
    assert block.export() == {"lines": [line.export() for line in lines],
                              "artefacts": [artefact.export() for artefact in artefacts], "geometry": geom}


def test_page():
    page_idx = 0
    page_size = (300, 200)
    orientation = {"value": 0., "confidence": 0.}
    language = {"value": "EN", "confidence": 0.8}
    blocks = _mock_blocks()
    page = elements.Page(blocks, page_idx, page_size, orientation, language)

    # Attribute checks
    assert len(page.blocks) == len(blocks)
    assert all(isinstance(b, elements.Block) for b in page.blocks)
    assert page.page_idx == page_idx
    assert page.dimensions == page_size
    assert page.orientation == orientation
    assert page.language == language

    # Render
    assert page.render() == "hello world\nhello world\n\nhello world\nhello world"

    # Export
    assert page.export() == {"blocks": [b.export() for b in blocks], "page_idx": page_idx, "dimensions": page_size,
                             "orientation": orientation, "language": language}


def test_document():
    pages = _mock_pages()
    doc = elements.Document(pages)

    # Attribute checks
    assert len(doc.pages) == len(pages)
    assert all(isinstance(p, elements.Page) for p in doc.pages)

    # Render
    page_export = "hello world\nhello world\n\nhello world\nhello world"
    assert doc.render() == f"{page_export}\n\n\n\n{page_export}"

    # Export
    assert doc.export() == {"pages": [p.export() for p in pages]}