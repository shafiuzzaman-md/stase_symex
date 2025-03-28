
### Step 1: Prepare harness
```
python3 prepare_harness.py ../edk2-testcases
```

### Step 2: Run analysis

```
python3 run_analysis.py ../edk2-testcases/Testcases/Sample2Tests/CharConverter/CharConverter.c 107 OOB_WRITE "(*OutputBuffer)[i] = (CHAR16)InputBuffer[i];"
```

