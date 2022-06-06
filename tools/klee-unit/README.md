KLEE-Unit: KLEE-Driven Unit Test Generator
==========================================

## Requirements
The system is only tested on macOS. When adapting to the other platforms,
some additional changes may be required.
* LLVM12 is installed and in the PATH (llvm-dis)
* wllvm is installed and in the PATH (extract-bc)
* The bundled KLEE is compiled and in the PATH (klee)
* Python 3.8+
* PyQt6
* pycparser

## Running KLEE-Unit
```
python3 klee_unit_gui.py
```

Please refer to the report for instructions on how to run the two examples.