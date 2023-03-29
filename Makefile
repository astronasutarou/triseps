OBJECT := $(patsubst %.cc,%.o,$(SOURCE))

.PHONY: clean build build_pypi upload_test upload_pypi

all:

.cc.o: $(HEADER)
	$(CXX) -o $@ -c $<

build:
	python setup.py build_ext --inplace

build_pypi: build
	python setup.py sdist bdist_wheel -p manylinux1_x86_64

upload_test: build_pypi
	twine upload --skip-existing $(TESTPY) dist/*

upload_pypi: build_pypi
	twine upload --skip-existing dist/*

clean:
	rm -r $(OBJECT)

serve:
	mkdocs serve
