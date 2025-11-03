.PHONY: build preview clean
build:
	typst compile test.typ --root ..

preview:
	typst compile -f png --pages 1 --ppi 250 --root .. test.typ test.png

clean:
	rm -f test.pdf
