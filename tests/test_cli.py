from svg_compare.cli import main


def test_main_prints_hello_world(capsys) -> None:
    main()

    captured = capsys.readouterr()

    assert captured.out == "hello world\n"
