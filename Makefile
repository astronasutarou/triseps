OBJECT := $(patsubst %.cc,%.o,$(SOURCE))
TESTPY := --repository-url https://test.pypi.org/legacy/

.PHONY: clean build build_pypi upload_test upload_pypi

all:

.cc.o: $(HEADER)
	$(CXX) -o $@ -c $<

install:
	python -m pip install .

build:
	python -m build

upload_test: build
	twine upload --skip-existing $(TESTPY) dist/*

upload_pypi: build
	twine upload --skip-existing dist/*

clean:
	rm -r $(OBJECT)

serve:
	mkdocs serve
