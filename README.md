
```
python3 process_headerfiles.py ../edk2-testcases
python3 comment_out_static_assert.py ../edk2-testcases

```



```
chmod +x insert_assertion.py
./insert_assertion.py ../edk2-testcases/Testcases/Sample2Tests/CharConverter/CharConverter.c 107 OOB_WRITE "(*OutputBuffer)[i] = (CHAR16)InputBuffer[i];"
```

```
python3 generate_klee_driver.py CharConverterEntryPoint ../edk2-testcases/Testcases/Sample2Tests/CharConverter/CharConverter.c

```
```
clang-14 -emit-llvm -c -g -O0 -Xclang -disable-O0-optnone generated_klee_drivers/klee_driver_CharConverterEntryPoint.c
klee --external-calls=all -libc=uclibc --posix-runtime --smtlib-human-readable  --write-test-info --write-paths --write-smt2s   --write-cov  --write-cvcs --write-kqueries   --write-sym-paths --only-output-states-covering-new --use-query-log=solver:smt2  --simplify-sym-indices -max-time=5 klee_driver_CharConverterEntryPoint.bc
```
