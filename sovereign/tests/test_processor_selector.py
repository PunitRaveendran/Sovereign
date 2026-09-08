from backend.app.multimodal.processor_selector import ProcessorSelector


def test_image_defaults_to_ocr():
    selector = ProcessorSelector()

    result = selector.select("drawing.png")

    assert result == "ocr"


def test_pdf_defaults_to_vision():
    selector = ProcessorSelector()

    result = selector.select("document.pdf")

    assert result == "vision"


def test_extract_text_request_uses_ocr():
    selector = ProcessorSelector()

    result = selector.select(
        "document.png",
        "Extract text from this document.",
    )

    assert result == "ocr"


def test_read_text_request_uses_ocr():
    selector = ProcessorSelector()

    result = selector.select(
        "scan.jpg",
        "Read the text from this image.",
    )

    assert result == "ocr"


def test_describe_image_request_uses_vision():
    selector = ProcessorSelector()

    result = selector.select(
        "drawing.png",
        "Describe this image.",
    )

    assert result == "vision"


def test_diagram_request_uses_vision():
    selector = ProcessorSelector()

    result = selector.select(
        "diagram.png",
        "Explain this diagram.",
    )

    assert result == "vision"


def test_ocr_request_has_priority_over_vision():
    selector = ProcessorSelector()

    result = selector.select(
        "document.png",
        "Extract text and describe the image.",
    )

    assert result == "ocr"


def test_unsupported_file_type_is_rejected():
    selector = ProcessorSelector()

    try:
        selector.select("notes.txt")
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "Unsupported file type" in str(error)